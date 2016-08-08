import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

import numpy as np

def main(rooms):
    data = generate_data(len(rooms))
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.tick_params(axis='both', labelsize=10)
    calendar_heatmap(ax, data, rooms)
    plt.show()

def generate_data(numRooms):
    data = np.random.randint(0, 20, 48*numRooms)
    return data

def calendar_heatmap(ax, data, rooms):

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

main(['MOR 1','MOR 2','MOR 3','MOR 4','MOR 5','MOR 6','OPC 1','OPC 2','OPC 3'])