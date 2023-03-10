#!/usr/bin/env python3
import sqlite3
import argparse
import os
import json
import requests
import re
import sys
import time
import ssl
import socket
from bs4 import BeautifulSoup
import datetime
#from datetime import date, datetime, timedelta
from datetime import date
import subprocess
from subprocess import Popen
import dns.resolver

version = "v1.2a, 20230226"

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
    '-v','--version',
    action='store_true',
    help='show version info and exit'
)

parser.add_argument(
    '-xq','--exclude_qualys',
    action='store_true',
    help='exclude qualys ssltest from checks'
)

parser.add_argument(
    'filename', 
    metavar='FILENAME', 
    type=str,
    nargs='?', 
    const=None,
    help='filename with list of websites'
)

args = parser.parse_args()

if not args.filename and args.version:
    sys.exit(f"version: {version}")

if args.filename is None:
    parser.print_help()
    sys.exit("ERROR: missing FILENAME")

debug = args.debug
debug and print("debug output activated")

xqualys = args.exclude_qualys
if xqualys:
    debug and print("skipping qualys ssltest")

filename = args.filename

# Check if the file exists
if not os.path.exists(filename):
    sys.exit(f"The file {filename} does not exist.")

debug and print(f"websites will be read from: {filename}")

# Open the file with the websites to check
try:
    with open(filename, 'r') as file:
        inlines = file.readlines()
except IOError as e:
    print(f"Error opening file: {e}")

#debug and print("input file = ", args.input)
#inlines = args.input.readlines()

today = date.today()
directory_path = today.strftime("%Y%m%d")
if not os.path.exists(directory_path):
    try:
        os.makedirs(directory_path)
    except OSError as error:
        print(error)

# Connect to the SQLite database in the directory
try:
    conn = sqlite3.connect(os.path.join(directory_path, 'websites.db'))
    debug and print(f"Connected to database {os.path.join(directory_path, 'websites.db')}.")
except sqlite3.Error as e:
    print(f"Error connecting to database: {e}")

c = conn.cursor()

# Create a table to store the check results, most checks will store a boolean, 1 for OK and 0 for FAIL
# only grade will contain a letter, because Qualys ssltest uses A-F or T for scores, apended with +'s & -'s
c.execute('''CREATE TABLE IF NOT EXISTS website_checks
            (websites TEXT PRIMARY KEY, 
                robots_check INT, 
                headers_check INT, 
                version_check INT, 
                error_check INT, 
                grade TEXT, 
                grade_check INT, 
                check_date TEXT,
                security_txt INT
            )''')


###########################################################################################################
# if the website name doesn't resolve we can skip the other checks
def check_dns(website):
    debug and print(f"=== check_dns {website}")
    outfile.write("\n===========DNS Check\n")
    try:
        ipv4_answers = dns.resolver.resolve(website, 'A')
        for answer in ipv4_answers:
            debug and print(answer.address)
            outfile.write(answer.address + "\n")

        try:
            ipv6_answers = dns.resolver.resolve(website, 'AAAA')
            for answer in ipv6_answers:
                debug and print(answer.address)
                outfile.write(answer.address + "\n")
        except dns.resolver.NoAnswer:
                debug and print ("no IPv6 addresses")  

        try:
            cname_answers = dns.resolver.resolve(website, 'CNAME')
            for answer in cname_answers:
                debug and print(f"cname: {answer.target.to_text()}")
                outfile.write("cname: " + answer.target.to_text() + "\n")
        except dns.resolver.NoAnswer:
                debug and print ("no CNAMEs")
                outfile.write("no CNAMEs")

    except dns.resolver.NXDOMAIN:
        debug and print("NXDOMAIN; Website {website} not found")
        outfile.write("NXDOMAIN; Website {website} not found")
        return False
    return True

###########################################################################################################
# function to check that certain security headers are present in the HTTP header
# we'll use https://github.com/santoru/shcheck for this, because why reinvent the wheel when there is allready
# a perfect program for this.
def header_check(website):
    debug and print(f"=== header_check {website}")
    try:
        url = 'https://' + website
        try:
            process = subprocess.run(['shcheck.py',"-j", "-d", url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as e:
            print(f"shcheck didn't like that: {e}")

        output = process.stdout.decode()
        # debug and print(f"shcheck stdout: {output}")
        # err = process.stderr.decode()
        # debug and print(f"shcheck stderr: {err}")

        if "URL Returned an HTTP error:" in output:
            print("ERR: looks like this is a dead-end street, bailing out of header_check")
            return

        data = json.loads(output)
        output = json.dumps(data,indent=2)


        outfile.write("\n===========Header Check\n")
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
            debug and print("record inserted into website_checks ", check_header)
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)

        return check
    except KeyboardInterrupt:
        sys.exit()
    except OSError as error:
        print(error)

###########################################################################################################
# this is a very rudimentary check to see if version numbers are present in the HTTP headers
# at the moment this is purely done by looking for numbers in the HTTP server or x-generator header field
def check_versioninfo(url):
    debug and print(f"=== check_versioninfo {url}")
    try: 
        result = "OK"       # we'll assume OK unless proven otherwise
        check_version = 1

        r = requests.head(url, allow_redirects=True, timeout=2)
        if 'server' in r.headers:
            if re.match(r".*[0-9].*", r.headers['server']):
                result = "NOK"
                check_version = 0

        if 'x-generator' in r.headers:
            if re.match(r".*[0-9].*", r.headers['x-generator']):
                result = "NOK"
                check_version = 0

        # output = process.stdout.decode()
        outfile.write("\n===========Version Info CHECK\n")
        outfile.write(result + "\n")

        outfile.write(str(r.headers))
        outfile.write("\n")

        try:
            c.execute("UPDATE website_checks SET version_check = ? WHERE websites = ?", (check_version, website))
            conn.commit()
            debug and print("record inserted into website_checks ", check_version)
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)

        return check_version
    except KeyboardInterrupt:
        sys.exit()
    except OSError as error:
        print(error)

