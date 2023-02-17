#!/usr/bin/python3
import sqlite3
import argparse
import os
import json
import requests
import re
import sys
import time
from bs4 import BeautifulSoup
import datetime
from datetime import date
import subprocess
from subprocess import Popen

current_time = datetime.datetime.now()
#
# Format the time as a string
time_string = current_time.strftime("%Y-%m-%d %H:%M:%S")

parser = argparse.ArgumentParser(description='check websites')

parser.add_argument(
    '-d','--debug',
    action='store_true',
    help='print debug messages to stderr'
)

parser.add_argument(
    '-i','--input',
    type=argparse.FileType('r'),
     required=True,
    default=sys.stdin
)
parser.add_argument(
    '-o','--output',
    type=argparse.FileType('w'),
    default=sys.stdout
)

args = parser.parse_args()
debug = args.debug

debug and print("debug output activated")

#debug and print("input file = ", args.input)
inlines = args.input.readlines()

today = date.today()
d1 = today.strftime("%Y%m%d")
if not os.path.exists(d1):
    try:
        os.makedirs(d1)
    except OSError as error:
        print(error)

# Create a connection to the SQLite database
mydb = d1 + "/" + "websites.db"
conn = sqlite3.connect(mydb)
c = conn.cursor()
debug and print("Succesfully connected to SQLite")

# Create a table to store the check results
c.execute('''CREATE TABLE IF NOT EXISTS website_checks
             (websites TEXT PRIMARY KEY, robots_check INT, headers_check INT, version_check INT, error_check INT, grade TEXT, grade_check INT, check_date TEXT)''')


def header_check(website):
    try:
        url = 'https://' + website
        process = subprocess.run(['shcheck.py',"-j", url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = process.stdout.decode()
        data = json.loads(output)
        output = json.dumps(data,indent=2)


        outfile.write("\n===========HEADER CHECK\n")
        outfile.write(output + "\n")

        check = "OK"
        check_header = 1
        for jsonName,jsonObject in data.items():
            x = data[jsonName]["present"]
            if "X-XSS-Protection" not in x:
                check = "NOK"
            if "X-Frame-Options" not in x:
                check = "NOK"
            if "X-Content-Type-Options" not in x:
                check = "NOK"
            if "Strict-Transport-Security" not in x:
                check = "NOK"
            if "Referrer-Policy" not in x:
                check = "NOK"
        if check == "NOK":
            check_header = 0

        try:
            c.execute("UPDATE website_checks SET headers_check = ? WHERE websites = ?", (check_header, website))
            conn.commit()
            debug and print("header_check, record inserted into website_checks ", check_header)
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)

        return check
    except KeyboardInterrupt:
        sys.exit()
    except OSError as error:
        print(error)

def check_versioninfo(url):
    try:
        r = requests.head(url, allow_redirects=True, timeout=2)
        if 'server' in r.headers:
            if re.match(r".*[0-9].*", r.headers['server']):
                result = "NOK"
                check_version = 0
            else:
                result = "OK"
                check_version = 1

        # output = process.stdout.decode()
        outfile.write("\n===========Version Info CHECK\n")
        outfile.write(result + "\n")

        outfile.write(str(r.headers))
        outfile.write("\n")

        try:
            c.execute("UPDATE website_checks SET version_check = ? WHERE websites = ?", (check_version, website))
            conn.commit()
            debug and print("check_versioninfo, record inserted into website_checks ", check_version)
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)

        return check_version
    except KeyboardInterrupt:
        sys.exit()
    except OSError as error:
        print(error)

