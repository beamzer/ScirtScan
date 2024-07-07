###########################################################################################################
# this is a very rudimentary check to see if version numbers are present in the HTTP headers
# at the moment this is purely done by looking for numbers in the HTTP server or x-generator header field
# 20240612
###########################################################################################################
import requests
import re

def check_versioninfo(website, url, outfile, logger, myheaders):
    """
    Args:
    website (str): The website being checked.
    url (str): The URL to check.
    outfile (file object): The file to write output to.
    logger (function pointer): Function to print debug information.
    myheaders (dict): The headers to send with the request.
    """
    
    logger(f"=== check_versioninfo")
    outfile.write("\n===========Version Info CHECK\n")

    result = "OK"  # Assume OK unless proven otherwise
    check_version = 1

    try:
        response = requests.head(url, headers=myheaders, allow_redirects=True, timeout=5)           
    except requests.RequestException as e:
        logger(f"Failed to fetch {url}: {str(e)}")
        return 0  # returning NotOK in case of request failures

    headers_to_check = [
        'server', 'x-generator', 'x-powered-by', 'via', 
        'x-aspnet-version', 'x-aspnetmvc-version', 
        'x-drupal-cache', 'x-joomla-version', 'x-wordpress', 'x-engine'
    ]
    for header in headers_to_check:
        if header in response.headers:
            header_value = response.headers[header]
            if re.match(r".*[0-9].*", header_value, re.IGNORECASE):
                outfile.write(f'Might be version info: {header}: {header_value}\n')
                logger(f'Might be version info: {header}: {header_value}\n')
                result = "NOK"
                check_version = 0

    outfile.write(f'{result}\n')
    return check_version
