import argparse
import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
from sortedcontainers import SortedList

import statAggregator as sa

def calculateIdleStats(procs):
    """
    Inputs:
    procs - a list of at least one days worth of Procedure objects, in chronological order

    Outputs:
    roomCumIdles - a list of dicts, where keys are rooms and values are cumulative conservative idle time, cumulative
    liberal idle time, and number of idle intervals. Each dict is one day.
    """

    roomIdles = []
    onlyInBetweenIdles = []
    i = 0
    while i < len(procs): # Because i is incremented in inner loop, this outer while loop is iterated once per day

        currentDate = procs[i].date
        todaysProcs = []
        while i < len(procs) and procs[i].date == currentDate:
            todaysProcs.append(procs[i])
            i += 1

        idBlocks(todaysProcs)
        roomIdle = findIdles(todaysProcs, trailingIdles=True)
        roomIdles.append(roomIdle)
        inBetweenIdle = findIdles(todaysProcs)
        onlyInBetweenIdles.append(inBetweenIdle)

    ideals = calculateIdealIdles(onlyInBetweenIdles, plot=True)

    return ideals, roomIdles

def idBlocks(procs):
    """
    Inputs:
    procs - a list of exactly one days worth of Procedure objects

    idBlocks() adds a blockId field to each procedure, identifying which block the procedure belongs to. Indexing
    starts at 0 every day, so only useful for looking at blocks within the same day.
    """

    # Group the procedures by room
    rooms = makeRoomsDict(procs)

    # Join contiguous procedures into blocks with blockIds
    blockId = 0
    for room, surgeries in rooms.items():
        surgeries.sort(key=lambda x: x.schedStart) # sort by scheduled start time
        surgeries[0].blockId = blockId
        for i, surgery in enumerate(surgeries[1:]):
            if surgery.schedStart != surgeries[i].schedEnd: # if surgery start time != end time of previous surgery, make new block
                blockId += 1
            surgery.blockId = blockId
        blockId += 1


def findIdles(procs, estimate='conservative', trailingIdles = False):
    """
    Inputs:
    procs - a list of exactly one days worth of Procedure objects

    Outputs:
    roomIdles - a dict where keys are rooms and values are liberal and conservative idle times. Represents one day.
    """

    # Group the procedures by room
    rooms = makeRoomsDict(procs)

    # Calculate idles
    roomIdles = {}
    for room, surgeries in rooms.items():
        surgeries.sort(key=lambda x: x.inRoom) # sort by real start time, to accommodate for schedules that were shuffled
        individualIdles = []
        currentBlockIdles = []

        if surgeries:

            currentBlockId = surgeries[0].blockId
            for i, surgery in enumerate(surgeries[1:]):

                if surgery.blockId == currentBlockId:

                    if estimate == 'liberal':
                        # In case, surgery is in same block, but started next day
                        sameBlockNewDay = (surgery.date != surgeries[i].date) and not surgeries[i].procEndStraddledMidnight
                        # must be datetimes, not time objects, for subtraction
                        inRoom = dt.datetime.combine(dt.datetime(1, 1, 1 + sameBlockNewDay), surgery.inRoom)
                        prevProcEnd = dt.datetime.combine(dt.datetime(1,1,1), surgeries[i].procEnd)
                        delta = inRoom - prevProcEnd
                    elif estimate == 'conservative':
                        # In case, surgery is in same block, but started next day
                        sameBlockNewDay = (surgery.date != surgeries[i].date) and not surgeries[i].outRoomStraddledMidnight
                        # must be datetimes, not time objects, for subtraction
                        inRoom = dt.datetime.combine(dt.datetime(1, 1, 1 + sameBlockNewDay), surgery.inRoom)
                        prevOutRoom = dt.datetime.combine(dt.datetime(1,1,1), surgeries[i].outRoom)
                        delta = inRoom - prevOutRoom
                    else:
                        raise ValueError('findIdles() was given an invalid argument for estimate. Must me liberal or conservative')

                    delta = delta.seconds / 60 # convert to int in minutes
                    currentBlockIdles.append(delta)

                else: # finish current block, begin next

                    if trailingIdles:
                        # Find schedEnd of this block and append any trailing idle time to currentBlockIdles
                        currBlockProcs = filter(lambda x: x.blockId == currentBlockId, surgeries)
                        lastProcInBlock = max(currBlockProcs, key = lambda x: x.schedEnd)
                        schedBlockEnd = lastProcInBlock.schedEnd
                        if estimate == 'liberal':
                            if schedBlockEnd > surgeries[i].procEnd:
                                schedBlockEnd = dt.datetime.combine(dt.datetime(1, 1, 1), schedBlockEnd)
                                prevProcEnd = dt.datetime.combine(dt.datetime(1, 1, 1), surgeries[i].procEnd)
                                trailingIdle = schedBlockEnd - prevProcEnd
                                trailingIdle = trailingIdle.seconds / 60  # convert to int in minutes
                                currentBlockIdles.append(trailingIdle)
                        else:
                            if schedBlockEnd > surgeries[i].outRoom:
                                schedBlockEnd = dt.datetime.combine(dt.datetime(1, 1, 1), schedBlockEnd)
                                prevOutRoom = dt.datetime.combine(dt.datetime(1, 1, 1), surgeries[i].outRoom)
                                trailingIdle = schedBlockEnd - prevOutRoom
                                trailingIdle = trailingIdle.seconds / 60  # convert to int in minutes
                                currentBlockIdles.append(trailingIdle)

                    individualIdles.append(currentBlockIdles)
                    currentBlockIdles = []
                    currentBlockId = surgery.blockId

            # Append final block after loop finishes
            individualIdles.append(currentBlockIdles)

        roomIdles[room] = individualIdles

    return roomIdles # TODO: add a withTrailing data structure


