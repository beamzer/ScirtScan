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
import subprocess
from subprocess import Popen
import dns.resolver
from pprint import pformat

version = "v1.5b, 20230326"


current_time = datetime.datetime.now()
time_string = current_time.strftime("%Y-%m-%d %H:%M:%S")    # Format the time as a string

# create the output directory (if it doesn't exist)
today = datetime.date.today()
directory_path = today.strftime("%Y%m%d")
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
parser.add_argument('-nc','--no_cache', action='store_true', help='always request fresh tests from qualys')
parser.add_argument('-ndf', '--no_debugfile', action='store_true', help='Don\'t save debug output to debug.log in the YYYYMMDD directory')
parser.add_argument('filename', metavar='FILENAME', type=str, nargs='?', const=None, help='filename with list of websites')
args = parser.parse_args()

if not args.filename and args.version:
    sys.exit(f"version: {version}")

if args.filename is None:
    parser.print_help()
    sys.exit("ERROR: missing FILENAME")

debug = args.debug
skip_debug_file = args.no_debugfile

anon = args.anon

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

# comment this out if you want debug output of more runs on the same day added to one big file
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

c.execute('''CREATE TABLE IF NOT EXISTS website_checks
            (websites TEXT PRIMARY KEY, 
                robots_check INT,
                headers_check INT,
                version_check INT,
                error_check INT,
                grade TEXT,
                grade_check INT,
                check_date TEXT,
                security_txt INT,
                redirect_check INT,
                cert_validity INT,
                hsts INT
            )''')


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

        try:
            cname_answers = dns.resolver.resolve(website, 'CNAME')      # check cname's (aliases)
            for answer in cname_answers:
                debug_print(f"cname: {answer.target.to_text()}")
                outfile.write("cname: " + answer.target.to_text() + "\n")
        except dns.resolver.NoAnswer:
                debug_print ("no CNAMEs")
                outfile.write("no CNAMEs")

        try:
            cname_answers = dns.resolver.resolve(website, 'MX')         # check mx (mail exchange) records
            for answer in cname_answers:
                debug_print(f"mx: {answer.exchange.to_text()}")
                outfile.write("mx: " + answer.exchange.to_text() + "\n")
        except dns.resolver.NoAnswer:
            debug_print("no MX records")
            outfile.write("no MX records")

        try:
            txt_answers = dns.resolver.resolve(website, 'TXT')          # check for TXT (text) records
            for answer in txt_answers:
                for txt_string in answer.strings:
                    debug_print(f"TXT: {txt_string}")
                    outfile.write("TXT: " + txt_string.decode('utf-8') + "\n")
        except dns.resolver.NoAnswer:
            debug_print("no TXT records")
            outfile.write("no TXT records")

    except dns.resolver.NXDOMAIN:
        debug_print("NXDOMAIN; Website {website} not found")
        outfile.write("NXDOMAIN; Website {website} not found")
        return False
    except dns.resolver.LifetimeTimeout as e:
        print("DNS resolution failed due to lifetime timeout.")
        print(f"Error details: {e}")
        return False

    return True


import requests

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
        outfile.write(f"ERR Missing headers for {website}: {', '.join(missing_headers)}")
        check_header = 0

    if hsts_duration is not None:
        hsts_duration_days = int(hsts_duration/365)
        if hsts_duration >= 31536000:
            outfile.write(f"OK, {website} has HSTS value of at least one year: {hsts_duration_days} days\n")
        else:
            outfile.write(f"ERR, {website} HSTS value is LESS than one year: {hsts_duration_days} days\n")
            check_header = 0
    else:
        outfile.write(f"ERR {website} is missing Strict-Transport-Security header\n")
        check_header = 0

    headers_formatted = pformat(dict(response.headers))
    outfile.write(f'{headers_formatted}\n')

    try:
        c.execute("UPDATE website_checks SET headers_check = ? WHERE websites = ?", (check_header, website))
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

        try:
            c.execute("UPDATE website_checks SET robots_check = ? WHERE websites = ?", (check_robots, website))
            conn.commit()
            debug_print(f"record inserted into website_checks {check_robots}")
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
# This checks that the website has the right grade on the Qualys SSLtest ( https://www.ssllabs.com/ssltest/ )
#
def get_ssl_labs_grade(website: str, use_cache=True) -> str:
    debug_print(f"=== get_ssllabs_grade {website}")
    outfile.write("\n===========SSL/TLS Configuration CHECK\n")

    base_url = "https://api.ssllabs.com/api/v3"
    cache_param = 'on' if use_cache else 'off'
    analyze_url = f"{base_url}/analyze?host={website}&publish=off&all=done&fromCache={cache_param}"
    
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
        if response.status_code >= 200 and response.status_code < 300:
            check_security_file = 1
            outfile.write("OK\n")
            outfile.write(response.text)
        else:
            outfile.write("NOK\n")
            
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
# check if HTTP requests are redirected to HTTPS
#
def check_http_redirected_to_https(website: str) -> bool:
    debug_print(f"=== check_http_redirected_to_https {website}")
    outfile.write("\n===========Check HTTP redirect to HTTPS\n")

    try:
        http_url = f'http://{website}'
        response = requests.get(http_url, allow_redirects=True, timeout=10, headers=headers)

        if response.history:
            final_url = response.url
            if final_url.startswith('https://'):
                check_redirect = 1
                outfile.write(f"{website} redirects HTTP to HTTPS\n")
            else:
                redirect_check = 0
                outfile.write(f"ERR {website} does not redirect HTTP to HTTPS\n")

            try:
                c.execute("UPDATE website_checks SET redirect_check = ? WHERE websites = ?", (check_redirect, website))
                conn.commit()
                debug_print(f"record inserted into redirect_checks {check_redirect}")
            except sqlite3.Error as error:
                print("Failed to insert data into table", error)
                return False

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        outfile.write(f"Error: {e}\n")
        return False

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

    if check_dns(website):
        try:
            if oqualys:
                if nocache:
                    get_ssl_labs_grade(website, use_cache=False)
                else:
                    get_ssl_labs_grade(website)
                continue
            # header_check(website)
            check_http_headers(website)
            check_versioninfo(url)
            error_check(url)
            robots_check(url)
            check_security_file(website)
            check_ssl_certificate_validity(website)
            check_http_redirected_to_https(website)
            if testssl:
                check_testssl(website)
            else:
                if not xqualys:
                    if nocache:
                        get_ssl_labs_grade(website, use_cache=False)
                    else:
                        get_ssl_labs_grade(website)
                else:
                    outfile.write('\n===========SSL/TLS Configuration CHECK\nSkipped because use of -nq\n')
        except KeyboardInterrupt:
            sys.exit("as you wish, aborting...")
        except OSError as e:
            sys.exit(f"Oops, scirtscan.py made a booboo: {e}")

# commit to all changes and close the sqlite database
conn.commit()
conn.close()
