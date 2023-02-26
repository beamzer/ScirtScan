#!/usr/bin/env python3
import sqlite3
import argparse
import os
#import datetime
from datetime import date
import openpyxl
from openpyxl.styles import Font, PatternFill

today = date.today()
dir = today.strftime("%Y%m%d")

parser = argparse.ArgumentParser(description='creates an index.html page from the sqlite database websites.db')

parser.add_argument(
    '-d','--debug',
    action='store_true',
    help='print debug messages to stderr'
    )

parser.add_argument(
    '-p', '--path', 
    type=str, 
    help=f'The directory path, if not given will assume the directory with todays date: {dir}'
    )

parser.add_argument(
    '-m', '--mail', 
    type=str,
    help='e-mail address to send the Excel file to'
    )

args = parser.parse_args()
debug = args.debug

# If the path argument is provided, use it as the directory path
if args.path:
    directory_path = args.path
else:
    # If the path argument is not provided, set the directory name to today's date
    directory_path = dir

debug and print("debug output activated")
debug and print(f"Will read from, and store into directory: {directory_path}")

# Check if the directory exists
if not os.path.exists(directory_path):
    print(f"The directory {directory_path} does not exist.")
    exit()

# Connect to the SQLite database in the directory
try:
    conn = sqlite3.connect(os.path.join(directory_path, 'websites.db'))
    debug and print(f"Connected to database {os.path.join(directory_path, 'websites.db')}")
except sqlite3.Error as e:
    print(f"Error connecting to database: {e}")


# Retrieve data from the database
cursor = conn.cursor()
cursor.execute('SELECT * FROM website_checks')
rows = cursor.fetchall()

# Create a new workbook and worksheet
workbook = openpyxl.Workbook()
worksheet = workbook.active

# Define cell styles for headers, OK values, and NotOK values
header_style = Font(bold=True)
value_ok_style = PatternFill(start_color='00FF89', end_color='00FF89', fill_type='solid')
value_notok_style = PatternFill(start_color='FF0000', end_color='FF0000', fill_type='solid')

# Write the header row
# table_headers = ['websites', 'robots_check', 'headers_check', 'version_check', 'error_check', 'grade', 'grade_check', 'check_date', 'security_txt']
# switching the last two colums:
table_headers = ['websites', 'robots_check', 'headers_check', 'version_check', 'error_check', 'grade', 'grade_check', 'security_txt', 'check_date']

for col, header in enumerate(table_headers):
    worksheet.cell(row=1, column=col+1, value=header).font = header_style
    worksheet.column_dimensions[openpyxl.utils.get_column_letter(col+1)].width = 15

# Write the data rows with appropriate styles
for row, data in enumerate(rows):
    for col, value in enumerate(data):
        debug and print(f"row = {row}, col = {col}, value = {value}")
        if col == 8:            # because the last two colums are switched
             col = 7
        elif col == 7: 
             col = 8
           
        cell = worksheet.cell(row=row+2, column=col+1, value=value)
        # if col in [1, 2, 3, 4, 6, 8]:
        if col in [1, 2, 3, 4, 6, 7]: # adjust for the switched columns ( check_date is a string )
            if value == 1:
                cell.fill = value_ok_style
                cell.value = 'OK'
            else:
                cell.fill = value_notok_style
                cell.value = 'NotOK'

# Save the excel workbook
excelfile = os.path.join(directory_path, 'website_checks.xlsx')
try:
    workbook.save(excelfile)
    debug and print(f"saving to: {excelfile}")
except OSError as e:
    print(f"Error saving excel file: {e}")

# If the -m switch was specified, e-mail the Excel file to the specified address
# N.B. this has to be modified to your specific situation before it will actually send an e-mail
if args.mail:
    msg = MIMEMultipart()
    msg['From'] = 'sender@example.com'
    msg['To'] = args.mail
    msg['Subject'] = 'Website Checks Report'
    with open(excelfile, 'rb') as f:
        attach = MIMEApplication(f.read(), _subtype = 'xls')
        attach.add_header('Content-Disposition', 'attachment', filename='website_checks.xlsx')
        msg.attach(attach)
    smtp = smtplib.SMTP('smtp.gmail.com', 587)
    smtp.starttls()
    smtp.login('sender@example.com', 'password')        # N.B. be very careful with putting passwords in scripts
    smtp.sendmail('sender@example.com', args.mail, msg.as_string())
    smtp.quit()