def calculateIdealIdles(roomIdles, percentileToAvg=-1, plot=False):
    """
    Inputs:
    roomIdles - List of dicts. Each dict is one day. Keys are rooms, values are lists of lists of individual idle times
    percentileToAvg - Float. A value of 0.1 will average the fastest 10% of idle times. Values < 0 or > 1 will use
    only the fastest time

    Outputs:
    ideals - Dict. Keys are rooms, values are estimated ideal cleaning times

    Inefficient
    """

    # gather by room
    ideals = {}
    if percentileToAvg > 1 or percentileToAvg <= 0:
        onlyBest = True
    for day in roomIdles:
        for room in day.keys():
            if room in ideals:
                flattenedList = [item for sublist in day[room] for item in sublist]
                for item in flattenedList:
                    if onlyBest and not plot:
                        ideals[room].add(item)
                        if len(ideals[room]) > 1:
                            ideals[room].pop()
                    else:
                        ideals[room].add(item)
            else:
                flattenedList = [item for sublist in day[room] for item in sublist]
                if onlyBest and not plot:
                    if flattenedList:
                        ideals[room] = SortedList([min(flattenedList)])
                    else:
                        ideals[room] = SortedList([])
                else:
                    ideals[room] = SortedList(flattenedList)

    if plot:
        def idleHistogram(curr_pos = 0, plots = None, **kwargs):
            #TODO: incorporate percentileToAvg
            try:
                plt.hist(plots.values()[curr_pos], 60, facecolor='green', alpha=0.75)
            except IndexError:
                print plots.keys()[curr_pos] + " had no individual idle times"
            plt.xlabel('Individual Idle Times')
            plt.ylabel('Occurences')
            plt.title(plots.keys()[curr_pos])
            plt.grid(True)

        flipThruPlotter(idleHistogram, ideals)

    # reduce to an integer
    for room, l in ideals.items():
        if not onlyBest:
            upperIndex = int(len(l) * percentileToAvg) - 1
            upperIndex = max(upperIndex, 0)
            l = sum(l[:upperIndex]) / (upperIndex+1)
            ideals[room] = l
        else:
            try:
                best = ideals[room].pop(0)
                ideals[room] = best
            except IndexError:
                print room + " had no individual idle times"
                ideals[room] = 0

    # Debugging
    for room, l in ideals.items():
        print "Ideal idle time for " + room + " is " + str(l) + " minutes"

    return ideals


def makeRoomsDict(procs):
    rooms = {}
    for proc in procs:
        if proc.room in rooms:
            rooms[proc.room].append(proc)
        else:
            rooms[proc.room] = [proc]
    return rooms


def idleDictsToTuples(dictsOfIdles):
    """
    Inputs:
    dictsOfIdles - a list of dicts, where keys are rooms and values are lists of lists of idle times. Each dict is one day.

    Outputs:
    roomPlots - a list of plottable 2-tuples. First value is list of rooms, second is list of lists representing cumulative idle
    time per block
    """

    roomPlots = []
    for d in dictsOfIdles:
        items = d.items()
        rooms = [item[0] for item in items]
        unflattendLists = [item[1] for item in items]
        cumulatives = []
        maxNumBlocks = 0
        for l in unflattendLists:
            flattenedL = [sum(sublist) for sublist in l]
            maxNumBlocks = len(flattenedL) if len(flattenedL) > maxNumBlocks else maxNumBlocks
            cumulatives.append(flattenedL)

        # pad cumulatives so that they're all same length
        for c in cumulatives:
            if len(c) < maxNumBlocks:
                difference = maxNumBlocks - len(c)
                c.extend([0]*difference)

        roomPlots.append((rooms, cumulatives))

    return roomPlots


