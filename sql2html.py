#!/usr/bin/env python3
import sqlite3
import argparse
import os
import sys
import datetime
import re
from datetime import date

# for this to display and work (sort) properly, sort.js and styles.css need to be in the directory above index.html
version = "v2.1e, 20230817"

html_table = ""

today = date.today()
dir = today.strftime("%Y%m%d")

parser = argparse.ArgumentParser(description='creates an index.html page from the sqlite database websites.db')
parser.add_argument('-d','--debug', action='store_true', help='print debug messages to stderr')
parser.add_argument('-p', '--path', type=str, help=f'The directory path, if not given will assume the directory with todays date: {dir}')
parser.add_argument('-v','--version', action='store_true', help='show version info and exit')

args = parser.parse_args()
debug = args.debug

if args.version:
    sys.exit(f"version: {version}")

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
    database = os.path.join(directory_path, 'websites.db')
    conn = sqlite3.connect(database)
    debug and print(f"Connected to database {database}.")
    c = conn.cursor()
except sqlite3.Error as e:
    sys.exit(f"Error connecting to database {database}: {e}")

# Define the HTML table headers as a list, in the order they should appear on the webpage
table_headers = ['website',
                 'https',
                 'grade', 
                 'grade<br>check',
                 'HTTPS<br>redirect',
                 'cert<br>validity',
                 'HSTS<br>(days)',
                 'headers', 
                 'security<br>.txt', 
                 'robots<br>.txt', 
                 'version', 
                 'error', 
                 'remnants',
                 'debug',
                 'check date']

# Using a loop to construct the header row
count=0
# header_row = '<tr style="text-align: right;">'
# for header in table_headers:
#         header_row += f'<th onclick="sortTable({count})">{header}'
#         header_row += '<div class="explanation">click to sort</div></th>'
#         count += 1
# header_row += '</tr>'


# Query the table structure from the meta table
c.execute("SELECT structure FROM meta")
result = c.fetchone()

if result:
    table_structure = result[0]
    debug and print(f"Table structure: {table_structure}")

    # Extract column names from the table structure
    column_pattern = re.compile(r'(\w+)\s+[\w\(\)]+(,)?')
    columns = [match.group(1) for match in column_pattern.finditer(table_structure) if match.group(1) != "IF"]

    # Build the SQL query
    sql_query = "SELECT {} FROM website_checks".format(", ".join(columns))
    debug and print(f"sql_query = {sql_query}")
else:
    sys.exit(f"unable to read database structure from {database}")

cs = conn.cursor()
try:
    cs.execute(sql_query)
    result = cs.fetchall()
except sqlite3.Error as error:
    sys.exit(f"Failed to fetch data from {database}", error)

for row in result:
    debug and print(row)
    website = row[0]
    https_check = row[1]
    grade = row[2]
    grad_check = row[3]
    redirect_check = row[4]
    cert_valid = row[5]
    hsts = row[6]
    head_check = row[7]
    security_txt = row[8]
    robo_check = row[9]
    vers_check = row[10]
    err_check  = row[11]
    remnants = row[12]
    debug = row[13]
    date_check = row[14]
        
    debug and print(date_check, website, https_check, grad_check, grade, redirect_check, cert_valid, hsts, head_check, security_txt, robo_check, vers_check, err_check, remnants, debug)
 
    debugfile = f'{website}.txt'
    html_table += f'<tr><td><a class="check" href=https://{website}>{website}</a></td>'

    if https_check == 1:
        html_table += '<td class="green">&#x2705;</td>'
    elif https_check == 0:
        html_table += '<td class="red">&#10006;</td>'
    else:
        html_table += '<td class="orange"><b>&quest;</b></td>'

    if grad_check == 1:
        html_table += '<td class="green">'
        vtgradelink = f'<a href="https://www.ssllabs.com/ssltest/analyze.html?d={website}&hideResults=on">{grade}</a>'
    elif grad_check == 0:
        html_table += '<td class="red">'
        vtgradelink = f'<a href="https://www.ssllabs.com/ssltest/analyze.html?d={website}&hideResults=on">{grade}</a>'
    else:
        html_table += '<td class="orange">'
        vtgradelink = '<b>&quest;</b>'
    html_table += vtgradelink + "</td>"

    if grad_check == 1:
        html_table += f'<td class="green">&#x2705;</td>'
    elif grad_check == 0:
        html_table += f'<td class="red">&#10006;</td>'
    else:
        html_table += f'<td class="orange"><b>&quest;</b></td>'

    if redirect_check == 1:
        html_table += f'<td class="green">&#x2705;</td>'
    elif redirect_check == 0:
        html_table += f'<td class="red">&#10006;</td>'
    else:
        html_table += f'<td class="orange"><b>&quest;</b></td>'

    if cert_valid is None:
        html_table += f'<td class="orange"><b>&quest;</b></td>'
    elif cert_valid > 29:
        html_table += f'<td class="green">{cert_valid}</td>'
    elif cert_valid < 30:
        html_table += f'<td class="red">{cert_valid}</td>'
    else:
        html_table += f'<td class="orange"><b>&quest;</b></td>'

    if hsts is None:
        html_table += f'<td class="red">&#10006;</td>'
    elif hsts >= 365:
        html_table += f'<td class="green">{hsts}</td>'
    else:
        html_table += f'<td class="red">{hsts}</td>'


    if head_check == 1:
        html_table += f'<td class="green">&#x2705;</td>'
    elif head_check == 0:
        html_table += f'<td class="red">&#10006;</td>'
    else:
        html_table += f'<td class="orange"><b>&quest;</b></td>'

    if security_txt == 1:
        sectxtlink = f'<a class="check" href="https://{website}/.well-known/security.txt">&#x2705;</a>'
        html_table += f'<td class="green">{sectxtlink}</td>'
    elif security_txt == 0:
        html_table += f'<td class="red">&#10006;</td>'
    else:
        html_table += f'<td class="orange"><b>&quest;</b></td>'
           
    robo_url = f'<a class="check" href="https://{website}/robots.txt">'
    if robo_check == 1:
        html_table += f'<td class="green">{robo_url}&#x2705;</a></td>'
    elif robo_check == 0:
        html_table += f'<td class="red">{robo_url}&#10006;</a></td>'
    else:
        html_table += f'<td class="orange">{robo_url}<b>&quest;</b></a></td>'

    if vers_check == 1:
        html_table += f'<td class="green">&#x2705;</td>'
    elif vers_check == 0:
        html_table += f'<td class="red">&#10006;</td>'
    else:
        html_table += f'<td class="orange"><b>&quest;</b></td>'

    if err_check == 1:
        html_table += f'<td class="green">&#x2705;</td>'
    elif err_check == 0:
        html_table += f'<td class="red">&#10006;</td>'
    else:
        html_table += f'<td class="orange"><b>&quest;</b></td>'

    if remnants == 1:
        html_table += f'<td class="green">&#x2705;</td>'
    elif remnants == 0:
        html_table += f'<td class="red">&#10006;</td>'
    else:
        html_table += f'<td class="orange"><b>&quest;</b></td>'

    if debug == 1:
        html_table += f'<td class="green">&#x2705;</td>'
    elif debug == 0:
        html_table += f'<td class="red">&#10006;</td>'
    else:
        html_table += f'<td class="orange"><b>&quest;</b></td>'

    html_table += f'<td><a class="check" href={debugfile}>{date_check}</td></tr>\n'

