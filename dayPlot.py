import datetime as dt
import argparse

import statAggregator as sa
import calculateIdles as ci


def groupProcsByDay(procs):

    dayList = []
    i = 0
    while i < len(procs): # Because i is incremented in inner loop, this outer while loop is iterated once per day

        currentDate = procs[i].date
        todaysProcs = []
        while i < len(procs) and procs[i].date == currentDate:
            todaysProcs.append(procs[i])
            i += 1
        dayList.append(todaysProcs)
    return dayList

def dayPlot(curr_pos = 0, plots = None, ax=None):

    barSpacing = 12
    barWidth = 4

    procs = plots[curr_pos]
    if procs:
        currDay = procs[0].date.isoformat()[:10]
    else:
        currDay = "No Procedures"

    # Group the procedures by room
    rooms = ci.makeRoomsDict(procs)

    earliest = min(min([proc.schedStart.hour * 60 + proc.schedStart.minute for proc in procs]),
                   min([proc.inRoom.hour * 60 + proc.inRoom.minute for proc in procs]))
    latest = max(max([proc.schedEnd.hour * 60 + proc.schedEnd.minute for proc in procs]),
                   max([proc.outRoom.hour * 60 + proc.outRoom.minute for proc in procs]))

    for i, (room, l) in enumerate(rooms.items()):
        schedTimes = [(proc.schedStart.hour * 60 + proc.schedStart.minute, proc.schedLength.seconds/60) for proc in l]
        inOutTimes = [(proc.inRoom.hour * 60 + proc.inRoom.minute, proc.roomDuration.seconds/60) for proc in l]
        procTimes = [(proc.procStart.hour * 60 + proc.procStart.minute, proc.procDuration.seconds/60) for proc in l]
        ax.broken_barh(schedTimes, (barSpacing * i + barWidth + 1, barWidth), facecolors='#66b3ff')
        ax.broken_barh(inOutTimes, (barSpacing * i + (barWidth + 1) * 2, barWidth), facecolors='#ffcc99')
        ax.broken_barh(procTimes, (barSpacing * i + (barWidth + 1) * 2, barWidth), facecolors='#e67300')

    ax.set_ylim(0, len(rooms) * barSpacing + (barWidth + 1) * 3)
    ax.set_xlabel('Hour')
    ax.set_ylabel('Room')
    ax.set_yticks([barSpacing * i + (barWidth + 1) * 2 for i in range(len(rooms))])
    ax.set_yticklabels(rooms.keys())
    halfHourList = [30*i for i in range(48)]
    ax.set_xticks(halfHourList)
    ax.set_xticklabels([str(h/60) + ':' + str(h%60).zfill(2)  for h in halfHourList], rotation=90)
    ax.set_xlim(earliest - 30, latest + 30)
    ax.set_title(currDay)
    ax.grid(True)



def parseInputs():
    parser = argparse.ArgumentParser(description="Query excel file for days with daily cumulative \"real\" idle time "
                                                 "over a threshold")
    parser.add_argument("filename", help="Excel file to read surgery data from")
    parser.add_argument("-m", "--min", help="Row to start processing excel data", required=True) # TODO: change to dates
    parser.add_argument("-M", "--max", help="Row to finish processing excel data", required=True) # TODO: change to dates
    args = parser.parse_args()

    excel = sa.StatAggregator(args.filename, min=args.min, max=args.max)  # TODO: ensure valid file name and exists
    dayList = groupProcsByDay(excel.procs)
    ci.flipThruPlotter(dayPlot, dayList)

parseInputs()