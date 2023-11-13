#!/usr/bin/env python3
import threading    # because of running multiple ssllabs check concurrently
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
import subprocess
from subprocess import Popen
import dns.resolver
from pprint import pformat

version = "v2.2, 20231113"

current_time = datetime.datetime.now()
time_string = current_time.strftime("%Y-%m-%d %H:%M:%S")    # Format the time as a string

# create the output directory (if it doesn't exist)
today = datetime.date.today()
directory_path = today.strftime("%Y%m%d")
#directory_path = "debug_" + today.strftime("%Y%m%d")
if not os.path.exists(directory_path):
    try:
        os.makedirs(directory_path)
    except OSError as error:
        sys.exit(f"Error trying create {directory_path}: {error}")


parser = argparse.ArgumentParser(description='check websites')
parser.add_argument('-d','--debug', action='store_true', help='print debug messages to stderr')
parser.add_argument('-a','--anon', action='store_true', help='don\'t modify user-agent to show who is scanning')
parser.add_argument('-v','--version', action='store_true', help='show version info and exit')
parser.add_argument('-nq','--no_qualys', action='store_true', help='exclude qualys ssltest')
parser.add_argument('-oq','--only_qualys', action='store_true', help='only do qualys ssltest (skip other tests)')
parser.add_argument('-t','--testssl', action='store_true', help='use locally installed testssl.sh instead of qualys')
parser.add_argument('-ot','--only_testssl', action='store_true', help='only do testssl.sh checks on websites')
parser.add_argument('-nc','--no_cache', action='store_true', help='always request fresh tests from qualys')
parser.add_argument('-ndf', '--no_debugfile', action='store_true', help='Don\'t save debug output to debug.log in the YYYYMMDD directory')
parser.add_argument('filename', metavar='FILENAME', type=str, nargs='?', const=None, help='filename with list of websites')
args = parser.parse_args()

if not args.filename and args.version:
    sys.exit(f"version: {version}")

if args.filename is None:
    parser.print_help()
    sys.exit("ERROR: missing FILENAME")

anon = args.anon


debug = args.debug
skip_debug_file = args.no_debugfile

# print debug messages to screen on -d
debug_file_path = os.path.join(directory_path, "debug.log")

def debug_print(msg):
    if not skip_debug_file:      
        with open(debug_file_path, 'a') as f:
            try:
                f.write(msg + '\n')
            except OSError as error:
                print(f"failed to write to debug.log: {error}")
    if debug:
        print(msg)

# support function to read contents of a file into variable
def read_lines_from_file(filename):
    try:
        with open(filename, 'r') as file:
            return [line.strip() for line in file]
    except FileNotFoundError:
        debug_print(f"Error: The file '{filename}' does not exist.")
    except PermissionError:
        debug_print(f"Error: You do not have permissions to read the file '{filename}'.")
    except Exception as e:
        debug_print(f"An unexpected error occurred: {e}")
    return None


# comment this out if you want the debug output of more runs on the same day added to one big file
if not skip_debug_file:
    print(f"debug.log output written to {debug_file_path}")
    if os.path.exists(debug_file_path):
        try:
            os.remove(debug_file_path)
        except OSError as error:
            print(f"found existing debug.log but failed to remove it: {error}")

debug_print(f"ScirtScan version: {version}, check started on: {time_string}")




xqualys = args.no_qualys
if xqualys:
    debug_print("skipping qualys ssltest")

oqualys = args.only_qualys
if oqualys:
    debug_print("only doing qualys ssltest")

otestssl = args.only_testssl
if otestssl:
    debug_print("only doing testssl.sh ssltest")

nocache = args.no_cache
if nocache:
    debug_print("not requesting cached results from qualys ssltest")

testssl = args.testssl
if testssl:
    debug_print("using locally installed testssh.sh instead of Qualys SSLtest")

filename = args.filename

# Check if the file exists
if not os.path.exists(filename):
    sys.exit(f"The file {filename} does not exist.")

debug_print(f"websites will be read from: {filename}")

# Open the file with the list of websites
try:
    with open(filename, 'r') as file:
        inlines = file.readlines()
except IOError as error:
    sys.exit(f"Error opening file {filename}: {error}")

# headers for normal (e.g. API calls) operation
aheaders = {
    'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
}
# It is a good practice to show who is doing the requests
# but we keep the normal User-Agent content to avoid clever blocking by WAFs, etc.
if not anon:
    myCERT = 'AmsterdamUMC CERT'
    headers = {
        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 ({myCERT})'
    }
else:
    headers = aheaders

# Connect to the SQLite database in the directory
try:
    conn = sqlite3.connect(os.path.join(directory_path, 'websites.db'))
    debug_print(f"Connected to database {os.path.join(directory_path, 'websites.db')}.")
