#!/usr/bin/env python3
import sqlite3
import argparse
import os
import json
import requests
import re
import sys
import time
import datetime

# importing scirtscan check functions
from check_dns import check_dns
from check_http_headers import check_http_headers
from check_https_reachable import check_https_reachable
from check_versioninfo import check_versioninfo
from check_robots import check_robots
from check_error import check_error
from check_security_file import check_security_file
from check_remnants import check_remnants
from check_ssl_certificate_validity import check_ssl_certificate_validity
from check_http_redirected_to_https import check_http_redirected_to_https
from check_debug_in_headers import check_debug_in_headers
from check_testssl import check_testssl
from check_sslscore import check_sslscore

version = "v3.0 20240701"

#### this is in the global section for now
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
debug_file_path = os.path.join(directory_path, "debug.log")

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

if not skip_debug_file:
    print(f"debug.log output written to {debug_file_path}")

###########################################################################################################
# support function to print debug information
###########################################################################################################
def debug_print(msg):
    if not skip_debug_file:      
        with open(debug_file_path, 'a') as f:
            try:
                f.write(msg + '\n')
            except OSError as error:
                print(f"failed to write to debug.log: {error}")
    if debug:
        print(msg)


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
usecache = not nocache

testssl = args.testssl
if testssl:
    debug_print("using locally installed testssh.sh instead of Qualys SSLtest")

filename = args.filename

debug_print(f"ScirtScan version: {version}, check started on: {time_string}")

###########################################################################################################
# support function to read contents of a file into variable
###########################################################################################################
def read_lines_from_file(filename):
    try:
        with open(filename, 'r') as file:
            return [line.strip() for line in file if not line.strip().startswith('#')]
    except FileNotFoundError:
        debug_print(f"Error: The file '{filename}' does not exist.")
    except PermissionError:
        debug_print(f"Error: You do not have permissions to read the file '{filename}'.")
    except Exception as e:
        debug_print(f"An unexpected error occurred: {e}")
    return None