def robots_check(url):
    try:
        check = "NOK"

        myurl = url + "/robots.txt"

        resp = requests.get(myurl)
        disallow_regex = re.compile('^Disallow:',re.I)     # re.I = case insensitive
        allow_regex = re.compile('^Allow:',re.I)
        disallow_all_regex = re.compile('^Disallow: \/$',re.I)


        if resp.ok:
            allow_count = 0
            disallow_count = 0
            disallow_all_count = 0

            for line in resp.text.splitlines():
                if allow_regex.match(line):
                    allow_count += 1
                elif disallow_all_regex.match(line):
                    disallow_all_count += 1
                elif disallow_regex.match(line):
                    disallow_count += 1

            # Determine whether the file is OK or not
            if (disallow_count == 0) and (allow_count > 0):
                check = "OK"
            elif (disallow_all_count > 0) and (disallow_count == 0):
                check = "OK"
            else:
                check = "NOK"

            outfile.write("\n===========Robots Check\n")
            outfile.write(check + "\n")
            outfile.write(resp.text)
        else:
            outfile.write("\n===========Robots Check\n")
            outfile.write("NOK\n")
            outfile.write("Error: Could not retrieve robots.txt file\n")

        check_robots = 1 if check == "OK" else 0

        try:
            c.execute("UPDATE website_checks SET robots_check = ? WHERE websites = ?", (check_robots, website))
            conn.commit()
            debug and print("robots_check, record inserted into website_checks ", check_robots)
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)

        return check
    except KeyboardInterrupt:
        sys.exit()
    except OSError as error:
        print(error)


def error_check(url):
    try:

        my_url = url + "/sdfsffe978hjcf65"  # random url which will generate a 404 on the webserver

        resp = requests.get(my_url, timeout=3)
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        # Check for databases, words, and numbers
        databases = re.findall(r'(Oracle|MySQL|SQL Server|PostgreSQL)', soup.get_text())
        words = re.findall(r'\b(Apache|nginx|Php)\b', soup.get_text())
        numbers = re.findall(r"\b\d+\.\b", soup.get_text())

        if databases or words or numbers:
            result = "NOK"
            check_error = 0
        else:
            result = "OK"
            check_error = 1

        outfile.write("\n===========Error Check\n")
        outfile.write(result + "\n")
        outfile.write(str(soup))

        if result == "NOK":
            check_error = 0
        else:
            check_error = 1

        try:
            c.execute("UPDATE website_checks SET error_check = ? WHERE websites = ?", (check_error, website))
            conn.commit()
            debug and print("error_check, record inserted into website_checks ", check_error)
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)
    except KeyboardInterrupt:
        sys.exit()
    except OSError as error:
        print(error)

def check_ssl(url):
    try:
        response = subprocess.run(['ssllabs-scan-v3','-quiet','-usecache',url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        check_result = response.stdout.decode()
        outfile.write("\n===========SSL/TLS Configuration CHECK\n")
        # outfile.write(check_result)

        # Parse JSON data
        data = json.loads(check_result)

        host = data[0]['host']
        ipAddress = data[0]['endpoints'][0]['ipAddress']
        grade = data[0]['endpoints'][0]['grade']

        json_formatted_str = json.dumps(data, indent=2)
        outfile.write(json_formatted_str)

        regexp = re.compile(r'A')
        if regexp.search(grade):
            check_score = 1
        else:
            check_score = 0

        try:
            c.execute("UPDATE website_checks SET grade = ?, grade_check = ? WHERE websites = ?", (grade,check_score, website))
            conn.commit()
            debug and print("check_ssl, record inserted into website_checks ", grade, check_score)
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)
    except KeyboardInterrupt:
        sys.exit()
    except OSError as error:
        print(error)


for website in inlines:
    website = website.strip()
    myfile = d1 + "/" + website + ".txt"
    url = 'https://' + website.strip()
    outfile = open(myfile, "w")
    check_date = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    outfile.write(website + " check performed on: " + check_date + "\n")

    debug and print("\n==========",url)

    # alleen de website naam wegschrijven als primary key als er nog geen rij bestaat met die info
    c.execute("INSERT INTO website_checks (websites) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM website_checks WHERE websites = ?)", (website,website))
    c.execute("UPDATE website_checks SET check_date = ? WHERE websites = ?", (check_date, website))
    conn.commit()

    security_headers = header_check(website)
    version_info = check_versioninfo(url)
    error_check_result = error_check(url)
    check_robots = robots_check(url)
    ssl_config = check_ssl(url)

conn.commit()
conn.close()