except sqlite3.Error as e:
    print(f"Error connecting to database: {e}")

c = conn.cursor()

# Create a table to store the check results, most checks will store a boolean, 1 for OK and 0 for FAIL
# only grade will contain a letter, because Qualys ssltest uses A-F or T for scores, apended with +'s & -'s
# robots_check INT,           # only Allow in robots.txt
# headers_check INT,          # required HTTP security headers present?
# version_check INT,          # no version information disclosed in HTTP headers
# error_check INT,            # no version information disclosed in HTTP error page (404)
# grade TEXT,                 # what is the Qualys SSLtest score (e.g. A+)
# grade_check INT,            # is Qualys SSLtest score compliant with our requirements (e.g. > A-)
# check_date TEXT,            # when where the checks performed
# security_txt INT,           # is .well-known/security.txt present?
# redirect_check INT,         # are HTTP requests redirected to HTTPS ?
# cert_validity INT           # how many days before the certificate expires
# https_reachable             # whether the website is reachable through HTTPS (on port443)
# remnants                    # whether the are remnants of CMS installation files on the website
# debug                       # if the HTTP headers returned contain the word debug (because you might want to investigate)

####=> for all INT values, 1 = Good, meaning the check did find that the website was compliant with the security check,
#      or there was no information found that the website was incompliant with the security check.
#      0 = Bad, empty = ? (don't know)

# if you want to add your own check/function, add the table name before check_date, and also add it to table_structure_below
c.execute('''CREATE TABLE IF NOT EXISTS website_checks
            (websites TEXT PRIMARY KEY, 
                https_reachable INT,
                grade TEXT,
                grade_check INT,
                redirect_check INT,
                cert_validity INT,
                hsts INT,                
                security_txt INT,
                version_check INT,
                error_check INT,
                remnants INT,
                debug INT,
                headers_check INT,
                check_date TEXT                
            )''')

# Create the meta table and store the structure
c.execute("CREATE TABLE IF NOT EXISTS meta (structure TEXT, version TEXT)")

# Insert the table structure into the meta table, so sql2html.py and sql2excel.py can use this
table_structure = """
(   websites TEXT, https_reachable INT, grade TEXT, grade_check INT, redirect_check INT, cert_validity INT, hsts INT,
    security_txt INT, version_check INT, error_check INT, remnants INT, debug INT, headers_check INT,
    check_date TEXT )
"""

# # Check if the structure is already in the meta table
# c.execute("SELECT table_structure FROM meta")
# result = c.fetchone()

# # If the meta table is empty, insert the structure
# if not result:
try:
    c.execute("INSERT INTO meta (structure) VALUES (?)", (table_structure,))
    c.execute("INSERT INTO meta (version) VALUES (?)", (version,))
except sqlite3.Error as error:
    print("Failed to insert structure and version into table meta", error)

###########################################################################################################
# if the website name doesn't resolve we can skip the other checks
# this check is only for logging purposes and is not visible in the dashboard overview
#
def check_dns(website):
    debug_print(f"=== check_dns {website}")
    outfile.write("\n===========DNS Check\n")

    try:
        ipv4_answers = dns.resolver.resolve(website, 'A')               # check IPv4 addresses
        for answer in ipv4_answers:
            debug_print(answer.address)
            outfile.write(answer.address + "\n")

        try:
            ipv6_answers = dns.resolver.resolve(website, 'AAAA')        # check IPv6 addresses
            for answer in ipv6_answers:
                debug_print(answer.address)
                outfile.write(answer.address + "\n")
        except dns.resolver.NoAnswer:
                debug_print ("no IPv6 addresses")
                outfile.write("no IPv6 addresses\n")

        try:
            cname_answers = dns.resolver.resolve(website, 'CNAME')      # check cname's (aliases)
            for answer in cname_answers:
                debug_print(f"cname: {answer.target.to_text()}")
                outfile.write("cname: " + answer.target.to_text() + "\n")
        except dns.resolver.NoAnswer:
                debug_print ("no CNAMEs")
                outfile.write("no CNAMEs\n")

        try:
            cname_answers = dns.resolver.resolve(website, 'MX')         # check mx (mail exchange) records
            for answer in cname_answers:
                debug_print(f"mx: {answer.exchange.to_text()}")
                outfile.write("mx: " + answer.exchange.to_text() + "\n")
        except dns.resolver.NoAnswer:
            debug_print("no MX records")
            outfile.write("no MX records\n")

        try:
            txt_answers = dns.resolver.resolve(website, 'TXT')          # check for TXT (text) records
            for answer in txt_answers:
                for txt_string in answer.strings:
                    debug_print(f"TXT: {txt_string}")
                    outfile.write("TXT: " + txt_string.decode('utf-8') + "\n")
        except dns.resolver.NoAnswer:
            debug_print("no TXT records")
            outfile.write("no TXT records\n")

    except dns.resolver.NoNameservers as e:
        debug_print(f"DNS lookup for {website} failed with SERVFAIL")
        outfile.write(f"DNS lookup for {website} failed with SERVFAIL")
        return False
    except dns.resolver.NXDOMAIN:
        debug_print(f"NXDOMAIN; Website {website} not found")
        outfile.write(f"NXDOMAIN; Website {website} not found")
        return False
    except dns.resolver.LifetimeTimeout as e:
        print(f"DNS resolution for {website} failed due to lifetime timeout.")
        print(f"Error details: {e}")
        return False

    return True

