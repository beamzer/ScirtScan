#!/usr/bin/python3
import sqlite3
import argparse
import datetime
from datetime import date

html_table = ""

today = date.today()
dir = today.strftime("%Y%m%d")

parser = argparse.ArgumentParser(description='sql2html')

parser.add_argument(
    '-d','--debug',
    action='store_true',
    help='print debug messages to stderr'
)

args = parser.parse_args()
debug = args.debug

debug and print("debug output activated")

# Connect to the SQLite database
conn = sqlite3.connect('websites.db')

# Query the database and store the results in a dataframe
sql_query = ("SELECT websites, robots_check, headers_check, version_check, error_check, grade, grade_check, check_date FROM website_checks")
cs = conn.cursor()
try:
    cs.execute(sql_query)
    result = cs.fetchall()
except sqlite3.Error as error:
    print("Failed to fetch data from website_check", error)
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
 
    debugfile = dir + "/" + website + ".txt"
    html_table = html_table +  "<tr><td class=\"url\"><a href=\"" + debugfile + "\">" + website + "</a></td>"

    # https://www.freecodecamp.org/news/checkmark-symbol-html-for-checkmark-unicode/
    # https://www.howtocodeschool.com/2020/09/cross-symbols.html
    if robo_check == 0:
        html_table = html_table + "<td class=\"red\">" + "&#10006;" + "</td>"
    else:
        html_table = html_table + "<td class=\"green\">" + "&#x2705;" + "</td>"

    if head_check == 0:
        html_table = html_table + "<td class=\"red\">" + "&#10006;" + "</td>"
    else:
        html_table = html_table + "<td class=\"green\">" + "&#x2705;" + "</td>"

    if vers_check == 0:
        html_table = html_table + "<td class=\"red\">" + "&#10006;" + "</td>"
    else:
        html_table = html_table + "<td class=\"green\">" + "&#x2705;" + "</td>"

    if err_check == 0:
        html_table = html_table + "<td class=\"red\">" + "&#10006;" + "</td>"
    else:
        html_table = html_table + "<td class=\"green\">" + "&#x2705;" + "</td>"

    if grad_check == 0:
        html_table = html_table + "<td class=\"red\">" + "&#10006;" + "</td>"
    else:
        html_table = html_table + "<td class=\"green\">" + "&#x2705;" + "</td>"

    if grad_check == 0:
        html_table = html_table + "<td class=\"red\">"
    else:
        html_table = html_table + "<td class=\"green\">"
    html_table = html_table + grade + "</td>"

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
      <th>robots</th>
      <th>headers</th>
      <th>version</th>
      <th>error</th>
      <th>grade_check</th>
      <th>grade</th>
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

try:
    with open('index.html', 'w') as f:
        f.write(html_page)
except OSError as error:
    print(error)

debug and print("HTML table written to index.html")
