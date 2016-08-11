import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
import time

import statAggregator as sa

def calculateIdles(procs):
    """
    Inputs:
    procs - a list of at least one days worth of Procedure objects

    Outputs:
    dailyIdles - a list of total idle time per day, in minutes
    """

    dailyIdlesConservative = []
    dailyIdlesLiberal = []
    i = 0
    while i < len(procs):

        currentDate = procs[i].date
        todaysProcs = []
        while i < len(procs) and procs[i].date == currentDate:
            todaysProcs.append(procs[i])
            i += 1

        idBlocks(todaysProcs)
        inRoomMinusProcEnds, inRoomMinusOutRooms = findIdles(todaysProcs)
        dailyIdlesConservative.append(sum(inRoomMinusOutRooms, dt.timedelta()))
        dailyIdlesLiberal.append(sum(inRoomMinusProcEnds, dt.timedelta()))

    print "Done"
    conservativeMins = [x.seconds / 60 for x in dailyIdlesConservative]
    liberalMins = [x.seconds / 60 for x in dailyIdlesLiberal]
    return conservativeMins, liberalMins

def idBlocks(procs):
    """
    Inputs:
    procs - a list of exactly one days worth of Procedure objects

    TODO: description of idBlocks
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
    idles - a list of all idle durations, in minutes
    """

    # Group the procedure start and end times by room
    rooms = {}
    for proc in procs:
        if proc.room in rooms:
            rooms[proc.room].append(proc)
        else:
            rooms[proc.room] = [proc]

    # Calculate idles
    inRoomMinusProcEnds = []
    inRoomMinusOutRooms = []
    for room, surgeries in rooms.items():
        surgeries.sort(key=lambda x: x.inRoom) # sort by real start time
        sortedBySchedStart = sorted(surgeries, key=lambda x: x.schedStart) # sorted by sched start time
        if surgeries != sortedBySchedStart:
            print "oops"

        for i, surgery in enumerate(surgeries[1:]):
            if surgery.blockId == surgeries[i].blockId:
                # must be datetimes, not time objects, for subtraction
                inRoom = dt.datetime.combine(dt.datetime(1,1,1), surgery.inRoom)
                prevProcEnd = dt.datetime.combine(dt.datetime(1,1,1), surgeries[i].procEnd)
                prevOutRoom = dt.datetime.combine(dt.datetime(1,1,1), surgeries[i].outRoom)

                inRoomMinusProcEnds.append(inRoom - prevProcEnd)
                inRoomMinusOutRooms.append(inRoom - prevOutRoom)

    return inRoomMinusProcEnds, inRoomMinusOutRooms



start = time.clock()
excel = sa.StatAggregator('ProceduresData.xlsx', max=1000)
finish = time.clock()
print "Loading excel took " + str(finish - start) + " seconds"

start = time.clock()
dailyIdlesConservative, dailyIdlesLiberal = calculateIdles(excel.procs)
finish = time.clock()
print "calculateIdles() took " + str(finish - start) + " seconds"

ind = np.arange(len(dailyIdlesConservative))  # the x locations for the groups
width = 0.2      # the width of the bars

fig, ax = plt.subplots()
rects1 = ax.bar(ind, dailyIdlesConservative, width, color='r')
rects2 = ax.bar(ind + width, dailyIdlesLiberal, width, color='y')

# add some text for labels, title and axes ticks
ax.set_ylabel('Minutes')
ax.set_title('Idle Minutes')
ax.set_xticks(ind + width/2)
dateRange = [(excel.procs[0].date + dt.timedelta(days=d)).isoformat()[:10] for d in range(len(dailyIdlesConservative))]
ax.set_xticklabels(dateRange, rotation=90)

ax.legend((rects1[0], rects2[0]), ('conservative', 'liberal'))
plt.show()