###########################################################################################################
# Check if the website is reachable with HTTPS
###########################################################################################################
# Check if the website is reachable with HTTPS
def check_https_reachable(website):
    debug_print(f"=== check_https_reachable {website}")
    outfile.write(f'\n===========HTTPS reachable check\n')
    try:
        response = requests.get('https://' + website, timeout=5)
        response.raise_for_status()  # If the response was successful, no Exception will be raised
        debug_print(f"Response Code: {response.status_code}")
        outfile.write(f"Response Code: {response.status_code}")


    except (requests.HTTPError) as e:
        debug_print(f"Website is reachable over HTTPS, but Response Code = {e.response.status_code}")
        outfile.write(f"Response is {e}")
        # HTTP 4xx or 5xx means a working website, so we don't exit here

    except (requests.ConnectionError, requests.Timeout, requests.TooManyRedirects) as e:
        print("Website is unreachable over HTTPS")
        if isinstance(e, requests.ConnectionError):
            debug_print("ConnectionError: Failed to establish a connection")
            outfile.write(f"ConnectionError: Failed to establish a connection, error msg:\n{e}")
        elif isinstance(e, requests.Timeout):
            debug_print("Timeout: The request timed out")
            outfile.write(f"Timeout: The request timed out, error msg:\n{e}")
        elif isinstance(e, requests.TooManyRedirects):
            debug_print("TooManyRedirects: The request exceeded the configured number of maximum redirections")
            outfile.write(f"TooManyRedirects: The request exceeded the configured number of maximum redirections, error msg:\n{e}")

        try:
            c.execute("UPDATE website_checks SET https_reachable = ? WHERE websites = ?", (0, website))
            conn.commit()
            debug_print(f"record inserted into website_checks: 0")
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)

        return False

    try:
        c.execute("UPDATE website_checks SET https_reachable = ? WHERE websites = ?", (1, website))
        conn.commit()
        debug_print(f"record inserted into website_checks: 1")
    except sqlite3.Error as error:
        print("Failed to insert data into table", error)

    return True

###########################################################################################################
# Check that certain security headers are present in the HTTP header
def check_http_headers(website):
    debug_print(f"=== check_http_headers {website}")
    outfile.write(f'\n===========HTTP Headers Check\n')
    url = f'https://{website}'

    headers_to_check = {
        "X-XSS-Protection",
        "X-Frame-Options",
        "X-Content-Type-Options",
        "Strict-Transport-Security",
        "Referrer-Policy"
    }

    try:
        response = requests.get(url)
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to {website}: {e}")
        outfile.write(f"Error connecting to {website}: {e}\n")
        return

    missing_headers = []
    hsts_duration = None
    hsts_duration_days = None
    check_header = 1
    result = "OK"

    for header in headers_to_check:
        outfile.write(f'checking precense of: {header} ')
        if header in response.headers:
            outfile.write(f'PRESENT\n')
            if header == "Strict-Transport-Security":
                hsts_value = response.headers[header]
                hsts_parts = hsts_value.split(";")
                max_age = next((part for part in hsts_parts if "max-age" in part), None)
                if max_age:
                    hsts_duration = int(max_age.split("=")[1].strip())
        else:
            outfile.write(f'NOT PRESENT\n')
            missing_headers.append(header)

    if missing_headers:
        outfile.write(f"ERR Missing headers for {website}: {', '.join(missing_headers)}\n")
        check_header = 0
        result = "NOK"

    if hsts_duration is not None:
        hsts_duration_days = int(hsts_duration/(24*3600))
        if hsts_duration >= 31536000:
            outfile.write(f"OK, {website} has HSTS value of at least one year: {hsts_duration_days} days\n")
        else:
            outfile.write(f"ERR, {website} HSTS value is LESS than one year: {hsts_duration_days} days\n")
            check_header = 0
            result = "NOK"
    else:
        outfile.write(f"ERR {website} is missing Strict-Transport-Security header\n")
        check_header = 0
        result = "NOK"

    headers_formatted = pformat(dict(response.headers))
    outfile.write(f'{headers_formatted}\n')

    try:
        c.execute("UPDATE website_checks SET headers_check = ? WHERE websites = ?", (check_header, website))
        outfile.write(f"header check result = {result}")
        c.execute("UPDATE website_checks SET hsts = ? WHERE websites = ?", (hsts_duration_days, website))
        conn.commit()
        debug_print(f"record inserted into website_checks {check_header}")
    except sqlite3.Error as error:
        print("Failed to insert data into table", error)


