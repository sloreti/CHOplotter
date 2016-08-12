import numpy as np
import matplotlib.pyplot as plt
import datetime as dt

import statAggregator as sa

def calculateIdles(procs):
    """
    Inputs:
    procs - a list of at least one days worth of Procedure objects

    Outputs:
    dailyIdles - a list of total idle time per day, in minutes
    roomIdles - a list of dicts, where keys are rooms and values are liberal and conservative idle times. Each dict is one day.
    """

    dailyIdlesConservative = []
    dailyIdlesLiberal = []
    roomIdles = []
    i = 0
    while i < len(procs):

        currentDate = procs[i].date
        todaysProcs = []
        while i < len(procs) and procs[i].date == currentDate:
            todaysProcs.append(procs[i])
            i += 1

        idBlocks(todaysProcs)
        inRoomMinusProcEnds, inRoomMinusOutRooms, roomIdle = findIdles(todaysProcs)
        dailyIdlesConservative.append(sum(inRoomMinusOutRooms, dt.timedelta()))
        dailyIdlesLiberal.append(sum(inRoomMinusProcEnds, dt.timedelta()))
        roomIdles.append(roomIdle)


    conservativeMins = [x.seconds / 60 for x in dailyIdlesConservative]
    liberalMins = [x.seconds / 60 for x in dailyIdlesLiberal]
    return conservativeMins, liberalMins, roomIdles

def idBlocks(procs):
    """
    Inputs:
    procs - a list of exactly one days worth of Procedure objects

    idBlocks() adds a blockId field to each procedure, identifying which block the procedure belongs to. Indexing
    starts at 0 every day, so only useful for looking at blocks within the same day.
    """

    # Group the procedure start and end times by room
    rooms = {}
    for proc in procs:
        if proc.room in rooms:
            rooms[proc.room].append(proc)
        else:
            rooms[proc.room] = [proc]

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

def findIdles(procs):
    """
    Inputs:
    procs - a list of exactly one days worth of Procedure objects

    Outputs:
    inRoomMinusProcEnds -
    inRoomMinusProcEnds -
    roomIdles - a dict where keys are rooms and values are liberal and conservative idle times. Repersents one day.
    """

    # Group the procedure start and end times by room
    rooms = {}
    for proc in procs:
        if proc.room in rooms:
            rooms[proc.room].append(proc)
        else:
            rooms[proc.room] = [proc]

    # Calculate idles
    roomIdles = {}
    inRoomMinusProcEnds = []
    inRoomMinusOutRooms = []
    for room, surgeries in rooms.items():
        surgeries.sort(key=lambda x: x.inRoom) # sort by real start time

        # sortedBySchedStart = sorted(surgeries, key=lambda x: x.schedStart) # sorted by sched start time
        # if surgeries != sortedBySchedStart: # TODO: remove after more thorough debugging
        #     print "oops"

        roomIdleCon = []
        roomIdleLib = []
        for i, surgery in enumerate(surgeries[1:]):
            if surgery.blockId == surgeries[i].blockId:
                # must be datetimes, not time objects, for subtraction
                inRoom = dt.datetime.combine(dt.datetime(1,1,1), surgery.inRoom)
                prevProcEnd = dt.datetime.combine(dt.datetime(1,1,1), surgeries[i].procEnd)
                prevOutRoom = dt.datetime.combine(dt.datetime(1,1,1), surgeries[i].outRoom)

                roomIdleLib.append(inRoom - prevProcEnd)
                roomIdleCon.append(inRoom - prevOutRoom)

        roomIdleCon = sum(roomIdleCon, dt.timedelta())
        roomIdleLib = sum(roomIdleLib, dt.timedelta())
        inRoomMinusProcEnds.append(roomIdleLib)
        inRoomMinusOutRooms.append(roomIdleCon)
        roomIdleCon = roomIdleCon.seconds / 60 # convert to int in minutes
        roomIdleLib = roomIdleLib.seconds / 60 # convert to int in minutes
        roomIdles[room] = [roomIdleCon, roomIdleLib]

    return inRoomMinusProcEnds, inRoomMinusOutRooms, roomIdles


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



excel = sa.StatAggregator('Report for Dr Stehr_Jean Walrand 2016.xlsx', max=1000)
roomIdles = calculateIdles(excel.procs)[2]
roomPlots = idleDictsToTuples(roomIdles)
idlePlotter(excel, roomPlots)

