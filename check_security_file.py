###########################################################################################################
# CVD (Coordinated Vulnerability Disclosure) requires security contact information to be present on this URL
# 20240521
###########################################################################################################
import requests
from pprint import pformat

def check_security_file(website, url, outfile, logger, myheaders):
    """
    Args:
    website (str): The website being checked.
    url (str): The URL to check.
    outfile (file object): The file to write output to.
    logger (function pointer): Function to print debug information.
    myheaders (dict): The headers to send with the request.
    """
    
    logger(f"=== check_security_file")
    outfile.write("\n===========Security.txt Check\n")

    security_file = 0
    try:
        response = requests.get(f"{url}/.well-known/security.txt", headers=myheaders)
        if response.status_code >= 200 and response.status_code < 300 and response.headers['Content-Type'].startswith("text/plain"):
            security_file = 1
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

    return security_file