###########################################################################################################
# this check will verify that robots.txt only contains Allow statements, since Disallow statements give away 
# interesting information to hackers (often first place to look in reconnaissance)
# 20240521
###########################################################################################################
import requests
import re

def check_robots(website, url, outfile, logger, myheaders):
    """
    Args:
    website (str): The website being checked.
    url (str): The URL to check.
    outfile (file object): The file to write output to.
    logger (function pointer): Function to print debug information.
    myheaders (dict): The headers to send with the request.
    """
    
    logger(f"=== robots_check")
    try:
        check = "NOK"
        myurl = url + "/robots.txt"
        response = requests.get(myurl, headers=myheaders)
        if response.status_code >= 200 and response.status_code < 300 and response.headers['Content-Type'].startswith("text/plain"):

            disallow_regex = re.compile('^Disallow:', re.I)  # re.I = case insensitive
            allow_regex = re.compile('^Allow:', re.I)
            disallow_all_regex = re.compile('^Disallow: \/$', re.I)

            if response.ok:
                allow_count = 0
                disallow_count = 0
                disallow_all_count = 0

                for line in response.text.splitlines():
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
                outfile.write(response.text)
            else:
                outfile.write("\n===========Robots Check\n")
                outfile.write("NOK\n")
                outfile.write("Error: Could not retrieve robots.txt file\n")

            check_robots = 1 if check == "OK" else 0

            # The code is functional, but at the moment other checks have priority, so we'll leave
            # the good/bad results from the overview, but just store the info in the per website debug file
            #
            # Update the database only if both `db_cursor` and `db_connection` are provided
            # if db_cursor and db_connection and website:
            #     try:
            #         db_cursor.execute("UPDATE website_checks SET robots_check = ? WHERE websites = ?", (check_robots, website))
            #         db_connection.commit()
            #         logger(f"record inserted into website_checks {check_robots}")
            #     except sqlite3.Error as error:
            #         print("Failed to insert data into table", error)
        else:
            check_robots = 0

        return check_robots

    except requests.RequestException as e:
        logger(f"Failed to fetch {url}: {str(e)}")
        return 0  # Consider returning 0 in case of request failures
