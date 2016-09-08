# Ripped from http://stackoverflow.com/questions/32485907/matplotlib-and-numpy-create-a-calendar-heatmap

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

import statAggregator as sa

def main(rooms, excel):
    data = generate_data(rooms, excel)
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.tick_params(axis='both', labelsize=10)
    calendar_heatmap(ax, data, rooms)
    plt.show()

def generate_data(rooms, excel):
    data = np.nan * np.zeros((len(rooms), 48))

    datesSchedStarts = []
    datesSchedEnds = []
    datesRooms = []
    date = excel.procs[0].date
    row = 0
    while True:
        proc = excel.procs[row]
        if proc.date == date:
            datesSchedStarts.append(proc.schedStart)
            datesSchedEnds.append(proc.schedEnd)
            datesRooms.append(proc.room)
        else:
            break
        row += 1

    for i, start in enumerate(datesSchedEnds):
        roomIndex = rooms.index(datesRooms[i])
        startIndex, endIndex = datetimeToIndex(start, datesSchedEnds[i])
        data[roomIndex, startIndex:endIndex] = 1

    return data

def datetimeToIndex(start, end):
    startIndex = start.hour*2 + (start.minute >= 30)
    endIndex = end.hour * 2 + (end.minute >= 30)
    return startIndex, endIndex

def calendar_array(rooms, data):

    calendar = np.nan * np.zeros((len(rooms), 48))
    calendar[i, j] = data
    return i, j, calendar

def calendar_heatmap(ax, data, rooms):
    im = ax.imshow(data, interpolation='none', cmap='summer')
    label_days(ax)
    label_months(ax, rooms)

def label_days(ax):

    ax.set(xticks=np.arange(49))
    ax.set_xticklabels([str(hour) + min for hour in range(24) for min in (':00',':30')],
                       rotation=90)

def label_months(ax, rooms):

    ax.set(yticks=np.arange(len(rooms)+1))

    # Hide major tick labels
    ax.yaxis.set_major_formatter(ticker.NullFormatter())

    # Customize minor tick labels
    ax.yaxis.set_minor_locator(ticker.FixedLocator([i + .5 for i in range(len(rooms))]))
    ax.yaxis.set_minor_formatter(ticker.FixedFormatter(rooms))

excel = sa.StatAggregator('ProceduresData.xlsx')
main(['MOR 1','MOR 2','MOR 3','MOR 4','MOR 5','MOR 6','OPC 1','OPC 2','OPC 3'], excel)