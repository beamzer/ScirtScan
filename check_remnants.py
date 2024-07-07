###########################################################################################################
# check if installation files from a CMS are still present on the webserver
# filenames to check are read from remnants.txt
# 20240521
###########################################################################################################
import os
import requests

def check_remnants(website, url, outfile, logger, myheaders, rlff):
    """
    Args:
    website (str): The website being checked.
    url (str): The URL to check.
    outfile (file object): The file to write output to.
    logger (function pointer): Function to print debug information.
    myheaders (dict): The headers to send with the request.
    rlff (function pointer): Function to read lines from file
    """
    
    logger(f"=== check_remnants")
    outfile.write("\n===========Check for installation files left behind\n")

    found_files = []
    filenames = rlff('remnants.txt')
    if filenames is None:
        return 0

    random_file = "iu87h8hkhkgigy"  # Replace this with your own random string
    file_url = os.path.join(url, random_file)
    response = requests.get(file_url, headers = myheaders, timeout=5)
    if response.status_code == 200:
        logger("This web server returns a HTTP code of 200 on everything, skipping checks")
        outfile.write("This web server returns a HTTP code of 200 on everything, skipping checks")
        return 1  # web server will pretend any file is present, so let's stop here

    for file in filenames:
        file_url = os.path.join(url, file)
        try:
            response = requests.get(file_url, headers = myheaders, timeout=5)
            if response.status_code == 200:
                found_files.append(file_url)
        except requests.exceptions.RequestException as e:
            logger(f"Error checking file '{file}': {e}")
    
    if found_files:
        logger(f"The following files gave a 200 response from {website}:")
        outfile.write(f"The following files gave a 200 response from {website}:")
        for file in found_files:
            logger(f"- {file}")
            outfile.write(f"- {file}\n")
        return 0

    else:
        logger(f"No files from remnants.txt were found in the web server root of {url}.")
        outfile.write(f"No files from remnants.txt were found in the web server root of {url}.")
        return 1