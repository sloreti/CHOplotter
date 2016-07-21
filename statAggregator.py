#!/usr/bin/env python 

import openpyxl

import matplotlib.pyplot as plt
plt.plot([1,2,3,4])
plt.ylabel('some numbers')
plt.show()

# surgeries = {}

# wb = openpyxl.load_workbook('ProceduresData.xlsx')
# sheet = wb.active
# addons = 0

# for row in sheet.rows:
#     surgery = row[0].value
#     if surgery == 'Yes':
#         addons += 1

# for i in surgeries.iteritems():
#     print i

print float(addons)/len(sheet.rows)
