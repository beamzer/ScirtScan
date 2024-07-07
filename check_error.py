###########################################################################################################
# the error check tries to verify that there is no product information or version numbers in the HTTP error page
# production websites should serve a clean error page and test websites should nog be open from the Internet
# 20240521
###########################################################################################################
import requests
from bs4 import BeautifulSoup
import re

def check_error(website, url, outfile, logger, myheaders):
    """
    Args:
    website (str): The website being checked.
    url (str): The URL to check.
    outfile (file object): The file to write output to.
    logger (function pointer): Function to print debug information.
    myheaders (dict): The headers to send with the request.
    """
    
    logger(f"=== error_check")
    try:
        my_url = url + "/sdfsffe978hjcf65"  # Random URL which will generate a 404 on the web server
        response = requests.get(my_url, headers=myheaders, timeout=3)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        # Check for databases, words, and version numbers
        databases = re.findall(r'(Oracle|MySQL|SQL Server|PostgreSQL)', soup.get_text())
        words = re.findall(r'\b(Apache|nginx|Php)\b', soup.get_text())
        numbers = re.findall(r"\b\d+\.\b", soup.get_text())

        check_error = 0
        if databases:
            logger(f"err found db: {databases}")
        elif words:
            logger(f"err found words: {words}")
        elif numbers:
            logger(f"err found numbers: {numbers}")
        else:
            check_error = 1

        outfile.write("\n===========Error Check\n")
        outfile.write(f"{'OK' if check_error == 1 else 'NOK'}")
        # outfile.write(str(soup))

        return (check_error, str(soup))  # Return both check_error and the HTML soup

    except requests.RequestException as e:
        logger(f"Failed to fetch {url}: {str(e)}")
        return (0, "")  # Returning 0 in case of request failures