def dailyIdlePlot(curr_pos=0, plots=None, ax=None, excel=None):
    rooms = plots[0][curr_pos][0]
    ind = np.arange(len(rooms))
    width = 0.2
    palette = ['#a8e6ce', '#dcedc2', '#ffd3b5', '#ffaaa6', '#ff8c94']

    for plotNum in range(len(plots)):
        cumIdles = plots[plotNum][curr_pos][1]
        start = [0]*len(cumIdles)
        for i in range(len(cumIdles[0])):
            color = palette[i % len(palette)]
            block = [c[i] for c in cumIdles]
            if plotNum == 0: # Don't create duplicate labels
                ax.bar(ind + width*plotNum, block, width, color=color, bottom=start, label='Block ' + str(i + 1))
            else:
                ax.bar(ind + width*plotNum, block, width, color=color, bottom=start)
            start = map(lambda x, y: x + y, start, block)


    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    ax.set_xticks(ind + width / 2)
    ax.set_xticklabels(rooms, rotation=90)
    currDay = (excel.procs[0].date + dt.timedelta(days=curr_pos)).isoformat()[:10]
    ax.set_title(currDay)
    ax.set_ylabel('Minutes')


def flipThruPlotter(plotFunction, plots, multiple=False, **kwargs):

    # Closure is needed so that key_event can write to curr_pos
    def callback():
        curr_pos = [0] # List, not int, so that we can write to var in Python 2
        def key_event(e):
            if e.key == "right":
                curr_pos[0] += 1
            elif e.key == "left":
                curr_pos[0] -= 1
            else:
                return
            curr_pos[0] = curr_pos[0] % len(plots[0]) if multiple else curr_pos[0] % len(plots)
            ax.cla()
            plotFunction(curr_pos = curr_pos[0], plots=plots, **kwargs)
            fig.canvas.draw()
        return key_event

    fig = plt.figure()
    fig.canvas.mpl_connect('key_press_event', callback())
    ax = fig.add_subplot(111)
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])  # make room for legend
    kwargs['ax'] = ax
    plotFunction(curr_pos = 0, plots = plots, **kwargs)
    plt.show()

def roomIdlesMinusIdeals(roomIdles, ideals):

    realRoomIdles = []
    for r in roomIdles:
        newIdles = {}
        for room, idles in r.items():
            newBlocks = []
            for block in idles:
                newBlock = [max(indiv - ideals[room], 0) for indiv in block]
                newBlocks.append(newBlock)
            newIdles[room] = newBlocks
        realRoomIdles.append(newIdles)
    return realRoomIdles

def plotTrueIdleDist(roomIdles):

    # TODO: do liberal too
    allCumIdles = []
    for r in roomIdles:
        for room, idles in r.items():
            allCumIdles.append(idles[0])

    allCumIdles.sort()
    # get rid of zeros
    allCumIdles = [i for i in allCumIdles if i != 0]

    # the histogram of the data
    n, bins, patches = plt.hist(allCumIdles, 60, facecolor='blue', alpha=0.75)

    plt.xlabel('Cumulative Idle Minutes per OR per Day')
    plt.ylabel('Occurences')
    plt.title('True Idle Distribution')
    plt.grid(True)

    plt.show()

def printThresholdedDates(excel, realRoomIdles, room, threshold):

    startDate = excel.procs[0].date
    thresholdedDates = []
    for i, roomIdle in enumerate(realRoomIdles):
        if room in roomIdle:
            flattenedList = [item for sublist in roomIdle[room] for item in sublist]
            dailyCumulative = sum(flattenedList)
            if dailyCumulative >= threshold:
                date = (startDate + dt.timedelta(days=i)).isoformat()[:10]
                thresholdedDates.append(date)

    print "\n\nDays with \"real\" cumulative idle time >= " +  str(threshold) + " minutes in " + str(room) + ":"
    for d in thresholdedDates:
        print d
    return thresholdedDates

def parseInputs():
    parser = argparse.ArgumentParser(description="Query excel file for days with daily cumulative \"real\" idle time "
                                                 "over a threshold")
    parser.add_argument("filename", help="Excel file to read surgery data from")
    parser.add_argument("-m", "--min", help="Date ('mm/dd/yy' format) or row to start processing excel data. If row, 1 refers "
                                            "to first row containing data, not necessarily first row of excel sheet",
                        required=True)
    parser.add_argument("-M", "--max", help="Date ('mm/dd/yy' format) or row to finish processing excel data. If row, 1 refers ",
                        required=True)

    args = parser.parse_args()

    # TODO: fix plotTrueIdleDist()

    # should be 'Report for Dr Stehr_Jean Walrand 2016.xlsx', 1, 1000
    excel = sa.StatAggregator(args.filename, min= args.min, max=args.max) #TODO: ensure valid file name and exists
    ideals, roomIdles = calculateIdleStats(excel.procs)
    realRoomIdles = roomIdlesMinusIdeals(roomIdles, ideals)
    # plotTrueIdleDist(realRoomIdles)
    roomPlots = idleDictsToTuples(roomIdles)
    realRoomPlots = idleDictsToTuples(realRoomIdles)
    flipThruPlotter(dailyIdlePlot, [roomPlots, realRoomPlots], multiple=True, excel=excel)

    while True:
        print "\n"
        room = raw_input("Enter room: ")
        threshold = raw_input("Enter threshold, in minutes:")
        printThresholdedDates(excel, realRoomIdles, room, int(threshold))

if __name__ == "__main__":
    parseInputs()