###########################################################################################################
# this is a very rudimentary check to see if version numbers are present in the HTTP headers
# at the moment this is purely done by looking for numbers in the HTTP server or x-generator header field
#
def check_versioninfo(url):
    debug_print(f"=== check_versioninfo {url}")
    outfile.write("\n===========Version Info CHECK\n")

    try: 
        result = "OK"       # we'll assume OK unless proven otherwise
        check_version = 1

        r = requests.head(url, headers=headers, allow_redirects=True, timeout=2)
        if 'server' in r.headers:
            sh = r.headers['server']
            if re.match(r".*[0-9].*", sh):
                outfile.write(f'Looks like version info: {sh}\n')
                result = "NOK"
                check_version = 0

        if 'x-generator' in r.headers:
            xh = r.headers['x-generator']
            if re.match(r".*[0-9].*", xh):
                outfile.write(f'Looks like version info: {xh}\n')
                result = "NOK"
                check_version = 0

        # output = process.stdout.decode()
        outfile.write(f'{result}\n')

        try:
            c.execute("UPDATE website_checks SET version_check = ? WHERE websites = ?", (check_version, website))
            conn.commit()
            debug_print(f"record inserted into website_checks {check_version}")
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)

        return check_version
    except KeyboardInterrupt:
        sys.exit()
    except OSError as error:
        print(error)

###########################################################################################################
# this check will verify that robots.txt only contains Allow statements, since Disallow statements give away 
# interesting information to hackers (often first place to look in reconnaissance)
#
def robots_check(url):
    debug_print(f"=== robots_check {url}")
    try:
        check = "NOK"

        myurl = url + "/robots.txt"

        resp = requests.get(myurl, headers=headers)
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

        # The code is functional, but at the moment other checks have priority, so we'll leave
        # the good/bad results from the overview, but just store the info in the per website debug file
        #
        # try:
        #     c.execute("UPDATE website_checks SET robots_check = ? WHERE websites = ?", (check_robots, website))
        #     conn.commit()
        #     debug_print(f"record inserted into website_checks {check_robots}")
        # except sqlite3.Error as error:
        #     print("Failed to insert data into table", error)

        return check
    except KeyboardInterrupt:
        sys.exit()
    except OSError as error:
        print(error)


###########################################################################################################
# the error check tries to verify that there is no product information or version numbers in the HTTP error page
# production websites should serve a clean error page and test websites should nog be open from the Internet
#
def error_check(url):
    debug_print(f"=== error_check {url}")
    try:

        my_url = url + "/sdfsffe978hjcf65"  # random url which will generate a 404 on the webserver

        resp = requests.get(my_url, headers=headers, timeout=3)
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
            debug_print(f"record inserted into website_checks {check_error}")
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)
    except KeyboardInterrupt:
        sys.exit()
    except OSError as error:
        print(error)

