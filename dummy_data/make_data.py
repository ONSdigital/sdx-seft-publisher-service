import xlsxwriter

for x in range(111, 222):
    workbook = xlsxwriter.Workbook('book{}.xlsx'.format(x))
    worksheet = workbook.add_worksheet()
    worksheet.write('A1', 'Hello, World!')
    workbook.close()
