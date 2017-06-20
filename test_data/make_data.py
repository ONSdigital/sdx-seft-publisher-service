import xlsxwriter

for x in range(1000):
    workbook = xlsxwriter.Workbook('book{}.xlsx'.format(x))
    worksheet = workbook.add_worksheet()
    worksheet.write('A1', 'Hello, World!')
    workbook.close()