###########################################################################################################
# new SSLlabs check which will use multiple threads running in the background to speed things up
#
def background_ssl_check(website, use_cache, aheaders, outfile_path, db_path):
    base_url = "https://api.ssllabs.com/api/v3"
    if use_cache:
        analyze_url = f"{base_url}/analyze?host={website}&all=done&publish=off&fromCache=on&maxAge=24"
    else:
        analyze_url = f"{base_url}/analyze?host={website}&all=done&publish=off&fromCache=off"

    # analyze_url = f"{base_url}/analyze?host={website}&all=done&publish=off&fromCache={'on' if use_cache else 'off'}"
    # debug_print(f"analyze_url = {analyze_url}")

    # Each thread creates its own database connection
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Check for rate limits before starting the analysis
    try:
        rate_limit_response = requests.head(analyze_url, headers=aheaders)
        rate_limit_response.raise_for_status()
        max_assessments = int(rate_limit_response.headers.get('X-Max-Assessments', 0))
        current_assessments = int(rate_limit_response.headers.get('X-Current-Assessments', 0))
        debug_print(f"SSLlabs API max and current assessment values are: {max_assessments} {current_assessments}")
        if current_assessments >= max_assessments:
            debug_print("Rate limit reached, waiting before re-attempting")
            time.sleep(10)  # Wait time before retrying, adjust as needed
            return background_ssl_check(website, use_cache, aheaders, outfile_path, db_path)  # Retry the function

    except requests.exceptions.RequestException as e:
        debug_print(f"Error while checking rate limits: {e}")
        return

    # Start the analysis with proper error handling
    try:
        response = requests.get(analyze_url, headers=aheaders)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        debug_print(f"timeout error connecting to ssllabs")
        return
    except requests.exceptions.TooManyRedirects:
        debug_print(f"too many redirects while connecting to ssllabs")
        return
    except requests.exceptions.HTTPError as e:
        debug_print(f"error while connecting to ssllabs: {e}")
        return
    except requests.exceptions.RequestException as e:
        debug_print(f"error while connecting to ssllabs: {e}")
        return

    result = response.json()

    # Polling the API with appropriate wait times
    while result.get('status', None) not in ('READY', 'ERROR'):
        time.sleep(5 if result.get('status') == 'IN_PROGRESS' else 10)
        try:
            response = requests.get(analyze_url, headers=aheaders)
            result = response.json()
        except requests.exceptions.RequestException as e:
            debug_print(f"Error while re-polling ssllabs: {e}")
            return

    if result.get('status') == 'READY':
        grade = result['endpoints'][0]['grade']

        # Database operations
        try:
            with conn:
                c.execute("UPDATE website_checks SET grade = ? WHERE websites = ?", (grade, website))
            debug_print(f"Updated ssllabs record for {website}")
        except sqlite3.Error as error:
            debug_print(f"Failed to update data in table for {website}: {error}")
    else:
        debug_print(f"Error: ssllabs check could not be completed for {website}")

    # Write JSON result to file
    with open(outfile_path, "a") as outfile:
        json_formatted_str = json.dumps(result, indent=2)
        outfile.write(f'{json_formatted_str}\n')

    # Close the thread's database connection
    conn.close()


###########################################################################################################
# This checks that the website has the right grade on the Qualys SSLtest ( https://www.ssllabs.com/ssltest/ )
# this is the old single thread version, which makes it slow if you have more than one site to check
#
def get_ssl_labs_grade_single(website: str, use_cache=True) -> str:
    debug_print(f"=== get_ssllabs_grade {website}")
    outfile.write("\n===========SSL/TLS Configuration CHECK\n")

    base_url = "https://api.ssllabs.com/api/v3"
    # cache_param = 'on' if use_cache else 'off'
    # analyze_url = f"{base_url}/analyze?host={website}&publish=off&all=done&fromCache={cache_param}"
    if use_cache:
        # analyze_url = f"{base_url}/analyze?host={website}&publish=off&all=done&fromCache=on&maxAge=24"
        analyze_url = f"{base_url}/analyze?host={website}&all=done&publish=off&fromCache=on&maxAge=24"
    else:
        analyze_url = f"{base_url}/analyze?host={website}&all=done&publish=off&fromCache=off"
    
    # Start the analysis
    try:
        response = requests.get(analyze_url, headers=aheaders)        # this is a normal API call, so we use our normal headers here
        response.raise_for_status()
    except requests.exceptions.Timeout:
        debug_print(f"timeout error connecting to ssllabs")
        outfile.write("timeout error connecting to ssllabs\n")
        return False
    except requests.exceptions.TooManyRedirects:
        debug_print(f"too many redirects while connecting to ssllabs")
        outfile.write("too many redirects while  connecting to ssllabs\n")
        return False
    except requests.exceptions.HTTPError as e:
        debug_print(f"error while connecting to ssllabs: {e}")
        outfile.write(f"error while  connecting to ssllabs: {e}\n")
        return False
    except requests.exceptions.RequestException as e:
        debug_print(f"error while connecting to ssllabs: {e}")
        outfile.write(f"error while  connecting to ssllabs: {e}\n")
        return False

    result = response.json()

