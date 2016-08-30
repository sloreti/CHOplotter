import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
import copy

import statAggregator as sa

def calculateIdleStats(procs):
    """
    Inputs:
    procs - a list of at least one days worth of Procedure objects

    Outputs:
    roomCumIdles - a list of dicts, where keys are rooms and values are cumulative conservative idle time, cumulative
    liberal idle time, and number of idle intervals. Each dict is one day.
    """

    roomCumIdles = []
    roomCons = makeRoomsDict(procs)
    for r in roomCons.keys(): # make all rooms empty lists
        roomCons[r] = []
    roomLibs = copy.deepcopy(roomCons)

    i = 0
    while i < len(procs):

        currentDate = procs[i].date
        todaysProcs = []
        while i < len(procs) and procs[i].date == currentDate:
            todaysProcs.append(procs[i])
            i += 1

        idBlocks(todaysProcs)
        roomIdle = findIdles(todaysProcs, roomCons, roomLibs)
        roomCumIdles.append(roomIdle)


    idealCons, idealLibs = calculateIdealIdles(roomCons, roomLibs)

    return idealCons, idealLibs, roomCumIdles

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

def findIdles(procs, roomCons, roomLibs):
    """
    Inputs:
    procs - a list of exactly one days worth of Procedure objects

    Outputs:
    cons -
    libs -
    roomIdles - a dict where keys are rooms and values are liberal and conservative idle times. Represents one day.
    """

    # Group the procedures by room
    rooms = makeRoomsDict(procs)

    # Calculate idles
    roomIdles = {}
    for room, surgeries in rooms.items():
        surgeries.sort(key=lambda x: x.inRoom) # sort by real start time

        # sortedBySchedStart = sorted(surgeries, key=lambda x: x.schedStart) # sorted by sched start time
        # if surgeries != sortedBySchedStart: # TODO: remove after more thorough debugging
        #     print "oops"

        cons = []
        libs = []
        for i, surgery in enumerate(surgeries[1:]):
            if surgery.blockId == surgeries[i].blockId:
                # must be datetimes, not time objects, for subtraction
                inRoom = dt.datetime.combine(dt.datetime(1,1,1), surgery.inRoom)
                prevProcEnd = dt.datetime.combine(dt.datetime(1,1,1), surgeries[i].procEnd)
                prevOutRoom = dt.datetime.combine(dt.datetime(1,1,1), surgeries[i].outRoom)

                cons.append(inRoom - prevOutRoom)
                libs.append(inRoom - prevProcEnd)

        cons = [c.seconds / 60 for c in cons] # convert to int in minutes
        libs = [l.seconds / 60 for l in libs] # convert to int in minutes
        cumCon = sum(cons)
        cumLib = sum(libs)
        roomIdles[room] = [cumCon, cumLib, len(cons)]

        roomCons[room].extend(cons)
        roomLibs[room].extend(libs)

    return roomIdles


def calculateIdealIdles(roomCons, roomLibs, percentileToAvg=-1):
    """
    Inputs:
    roomCons - Dict. Keys are rooms, values are lists of individual idle times in minutes
    roomLibs - Dict. Keys are rooms, values are lists of individual idle times in minutes
    percentileToAvg - Float. A value of 0.1 will average the fastest 10% of idle times. Values < 0 or > 1 will use
    only the fastest time

    Outputs:
    idealCons - Dict. Keys are rooms, values are estimated ideal cleaning times
    idealLibs - Dict. Keys are rooms, values are estimated ideal cleaning times
    """

    idealCons = {}
    idealLibs = {}
    for room in roomCons:

        # skip rooms that have no idle times (usually PICU or NICU)
        if not roomCons[room]:
            continue

        # room will be in both dicts
        roomCons[room].sort()
        roomLibs[room].sort()

        if percentileToAvg > 1 or percentileToAvg < 0:
            idealCons[room] = roomCons[room][0]
            idealLibs[room] = roomLibs[room][0]
        else:
            upperIndex = int(len(roomCons[room]) * percentileToAvg) - 1
            conMean =  sum(roomCons[room][0:upperIndex]) / (upperIndex+1)
            libMean =  sum(roomLibs[room][0:upperIndex]) / (upperIndex+1)
            idealCons[room] = conMean
            idealLibs[room] = libMean

    return idealCons, idealLibs


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
    dictsOfIdles - a list of dicts, where keys are rooms and values are liberal and conservative idle times. Each dict is one day.

    Outputs:
    roomPlots - a list of plottable 3-tuples. First value is rooms, second is conservative idle time, third is liberal idle time
    """

    roomPlots = []
    for d in dictsOfIdles:
        items = d.items()
        rooms = [i[0] for i in items]
        conservatives = [i[1][0] for i in items]
        liberals = [i[1][1] for i in items]
        roomPlots.append((rooms, conservatives, liberals))

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
            conservatives = roomPlots[curr_pos[0]][1]
            liberals = roomPlots[curr_pos[0]][2]
            ind = np.arange(len(rooms))
            width = 0.2

            rects1 = ax.bar(ind, conservatives, width, color='r')
            rects2 = ax.bar(ind + width, liberals, width, color='y')

            ax.set_xticks(ind + width / 2)
            ax.set_xticklabels(rooms, rotation=90)
            ax.set_title(currDay)
            ax.legend((rects1[0], rects2[0]), ('conservative', 'liberal'))
            fig.canvas.draw()
        return key_event

    fig = plt.figure()
    fig.canvas.mpl_connect('key_press_event', callback())
    ax = fig.add_subplot(111)

    rooms = roomPlots[0][0]
    conservatives = roomPlots[0][1]
    liberals = roomPlots[0][2]
    currDay = excel.procs[0].date.isoformat()[:10]
    ind = np.arange(len(rooms))
    width = 0.2

    rects1 = ax.bar(ind, conservatives, width, color='r')
    rects2 = ax.bar(ind + width, liberals, width, color='y')

    ax.set_xticks(ind + width / 2)
    ax.set_xticklabels(rooms, rotation=90)
    ax.set_title(currDay)
    ax.legend((rects1[0], rects2[0]), ('conservative', 'liberal'))
    ax.set_ylabel('Minutes')
    plt.show()

def makeRealRoomIdles(roomIdles, idealCons, idealLibs):

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






excel = sa.StatAggregator('Report for Dr Stehr_Jean Walrand 2016.xlsx', max=1000)
idealCons, idealLibs, roomIdles = calculateIdleStats(excel.procs)
# realRoomIdles = makeRealRoomIdles(roomIdles, idealCons, idealLibs)
# plotTrueIdleDist(realRoomIdles)
roomPlots = idleDictsToTuples(roomIdles)
idlePlotter(excel, roomPlots)

