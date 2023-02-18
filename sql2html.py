#!/usr/bin/env python3
import sqlite3
import argparse
import os
import datetime
from datetime import date


html_table = ""

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
    help='The directory path, if not given will assume the directory with todays date: YYYYMMDD'
    )

args = parser.parse_args()
debug = args.debug

# If the path argument is provided, use it as the directory path
if args.path:
    directory_path = args.path
else:
    # If the path argument is not provided, set the directory name to today's date
    directory_path = today.strftime('%Y%m%d')

debug and print("debug output activated")
debug and print(f"Will read from, and store into directory: {directory_path}")

# Check if the directory exists
if not os.path.exists(directory_path):
    print(f"The directory {directory_path} does not exist.")
    exit()

# Connect to the SQLite database in the directory
try:
    conn = sqlite3.connect(os.path.join(directory_path, 'websites.db'))
    debug and print(f"Connected to database {os.path.join(directory_path, 'websites.db')}.")
except sqlite3.Error as e:
    print(f"Error connecting to database: {e}")

# Query the database and store the results in a dataframe
sql_query = ("SELECT websites, robots_check, headers_check, version_check, error_check, grade, grade_check, check_date FROM website_checks")
cs = conn.cursor()
try:
    cs.execute(sql_query)
    result = cs.fetchall()
except sqlite3.Error as error:
    print("Failed to fetch data from websites.db", error)
for row in result:
    debug and print(row)
    website = row[0]
    robo_check = row[1]
    head_check = row[2]
    vers_check = row[3]
    err_check  = row[4]
    grade = row[5]
    grad_check = row[6]
    date_check = row[7]
    debug and print(date_check, website, robo_check, head_check, vers_check, err_check, grad_check, grade)
 
    # debugfile = dir + "/" + website + ".txt"
    debugfile = website + ".txt"
    html_table = html_table +  "<tr><td class=\"url\"><a href=\"" + debugfile + "\">" + website + "</a></td>"

    # https://www.freecodecamp.org/news/checkmark-symbol-html-for-checkmark-unicode/
    # https://www.howtocodeschool.com/2020/09/cross-symbols.html

    if grad_check == 1:
        html_table = html_table + "<td class=\"white\">"   # white for better readability
    elif grad_check == 0:
        html_table = html_table + "<td class=\"red\">"
    else:
        html_table = html_table + "<td class=\"orange\">"
    vtgradelink = '<a href="https://www.ssllabs.com/ssltest/analyze.html?d=' + website + '&hideResults=on">' + grade + '</a>'
    html_table = html_table + vtgradelink + "</td>"

    if grad_check == 1:
        html_table = html_table + "<td class=\"green\">" + "&#x2705;" + "</td>"
    elif grad_check == 0:
        html_table = html_table + "<td class=\"red\">" + "&#10006;" + "</td>"
    else:
        html_table = html_table + "<td class=\"orange\">" + "&quest;" + "</td>"

    if head_check == 1:
        html_table = html_table + "<td class=\"green\">" + "&#x2705;" + "</td>"
    elif head_check == 0:
        html_table = html_table + "<td class=\"red\">" + "&#10006;" + "</td>"
    else:
        html_table = html_table + "<td class=\"orange\">" + "&quest;" + "</td>"

           
    if robo_check == 1:
        html_table = html_table + "<td class=\"green\">" + "&#x2705;" + "</td>"
    elif robo_check == 0:
        html_table = html_table + "<td class=\"red\">" + "&#10006;" + "</td>"
    else:
        html_table = html_table + "<td class=\"orange\">" + "&quest;" + "</td>"

    if vers_check == 1:
        html_table = html_table + "<td class=\"green\">" + "&#x2705;" + "</td>"
    elif vers_check == 0:
        html_table = html_table + "<td class=\"red\">" + "&#10006;" + "</td>"
    else:
        html_table = html_table + "<td class=\"orange\">" + "&quest;" + "</td>"

    if err_check == 1:
        html_table = html_table + "<td class=\"green\">" + "&#x2705;" + "</td>"
    elif err_check == 0:
        html_table = html_table + "<td class=\"red\">" + "&#10006;" + "</td>"
    else:
        html_table = html_table + "<td class=\"orange\">" + "&quest;" + "</td>"


    html_table = html_table + "<td>" + date_check + "</td>"
    html_table = html_table + "</td></tr>\n"

# Close the connection to the database
conn.close()

with open('styles.css', 'r') as f:
    css_styles = f.read()
    
# Create the complete HTML page
html_page = """
<!DOCTYPE html>
<html>
<head>
    <title>My HTML Table</title>
    <style>
    {}
    </style>
</head>
<body>
    <table border="1" class="dataframe mystyle" id="table">
  <thead>
    <tr style="text-align: right;">
      <th>website</th>
      <th>grade</th>
      <th>grade_check</th>
      <th>headers</th>
      <th>robots</th>
      <th>version</th>
      <th>error</th>
      <th>check date</th>
    </tr>
  </thead>
  <tbody>
    {}
  </tbody>
  </table>
</body>
</html>
""".format(css_styles, html_table)

myindex = directory_path + "/" + "index.html"
try:
    with open(myindex, 'w') as f:
        f.write(html_page)
except OSError as error:
    print(error)

print(f"HTML table written to {myindex}")