# wait times are per Qualys API v3 documentation, see:
# https://github.com/ssllabs/ssllabs-scan/blob/master/ssllabs-api-docs-v3.md#%20access-rate-and-rate-limiting
    while result.get('status', None) not in ('IN_PROGRESS','READY', 'ERROR'):
        time.sleep(5)  # Wait for 5 seconds before polling the API again
        response = requests.get(analyze_url, headers=aheaders)
        result = response.json()
        debug and print(",", end="", flush=True)     # print a , every 5s to show we're waiting for Qualys

    while result.get('status', None) not in ('READY', 'ERROR'):
        time.sleep(10)  # Wait for 10 seconds before polling the API again
        response = requests.get(analyze_url, headers=aheaders)
        result = response.json()
        debug and print(".", end="", flush=True)     # print a . every 10s to show we're waiting for the result
    debug and print("")

    if result.get('status') == 'READY':
        grade = result['endpoints'][0]['grade']
        host = result['host']
        ipAddress = result['endpoints'][0]['ipAddress']
        debug_print(f"grade = {grade}, host = {host}, IP-Address = {ipAddress}")
        outfile.write(f"grade = {grade}, host = {host}, IP-Address = {ipAddress}")
        # return grade
    else:
        print(f"Error: ssllabs check could not be completed for {website}")
        outfile.write(f"Error: ssllabs check could not be completed for {website}")
        return None

    # Parse JSON data and write to logfile
    json_formatted_str = json.dumps(result, indent=2)
    outfile.write(f'{json_formatted_str}\n')

    #regexp = re.compile(r'A\+')      # change A+ to something else if your policy requires differently
    regexp = re.compile(r'A')         # anything from an A- and better is good for us
    if regexp.search(grade):
        check_score = 1
    else:
        check_score = 0

    try:
        c.execute("UPDATE website_checks SET grade = ?, grade_check = ? WHERE websites = ?", (grade,check_score, website))
        conn.commit()
        debug_print(f"ssllabs record inserted into website_checks {check_score}")
    except sqlite3.Error as error:
        print("Failed to insert data into table", error)

###########################################################################################################
# This checks that the website has the right grade according to Qualys SSLtest by using testssl.sh
#
def check_testssl(website):
    debug_print(f"=== testssl.sh {website}")
    outfile.write("\n===========SSL/TLS Configuration with testssl.sh CHECK\n")

    testssl_path = "/usr/local/bin/testssl.sh"  # Replace this with the path to your testssl.sh script
    if not os.path.exists(testssl_path):
        print(f"Skipping testssl.sh check because the path is invalid {testssl_path}")
        return False

    try:
        output = subprocess.check_output([testssl_path, "--color", "0", website])
        output = output.decode('utf-8')

        outfile.write(f"{output}")

        grade = None
        match = re.search(r"Overall\s+Grade\s+([A-F][+-]?|-)", output)

        if match:
            grade = match.group(1)
            debug_print(f"grade: {grade}")

    except subprocess.CalledProcessError as e:
        print(f"Error running testssl.sh: {e}")
        return False

    if grade is not None:
        regexp = re.compile(r'A')         # anything from an A- and better is good for us
        if regexp.search(grade):
            check_score = 1
        else:
            check_score = 0

        try:
            c.execute("UPDATE website_checks SET grade = ?, grade_check = ? WHERE websites = ?", (grade,check_score, website))
            conn.commit()
            debug_print(f"ssllabs record inserted into website_checks {check_score}")
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)

###########################################################################################################
# CVD (Coordinated Vulnerability Disclosure) requires security contact information to be present on this URL
#
def check_security_file(website):
    debug_print(f"=== check_security_file {website}")
    outfile.write("\n===========Security.txt Check\n")

    check_security_file = 0
    try:
        response = requests.get(f"https://{website}/.well-known/security.txt", headers=headers)
        if response.status_code >= 200 and response.status_code < 300 and response.headers['Content-Type'].startswith("text/plain"):
            check_security_file = 1
            outfile.write("OK\n")
            outfile.write(response.text)
        else:
            outfile.write("NOK\n")
            headers_formatted = pformat(dict(response.headers))
            outfile.write(f"HTTP response code: {response.status_code}\n")
            outfile.write(f"{headers_formatted}\n")
            
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while checking the security file: {e}")
        outfile.write(f"An error occurred while checking the security file: {e}\n")

    try:
        c.execute("UPDATE website_checks SET security_txt = ? WHERE websites = ?", (check_security_file, website))
        conn.commit()
        debug_print(f"record inserted into website_checks {check_security_file}")
    except sqlite3.Error as error:
        print("Failed to insert data into table", error)