# Close the connection to the database
conn.close()

with open('styles.css', 'r') as f:
    css_styles = f.read()

with open('sort.js', 'r') as f:
    sort_js = f.read()

# Create the complete HTML page, the {} below will be replaced with the content of the variables at the end
html_page = """
<!DOCTYPE html>
<html>
<head>
    <title>ScirtScan</title>
    <link rel="stylesheet" href="../styles.css">
</head>
<body>
  <script src="../sort.js"></script>
  <table border="1" class="dataframe mystyle" id="myTable">
  <thead>
    <tr style="text-align: right;">
    <th onclick="sortTable(0)">website<div class="explanation">click to sort</div></th>
    <th onclick="sortTable(1)">https<div class="explanation">click to sort</div></th>
    <th onclick="sortGrades(2)">grade<div class="explanation">click to sort</div></th>
    <th onclick="sortTable(3)">grade<br>check<div class="explanation">click to sort</div></th>
    <th onclick="sortTable(4)">HTTPS<br>redirect<div class="explanation">click to sort</div></th>
    <th onclick="sortTable(5)">cert<br>validity<div class="explanation">click to sort</div></th>
    <th onclick="sortTable(6)">HSTS<br>(days)<div class="explanation">click to sort</div></th>
    <th onclick="sortTable(7)">headers<div class="explanation">click to sort</div></th>
    <th onclick="sortTable(8)">security<br>.txt<div class="explanation">click to sort</div></th>
    <th onclick="sortTable(9)">robots<br>.txt<div class="explanation">click to sort</div></th>
    <th onclick="sortTable(10)">version<div class="explanation">click to sort</div></th>
    <th onclick="sortTable(11)">error<div class="explanation">click to sort</div></th>
    <th onclick="sortTable(12)">remnants<div class="explanation">click to sort</div></th>
    <th onclick="sortTable(13)">debug<div class="explanation">click to sort</div></th>
    <th onclick="sortTable(14)">check date<div class="explanation">click to sort</div></th>
    </tr>
  </thead>
  <tbody>
    {}
  </tbody>
  </table>
  <br />
  This overview is generated with: <a href="https://github.com/beamzer/ScirtScan">https://github.com/beamzer/ScirtScan</a><br /><br />
  Clicks on table headers will result in sorting or reverse sorting on that column content <br />
  &#187; Click on the date field to see the details for that website<br />
  In the security.txt column clicks on green checkbox will show the contents of that URL <br />
  Clicking in the robots.txt column on the checkmarks will try to open that URL<br />
  Click here for a: <a href="website_checks.xlsx">Excel file with the contents of this table</a><br />
  Click here for a: <a href="debug.log">debug.log</a> unless scirtscan was run with --no_debugfile<br />
</body>
</html>
""".format(html_table)

myindex = directory_path + "/" + "index.html"
try:
    with open(myindex, 'w') as f:
        f.write(html_page)
except OSError as error:
    print(error)

print(f"HTML table written to {myindex}")
