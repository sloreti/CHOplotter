#!/usr/bin/env python 

import datetime as dt
import openpyxl
import time


class Procedure(object):
    """docstring for Procedure"""

    def __init__(self, procParams):

        self.date = procParams.date
        self.day = procParams.day
        self.schedStart = self.toDateTime(procParams.schedStart)
        self.schedEnd = self.toDateTime(procParams.schedEnd)
        self.schedLength = self.toDateTime(procParams.schedLength, delta=True)
        self.inRoom = self.toDateTime(procParams.inRoom)
        self.ready = self.toDateTime(procParams.ready)
        self.procStart = self.toDateTime(procParams.procStart)
        self.procEnd = self.toDateTime(procParams.procEnd)
        self.outRoom = self.toDateTime(procParams.outRoom)
        self.procDuration = self.toDateTime(procParams.procDuration, delta=True)
        self.roomDuration = self.toDateTime(procParams.roomDuration, delta=True)
        self.room = procParams.room
        self.loc = procParams.loc
        self.logNum = procParams.logNum
        self.outRoomStraddledMidnight = self.outRoom < self.inRoom
        self.procEndStraddledMidnight = self.procEnd < self.inRoom


        self.ensureAllEntriesCorrect(procParams)
        # self.calculateDelays()


    def ensureAllEntriesCorrect(self, procParams):
        self.durationsAreCorrect(procParams)
        self.dayIsCorrect(procParams)
    
    def toDateTime(self, s, delta=False):
        if s:
            s = int(s)
            if not delta:
                return dt.time(s/100, s%100) # (hours, minutes)
            else:
                return dt.timedelta(minutes = s)
        else:
            return None
        
    def durationsAreCorrect(self, procParams):

        allDursGood = True
        durations = [(procParams.schedStart, procParams.schedEnd, procParams.schedLength), 
                    (procParams.inRoom, procParams.outRoom, procParams.roomDuration), 
                    (procParams.procStart, procParams.procEnd, procParams.procDuration)]
        for dur in durations:
            try:
                startHour, endHour = dur[0] / 100, dur[1] / 100
                if (endHour < startHour): # if procedure went from one day to the next
                    endHour = (24 - startHour) + endHour
                    startHour = 0

                startMin, endMin = dur[0] % 100, dur[1] % 100
                calculatedDur = (endMin - startMin) + (endHour - startHour)*60
                if calculatedDur != dur[2]:
                    allDursGood = False
                    print "Procedure " + str(self.logNum) + " has an incorrect duration length"
            except TypeError as e:
                print "Procedure " + str(self.logNum) + ": " +  e.message

        return allDursGood

    def dayIsCorrect(self, procParams):
        days = {'Mon':0, 'Tue':1, 'Wed':2, 'Thu':3, 'Fri':4, 'Sat':5, 'Sun':6}
        if days[procParams.day] != self.date.weekday():
            print "Procedure " + str(self.logNum) + " has an incorrectly labeled day"
            return False
        else:
            return True

    def calculateDelays(self):

        if self.schedStart and self.procStart:
            start = dt.datetime.combine(self.date, self.schedStart)
            if (self.schedStart > self.procStart): # if procedure started the next day TODO: might need to be improved
                finish = dt.datetime.combine(self.date + dt.timedelta(days=1), self.procStart)
            else:
                finish = dt.datetime.combine(self.date, self.procStart)
            delta  = finish - start
            self.delayedStart = delta.total_seconds() / 60 # minutes
            if self.delayedStart > 600:
                print "hmmmm"
        else:
            self.delayedStart = 0


class ProcedureParams(object):
    """docstring for ProcedureParams"""
    def __init__(self, row):
        self.date = row[1].value
        self.day = row[2].value
        self.schedStart = row[5].value
        self.schedEnd = row[6].value
        self.schedLength = row[7].value
        self.inRoom = row[8].value
        self.ready = row[9].value
        self.procStart = row[10].value
        self.procEnd = row[11].value
        self.outRoom = row[12].value
        self.procDuration = row[13].value
        self.roomDuration = row[14].value
        self.room = row[15].value
        self.loc = row[16].value
        self.logNum = row[18].value

class StatAggregator(object):

    def __init__(self, excel, min = None , max = None):

        start = time.clock()
        wb = openpyxl.load_workbook(excel)
        sheet = wb.worksheets[0]
        finish = time.clock()
        print "Loading workbook took " + str(finish - start) + " seconds"

        # check if -m and -M args were row nums or dates
        rowArgs = False
        dateArgs = False
        try:
            minRow = int(min) if min else -float("inf")
            maxRow = int(max) if max else float("inf")
            rowArgs = True
        except ValueError:
            minDate = dt.datetime.strptime(min, '%m/%d/%y') if min else dt.date(dt.MINYEAR,1,1) # TODO: Should probably check if valid str
            maxDate = dt.datetime.strptime(max, '%m/%d/%y') if max else dt.date(dt.MAXYEAR,1,1)
            dateArgs = True

        self.procs = []
        self.dates = []

        for i, row in enumerate(sheet.rows[1:]): # skip first row of data labels
            params = ProcedureParams(row)
            if dateArgs and (params.date and params.date >= minDate and params.date <= maxDate)\
                    or rowArgs and (params.date and i+1 >= minRow and i+1 <=maxRow): # +1 because data starts on 2nd row
                proc = Procedure(params)

                if proc.schedStart: # disregard procs without scheduled start times
                    self.procs.append(proc)
                    # self.delayedStarts.append(proc.delayedStart)
                    self.dates.append(proc.date)