###########################################################################################################
# SSL/TLS Certificate Check with help from ChatGPT: https://sharegpt.com/c/xHQQv9k
#
def check_ssl_certificate_validity(website):
    debug_print(f"=== check_ssl_certificate_validity {website}")
    outfile.write("\n===========Certificate validity Check\n")

    try:
        # Establish a secure connection to the website and retrieve its SSL certificate information
        cert = ssl.get_server_certificate((website, 443))

        # Verify the certificate
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        # Create a socket and wrap it with an SSL context
        with socket.create_connection((website, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=website) as ssock:
                # Get the certificate information
                cert_info = ssock.getpeercert()

        # Get the expiration date of the certificate
        cert_expiration = datetime.datetime.strptime(cert_info['notAfter'], '%b %d %H:%M:%S %Y %Z')

        # Get the issuer information of the certificate [not used right now 20230701]
        cert_ca = cert_info['issuer']

        current_time = datetime.datetime.utcnow()
        days_left = (cert_expiration - current_time).days
        if days_left > 29:
            outfile.write("OK\n")
        outfile.write(f"certificate expiration: {cert_expiration}\n")
        outfile.write(f"time of check (utc)   : {current_time}\n")
        outfile.write(f"certificate days left : {days_left}\n")
        # debug_print(f"certificate expiration: {cert_expiration}")
        # debug_print(f"time of check (utc)   : {current_time}")
        # debug_print(f"certificate  days left: {days_left}")

        outfile.write(f"certificate issuer    : {cert_ca}\n")

        try:
            c.execute("UPDATE website_checks SET cert_validity = ? WHERE websites = ?", (days_left, website))
            conn.commit()
            debug_print(f"record inserted into website_checks {days_left}")
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)

        return True

    except ssl.SSLError:
        # If the certificate is invalid, return False
        return False

###########################################################################################################
# check if the website is reachable over HTTP and if so, if requests are redirected to HTTPS
#
def check_http_redirected_to_https(website: str) -> bool:
    debug_print(f"=== check_http_redirected_to_https {website}")
    outfile.write("\n===========Check HTTP redirect to HTTPS\n")

    httperr = False
    check_redirect = 0

    try:
        http_url = f'http://{website}'
        response = requests.get(http_url, allow_redirects=False, timeout=3, headers=headers)
        response.raise_for_status()
        headers_formatted = pformat(dict(response.headers))
        response_code = response.status_code
        outfile.write(f"HTTP request returns response code: {response_code}\n")
        outfile.write(f"HTTP headers are: {headers_formatted}\n")
    except requests.exceptions.ConnectionError:
        httperr = True
        debug_print(f"HTTP Connection failed: {url} is not reachable over HTTP (port 80).")
        outfile.write(f"HTTP Connection failed: {url} is not reachable over HTTP (port 80).")
    except requests.exceptions.Timeout:
        httperr = True
        debug_print(f"HTTP Request timed out: {url} took too long to respond.")
        outfile.write(f"HTTP Request timed out: {url} took too long to respond.")
    except requests.exceptions.HTTPError as err:
        httperr = True
        debug_print(f"HTTP error occurred: {err}")
        outfile.write(f"HTTP error occurred: {err}")
    except requests.exceptions.RequestException as err:
        httperr = True
        debug_print(f"Error occurred: {err}")
        outfile.write(f"Error occurred: {err}")

    if httperr:
        check_redirect = 1  # from a security perspective this is also OK, because no unencrypted connection; will change the variable name some day
    else:
        try:
            response = requests.get(http_url, allow_redirects=True, timeout=3, headers=headers)

            if response.history:
                final_url = response.url
                if final_url.startswith('https://'):
                    check_redirect = 1
                    outfile.write(f"{http_url} redirects HTTP to HTTPS\n")
                else:
                    outfile.write(f"ERR {http_url} does not redirect HTTP to HTTPS\n")
                
                
                outfile.write(f"final URL is: {final_url}\n")
        except requests.exceptions.RequestException as err:
            print(f"HTTP request with allow redirects, Error: {err}")
            outfile.write(f"HTTP request with allow redirects, Error: {err}\n")
            return False      

    try:
        c.execute("UPDATE website_checks SET redirect_check = ? WHERE websites = ?", (check_redirect, website))
        conn.commit()
        debug_print(f"record inserted into redirect_checks {check_redirect}")
    except sqlite3.Error as error:
        print("Failed to insert data into table", error)
        return False



    return True

###########################################################################################################
# check if installation files from a CMS are still present on the webserver
# files are read from remnants.txt
#
def check_remants(webserver):
    debug_print(f"=== check_remnants {website}")
    outfile.write("\n===========Check for installation files left behind\n")

    webserver_url = f"https://{webserver}"
    found_files = []
    filenames = read_lines_from_file('remnants.txt')
    if filenames == None:
        return False

    file = "iu87h8hkhkgigy"     # replace this with your own random string
    file_url = os.path.join(webserver_url, file)
    response = requests.get(file_url)
    if response.status_code == 200:
        debug_print("This webserver returns a HTTP code of 200 on everything, skipping checks")
        outfile.write("This webserver returns a HTTP code of 200 on everything, skipping checks")
        return True               # webserver will pretend any file is present, so let's stop here

    for file in filenames:
        file_url = os.path.join(webserver_url, file)
        try:
            response = requests.get(file_url)
            if response.status_code == 200:
                found_files.append(file_url)
        except requests.exceptions.RequestException as e:
            debug_print(f"Error checking file '{file}': {e}")
    
    if found_files:
        debug_print(f"The following files gave a 200 response from {webserver}:")
        outfile.write(f"The following files gave a 200 response from {webserver}:")
        for file in found_files:
            debug_print(f"- {file}")
            outfile.write(f"- {file}")
        try:
            c.execute("UPDATE website_checks SET remnants = ? WHERE websites = ?", (0, website))
            conn.commit()
            debug_print(f"record inserted into website_checks for remnants: 0")
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)
        return False

    else:
        debug_print(f"No files from remnants.txt were found in the webserver root of {webserver_url}.")
        outfile.write(f"No files from remnants.txt were found in the webserver root of {webserver_url}.")
        try:
            c.execute("UPDATE website_checks SET remnants = ? WHERE websites = ?", (1, website))
            conn.commit()
            debug_print(f"record inserted into website_checks for remnants: 1")
        except sqlite3.Error as error:
            print("Failed to insert data into table", error)
        return True