###########################################################################################################
# Setup the SQLite database in the date directory
###########################################################################################################
# import sqlite3
# import os
def setup_database(directory_path, db_filename='websites.db'):
    """
    Sets up the connection to the SQLite database and initializes the tables.
    
    Args:
    directory_path (str): Path to the directory where the database file is stored.
    db_filename (str): Name of the SQLite database file.
    
    Returns:
    tuple: A tuple containing the database connection and cursor.
    """
    db_path = os.path.join(directory_path, db_filename)
    try:
        conn = sqlite3.connect(db_path)
        debug_print(f"Connected to database {db_path}.")
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None, None  # Return None if connection failed

    cursor = conn.cursor()
    
    # Create a table to store the check results, most checks will store a boolean, 1 for OK and 0 for FAIL
    ####=> for all INT values, 1 = Good, meaning the check did find that the website was compliant with the security check,
    #      or there was no information found that the website was incompliant with the security check.
    #      0 = Bad, empty = ? (don't know)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS website_checks
    (
        websites TEXT PRIMARY KEY,
        https_reachable INT,             -- whether the website is reachable through HTTPS (on port443)
        grade TEXT,                      -- what is the Qualys SSLtest score (e.g. A+)
        grade_check INT,                 -- is Qualys SSLtest score compliant with our requirements (e.g. > A-)
        redirect_check INT,              -- are HTTP requests redirected to HTTPS ?
        cert_validity INT,               -- how many days before the certificate expires
        hsts INT,                        -- HTTP Strict Transport Security
        security_txt INT,                -- is .well-known/security.txt present?
        version_check INT,               -- no version information disclosed in HTTP headers
        robots_check INT,                -- only Allow in robots.txt
        error_check INT,                 -- no version information disclosed in HTTP error page (404)
        remnants INT,                    -- whether there are remnants of CMS installation files on the website
        debug INT,                       -- if the HTTP headers returned contain the word debug (because you might want to investigate)
        headers_check INT,               -- required HTTP security headers present?
        check_date TEXT                  -- when were the checks performed
    )
    ''')

    cursor.execute("CREATE TABLE IF NOT EXISTS meta (structure TEXT, version TEXT)")

    # Inserting table structure and version meta data
    table_structure = """
    (   websites TEXT, https_reachable INT, grade TEXT, grade_check INT, redirect_check INT, cert_validity INT, hsts INT,
        security_txt INT, version_check INT, error_check INT, remnants INT, debug INT, headers_check INT,
        check_date TEXT )
    """
    try:
        cursor.execute("INSERT INTO meta (structure) VALUES (?)", (table_structure,))
        cursor.execute("INSERT INTO meta (version) VALUES (?)", (version,))  # version needs to be defined or passed
    except sqlite3.Error as error:
        print("Failed to insert structure and version into table meta", error)

    return conn, cursor

###########################################################################################################
# store results in sqlite database
###########################################################################################################
#import sqlite3
def update_website_checks(website, columns, db_cursor, db_connection):
    try:
        # db_connection = sqlite3.connect(db_path)
        # db_cursor = db_connection.cursor()
        
        # Construct the SQL update query dynamically based on the provided columns
        set_clause = ", ".join([f"{column} = ?" for column in columns])
        query = f"UPDATE website_checks SET {set_clause} WHERE websites = ?"
        
        # Execute the update query
        db_cursor.execute(query, list(columns.values()) + [website])
        db_connection.commit()
        debug_print(f"Record updated {website}, {columns}")
    
    except sqlite3.Error as error:
        print("Failed to update data in table", error)

###########################################################################################################
############################################# Main code block #############################################
###########################################################################################################
def main():

    websites = []   # list of online websites tho pass to sslscan
    websites2 = []   # list of online websites that failed to produce a grade on the first time


    # HTTP GET/POST headers for normal (e.g. API calls) operation
    aheaders = {
        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
    }
    # It is a good practice to show who is doing the requests
    # but we keep the normal User-Agent content to avoid clever blocking by WAFs, etc.

    if not anon:
        myCERT = 'Fill in the name of your CERT'
        headers = {
            'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 ({myCERT})'
        }
    else:
        headers = aheaders

    db_connection, db_cursor = setup_database(directory_path)   # Setup database connection

    if not(db_connection and db_cursor):
        sys.exit("failed to connect tot database, aborting")

    if not os.path.exists(filename):
        sys.exit(f"The file {filename} does not exist.")
    
    debug_print(f"websites will be read from: {filename}")

    try:
        with open(filename, 'r') as file:
            inlines = [line.strip() for line in file if not line.strip().startswith("#")]

        websites = []
  
        for website in inlines:
            myfile = os.path.join(directory_path, f"{website}.html")

            with open(myfile, "a") as outfile:      # set this to "a" if you want to append to an existing outfile
                outfile.write("<html>\n<body>\n<pre>\n")
                check_date = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                outfile.write(f"{website} checks started on: {check_date}\n")

                debug_print(f"\n===============================================> {website}")
                if check_dns(website, outfile, debug_print):
                    url = f"https://{website}"

                    # only write the website name as primary key if there is no row with that info
                    db_cursor.execute("INSERT INTO website_checks (websites) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM website_checks WHERE websites = ?)", (website,website))
                    db_cursor.execute("UPDATE website_checks SET check_date = ? WHERE websites = ?", (check_date, website))
                    db_connection.commit()

                    https = check_https_reachable(website, url, outfile, debug_print, headers)
                    update_website_checks(website, {"https_reachable": https}, db_cursor, db_connection)

                    if https:       # only do the checks if the website is reachable over HTTPS
                        websites.append(website)    # store website in list for Qualys SSLscan

                        if oqualys:         # only do qualys checks
                            continue

                        if otestssl:        # only do testssl checks
                            for website in websites:
                                gr, checkssl = check_testssl(website, outfile, debug_print)
                                update_website_checks(website, {"grade": gr, "grade_check": checkssl}, db_cursor, db_connection)
                            continue
                        else:

                            check_header, hsts_duration_days = check_http_headers(website, url, outfile, debug_print, headers)
                            update_website_checks(website, {"hsts": hsts_duration_days, "headers_check": check_header}, db_cursor, db_connection)

                            versioninfo = check_versioninfo(website, url, outfile, debug_print, headers)
                            update_website_checks(website, {"version_check": versioninfo}, db_cursor, db_connection)

                            robo = check_robots(website, url, outfile, debug_print, headers)
                            update_website_checks(website, {"robots_check": robo}, db_cursor, db_connection)

                            err, html_content = check_error(website, url, outfile, debug_print, headers)
                            update_website_checks(website, {"error_check": err}, db_cursor, db_connection)
                            errfile = os.path.join(directory_path, f"{website}-error.txt")
                            with open(errfile, "w") as outerrfile:
                                try:
                                    outerrfile.write(f"{html_content}")
                                    outfile.write(f"\n<a href=\"{website}-error.txt\">{website}-error.txt</a>\n")
                                except OSError as e:
                                    sys.exit(f"Error trying to open for writing {errfile}: {e}")
                            outerrfile.close()

                            secfile = check_security_file(website, url, outfile, debug_print, headers)
                            update_website_checks(website, {"security_txt": secfile}, db_cursor, db_connection)

                            remnant = check_remnants(website, url, outfile, debug_print, headers, read_lines_from_file)
                            update_website_checks(website, {"remnants": remnant}, db_cursor, db_connection)

                            certv = check_ssl_certificate_validity(website, outfile, debug_print)
                            update_website_checks(website, {"cert_validity": certv}, db_cursor, db_connection)

                            redir = check_http_redirected_to_https(website, outfile, debug_print, headers)
                            update_website_checks(website, {"redirect_check": redir}, db_cursor, db_connection)

                            dbg = check_debug_in_headers(website, url, outfile, debug_print, headers)
                            update_website_checks(website, {"debug": dbg}, db_cursor, db_connection)

                            if testssl:
                                gr, checkssl = check_testssl(website, outfile, debug_print)
                                update_website_checks(website, {"grade": gr, "grade_check": checkssl}, db_cursor, db_connection)

                if xqualys:
                    done_date = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                    outfile.write(f"{website} checks done at: {done_date} \n")
                    outfile.write("</pre>\n</body>\n</html>")
                    outfile.close()

        # this will run after all the websites have been gone through all the checks above.
        if not (xqualys or testssl or otestssl):
            count = 10;
            debug_print(f"\n===============================================> starting sslchecks for:\n{websites}")
            while websites and count >= 0:
                debug_print(f"\nstarting round {11 - count}")
                results, retry = check_sslscore(websites, usecache, directory_path, debug_print)
                for website, grade, check_score in results:
                    update_website_checks(website, {"grade": grade, "grade_check": check_score}, db_cursor, db_connection)
                websites = retry
                count -= 1

            if websites:
                debug_print(f"===> sslcheck didn't succeed for: {websites}")
            else:
                debug_print(f'\n===========Qualys SSL/TLS Configuration CHECK\nSkipped; eXclude Qualys: {xqualys}; testssl: {testssl}; only testssl: {otestssl}\n')

        db_connection.commit()      # Commit to all changes and close the SQLite database
        db_connection.close()

        check_date = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        debug_print(f"\nALL DONE on: {check_date}\n")
    except KeyboardInterrupt:
        sys.exit("as you wish, aborting...")
    except OSError as e:
        sys.exit(f"Error trying to open {myfile}: {e}")

if __name__ == "__main__":
    main()
