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
    i = 0
    while i < len(procs): # Because i is incremented in inner loop, this outer while loop is iterated once per day

        currentDate = procs[i].date
        todaysProcs = []
        while i < len(procs) and procs[i].date == currentDate:
            todaysProcs.append(procs[i])
            i += 1

        idBlocks(todaysProcs)
        roomIdle = findIdles(todaysProcs)
        roomIdles.append(roomIdle)

    ideals = calculateIdealIdles(roomIdles, plot=True)

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


def findIdles(procs, estimate='conservative'):
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
                else:
                    individualIdles.append(currentBlockIdles)
                    currentBlockIdles = []
                    currentBlockId = surgery.blockId

            # Append final block after loop finishes
            individualIdles.append(currentBlockIdles)

        roomIdles[room] = individualIdles

    return roomIdles


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
                        ideals[room].pop()
                    else:
                        ideals[room].add(item)
            else:
                flattenedList = [item for sublist in day[room] for item in sublist]
                ideals[room] = SortedList(flattenedList)

    if plot:
        def idleHistogram(curr_pos=0, plots=None):
            #TODO: incorporate percentileToAvg
            try:
                plt.hist(plots.values()[curr_pos], 60, facecolor='green', alpha=0.75)
            except IndexError:
                print plots.keys()[curr_pos] + " had no individual idle times"
            plt.xlabel('Individual Idle Times')
            plt.ylabel('Occurences')
            plt.title(plots.keys()[curr_pos])
            plt.grid(True)

        flipThruPlotter(idleHistogram, plots = ideals)



    # reduce to mean
    if not onlyBest:
        for room, l in ideals.items():
            upperIndex = int(len(l) * percentileToAvg) - 1
            l = sum(l[:upperIndex]) / (upperIndex+1)
            ideals[room] = l

    # If we wanted only best, but we accumulated all ideals for plotting, ditch all but best
    if onlyBest and plot:
        for room, l in ideals.items():
            try:
                best = ideals[room].pop(0)
                ideals[room] = best
            except IndexError:
                print room + " had no individual idle times"
                ideals[room] = 0

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
    roomPlots - a list of plottable 2-tuples. First value is rooms, second is list of lists representing cumulative idle
    time per block
    """

    # TODO: Make 0s into 0.1s or soemthing?

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


def idlePlotter(excel, roomPlots):

    # Closure is needed so that key_event can write to curr_pos
    def callback():
        curr_pos = [0]
        def key_event(e):

            if e.key == "right":
                curr_pos[0] += 1
            elif e.key == "left":
                curr_pos[0] -= 1
            else:
                return
            curr_pos[0] = curr_pos[0] % len(roomPlots)
            currDay = (excel.procs[0].date + dt.timedelta(days=curr_pos[0])).isoformat()[:10]

            ax.cla()
            rooms = roomPlots[curr_pos[0]][0]
            cumIdles = roomPlots[curr_pos[0]][1]
            ind = np.arange(len(rooms))
            width = 0.2

            palette = ['#a8e6ce', '#dcedc2', '#ffd3b5', '#ffaaa6', '#ff8c94']
            for i in range(len(cumIdles[0])):
                color = palette[i % len(palette)]
                block = [c[i] for c in cumIdles]
                bar = ax.bar(ind, block, width, color=color, label='Block ' + str(i+1))

            plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
            ax.set_xticks(ind + width / 2)
            ax.set_xticklabels(rooms, rotation=90)
            ax.set_title(currDay)
            fig.canvas.draw()
        return key_event

    fig = plt.figure()
    fig.canvas.mpl_connect('key_press_event', callback())
    ax = fig.add_subplot(111)
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height]) # make room for legend

    rooms = roomPlots[0][0]
    cumIdles = roomPlots[0][1]
    currDay = excel.procs[0].date.isoformat()[:10]
    ind = np.arange(len(rooms))
    width = 0.2

    palette = ['#a8e6ce','#dcedc2','#ffd3b5','#ffaaa6','#ff8c94']
    for i in range(len(cumIdles[0])):
        color = palette[i % len(palette)]
        block = [c[i] for c in cumIdles]
        bar = ax.bar(ind, block, width, color=color, label='Block ' + str(i+1))

    ax.set_xticks(ind + width / 2)
    ax.set_xticklabels(rooms, rotation=90)
    ax.set_title(currDay)
    ax.set_ylabel('Minutes')
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    plt.show()

def flipThruPlotter(plotFunction, **kwargs):

    # Closure is needed so that key_event can write to curr_pos
    def callback(**kwargs):
        curr_pos = [0] # List, not int, so that we can write to var in Python 2
        plots = kwargs['plots']
        def key_event(e):
            if e.key == "right":
                curr_pos[0] += 1
            elif e.key == "left":
                curr_pos[0] -= 1
            else:
                return
            curr_pos[0] = curr_pos[0] % len(plots)
            ax.cla()
            plotFunction(curr_pos = curr_pos[0], plots=plots)
            fig.canvas.draw()
        return key_event

    fig = plt.figure()
    fig.canvas.mpl_connect('key_press_event', callback(**kwargs))
    ax = fig.add_subplot(111)
    plotFunction(curr_pos = 0, **kwargs)
    plt.show()

def makeRealRoomIdles(roomIdles, ideals):

    realRoomIdles = []
    for r in roomIdles:
        newIdles = {}
        for room, idles in r.items():
            try:
                newIdles[room] = [idles[0] - idealCons[room]*idles[2], idles[1] - idealLibs[room]*idles[2]]
            except KeyError:
                newIdles[room] = [idles[0], idles[1]]
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



# TODO: fix makeRealRoomIdles() and plotTrueIdleDist() and tidy up idlePlotter()

excel = sa.StatAggregator('Report for Dr Stehr_Jean Walrand 2016.xlsx', max=1000)
ideals, roomIdles = calculateIdleStats(excel.procs)
# realRoomIdles = makeRealRoomIdles(roomIdles, ideals)
# plotTrueIdleDist(realRoomIdles)
roomPlots = idleDictsToTuples(roomIdles)
idlePlotter(excel, roomPlots)