###########################################################################################################
# this check will verify that robots.txt only contains allow statements, since disallow statements give away 
# interesting information to hackers
def robots_check(url):
    debug and print(f"=== robots_check {url}")
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
            debug and print("record inserted into website_checks ", check_robots)
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)

        return check
    except KeyboardInterrupt:
        sys.exit()
    except OSError as error:
        print(error)


###########################################################################################################
# the error check tries to verify that there is no product information or version numbers in the HTTP error page
# production websites should serve a clean error page and test websites should nog be open from the Internet
def error_check(url):
    debug and print(f"=== error_check {url}")
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
            debug and print("record inserted into website_checks ", check_error)
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)
    except KeyboardInterrupt:
        sys.exit()
    except OSError as error:
        print(error)

###########################################################################################################
# This checks that the website has an A+ grade on the Qualys SSLtest
# by requiring an A+ score out security policy is future proof, since Qualys will modify the grading scores when certain
# algorithms are not safe to use anymore.
# Maybe your policy requires an other SSL/TLS check, you can easily cater for that by defining and using your own check function
def check_ssl(url):
    debug and print(f"=== check_ssl {url}")
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

        regexp = re.compile(r'A+')
        if regexp.search(grade):
            check_score = 1
        else:
            check_score = 0

        try:
            c.execute("UPDATE website_checks SET grade = ?, grade_check = ? WHERE websites = ?", (grade,check_score, website))
            conn.commit()
            debug and print("record inserted into website_checks ", grade, check_score)
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)
    except KeyboardInterrupt:
        sys.exit()
    except OSError as error:
        print(error)

###########################################################################################################
# CVD (Coordinated Vulnerability Disclosure) requires security contact information to be present on this URL
def check_security_file(website):
    debug and print(f"=== check_security_file {website}")
    check_security_file = 0
    try:
        response = requests.get(f"https://{website}/.well-known/security.txt")
        if response.status_code >= 200 and response.status_code < 300:
            check_security_file = 1
            outfile.write("\n===========Security.txt Check\n")
            outfile.write("OK\n")
            outfile.write(response.text)
        else:
            outfile.write("\n===========Security.txt Check\n")
            outfile.write("NOK\n")
            
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while checking the security file: {e}")

    try:
        c.execute("UPDATE website_checks SET security_txt = ? WHERE websites = ?", (check_security_file, website))
        conn.commit()
        debug and print("record inserted into website_checks ", check_security_file)
    except sqlite3.Error as error:
        print("Failed to insert data into table", error)


###########################################################################################################
# SSL/TLS Certificate Check by ChatGPT: https://sharegpt.com/c/xHQQv9k
#
def check_ssl_certificate_validity(website):
    debug and print(f"=== check_ssl_certificate_validity {website}")
    # Add the https protocol to the website name
    website_url = "https://" + website

    try:
        # Establish a secure connection to the website and retrieve its SSL certificate information
        cert = ssl.get_server_certificate((website_name, 443))

        # Verify the certificate
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        # Create a socket and wrap it with an SSL context
        with socket.create_connection((website_name, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=website) as ssock:
                # Get the certificate information
                cert_info = ssock.getpeercert()

        # Get the expiration date of the certificate
        cert_expiration = datetime.strptime(cert_info['notAfter'], '%b %d %H:%M:%S %Y %Z')

        # Check if the certificate is going to expire within the next 30 days
        if cert_expiration - datetime.now() < timedelta(days=30):
            return False

        # If the certificate is valid, return True
        return True

    except ssl.SSLError:
        # If the certificate is invalid, return False
        return False




############################################# Main code block #############################################
for website in inlines:
    website = website.strip()
    myfile = directory_path + "/" + website + ".txt"
    url = 'https://' + website.strip()
    try:
        outfile = open(myfile, "w")
    except OSError as e:
        sys.exit(f"Error trying to open {myfile}: {e}")

    check_date = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    outfile.write(website + " check performed on: " + check_date + "\n")

    debug and print("\n==========",url)

    # only write the website name as primary key if there is no row with that info
    c.execute("INSERT INTO website_checks (websites) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM website_checks WHERE websites = ?)", (website,website))
    c.execute("UPDATE website_checks SET check_date = ? WHERE websites = ?", (check_date, website))
    conn.commit()

# Pro tip:
# when you are modifying a function or adding another one, it's best to comment out all other functions 
# untill it works the way you want. Or we can add other commandline arguments to you can specify it at runtime

    if check_dns(website):
        try:
            header_check(website)
            check_versioninfo(url)
            error_check(url)
            robots_check(url)
            check_security_file(website)
            if not xqualys:
                check_ssl(url)
        except KeyboardInterrupt:
            sys.exit("as you wish, aborting...")
        except OSError as e:
            sys.exit(f"Oops, scirtscan.py made a booboo: {e}")

# commit to all changes and close the sqlite database
conn.commit()
conn.close()