###########################################################################################################
# check if the word "debug" is present in HTTP header info,
# for instance laravel has a HTTP header "phpdebugbar-id:" when debug is enabled
#
def check_debug_in_headers(website):
    debug_print(f"=== check_debug_in_headers {website}")
    outfile.write("\n===========Check for the word \"debug\" in HTTP header info\n")

    prefix = "https"
    try:
        response = requests.get(website, timeout = 3)
        headers = response.headers
        for key, value in headers.items():
            if 'debug' in key.lower() or 'debug' in value.lower():
                debug_print(f"'debug' found in {key} header for {prefix}{website}")
                outfile.write(f"'debug' found in {key} header for {prefix}{website}")
                try:
                    c.execute("UPDATE website_checks SET debug = ? WHERE websites = ?", (0, website))
                    conn.commit()
                    debug_print(f"record inserted into website_checks for debug: 0")
                except sqlite3.Error as error:
                    print("Failed to insert data into table", error)
                return False

    except requests.exceptions.RequestException as e:
        debug_print(f"Error while connecting to {prefix}{website}: {str(e)}")

    debug_print("debug not found in HTTP headers")
    outfile.write("debug not found in HTTP headers")
    try:
        c.execute("UPDATE website_checks SET debug = ? WHERE websites = ?", (1, website))
        conn.commit()
        debug_print(f"record inserted into website_checks for debug: 1")
    except sqlite3.Error as error:
        print("Failed to insert data into table", error)

    return True


############################################# Main code block #############################################
#
for website in inlines:
    if website.startswith("#"):
        continue                        # allow for comments in website list

    website = website.strip()
    myfile = directory_path + "/" + website + ".txt"
    url = 'https://' + website.strip()
    try:
        outfile = open(myfile, "w")
    except OSError as e:
        sys.exit(f"Error trying to open {myfile}: {e}")

    check_date = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    outfile.write(website + " check performed on: " + check_date + "\n")

    debug_print(f"\n==============================================={url}")

    # only write the website name as primary key if there is no row with that info
    c.execute("INSERT INTO website_checks (websites) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM website_checks WHERE websites = ?)", (website,website))
    c.execute("UPDATE website_checks SET check_date = ? WHERE websites = ?", (check_date, website))
    conn.commit()

# when you are modifying a function or adding another one, comment out all other functions 
# untill it works the way you want. Or add other commandline arguments to you can specify it at runtime

    threads = []    # List to keep track of SSL check threads

    sqlitefile = os.path.join(directory_path, 'websites.db')

    if check_dns(website) and check_https_reachable(website):
        try:
            if oqualys:
                thread = threading.Thread(target=background_ssl_check, args=(website, not nocache, aheaders, myfile, sqlitefile))
                thread.start()
                threads.append(thread)
                continue

            if otestssl:
                check_testssl(website)
                continue

            check_http_headers(website)
            check_versioninfo(url)
            error_check(url)
            robots_check(url)
            check_security_file(website)
            check_ssl_certificate_validity(website)
            check_http_redirected_to_https(website)
            check_remants(website)
            check_debug_in_headers(url)

            if testssl:
                check_testssl(website)
            else:
                if not xqualys:
                    thread = threading.Thread(target=background_ssl_check, args=(website, not nocache, aheaders, myfile, sqlitefile))
                    thread.start()
                    threads.append(thread)
                else:
                    outfile.write('\n===========SSL/TLS Configuration CHECK\nSkipped because use of -nq\n')

        except KeyboardInterrupt:
            sys.exit("as you wish, aborting...")
        except OSError as e:
            sys.exit(f"Oops, scirtscan.py made a booboo: {e}")

# Wait for all SSL check threads to complete
debug_print("\nnow waiting for threads to finish...")
for thread in threads:
    thread.join()

# commit to all changes and close the sqlite database
conn.commit()
conn.close()
