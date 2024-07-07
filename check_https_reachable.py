###########################################################################################################
# Check if the website is reachable with HTTPS
# 20240521
###########################################################################################################
import requests

def check_https_reachable(website, url, outfile, logger, myheaders):
    """
    Args:
    website (str): The website being checked.
    url (str): The URL to check.
    outfile (file object): The file to write output to.
    logger (function pointer): to function printing debug information
    myheaders (dict): The headers to send with the request.
    """
    
    logger(f"=== check_https_reachable")
    outfile.write(f'\n===========HTTPS reachable check\n')
    try:
        response = requests.get(url, headers = myheaders, timeout=5)
        response.raise_for_status()  # If the response was successful, no Exception will be raised
        logger(f"Response Code: {response.status_code}")
        outfile.write(f"Response Code: {response.status_code}")

    except requests.HTTPError as e:
        logger(f"Website is reachable over HTTPS, but Response Code = {e.response.status_code}")
        outfile.write(f"Response is {e}")
        # HTTP 4xx or 5xx means a working HTTPS connection, so we don't exit here

    except (requests.ConnectionError, requests.Timeout, requests.TooManyRedirects) as e:
        print(f"{website} is unreachable over HTTPS")
        if isinstance(e, requests.ConnectionError):
            logger("ConnectionError: Failed to establish a connection")
            outfile.write(f"ConnectionError: Failed to establish a connection, error msg:\n{e}")
        elif isinstance(e, requests.Timeout):
            logger("Timeout: The request timed out")
            outfile.write(f"Timeout: The request timed out, error msg:\n{e}")
        elif isinstance(e, requests.TooManyRedirects):
            logger("TooManyRedirects: The request exceeded the configured number of maximum redirections")
            outfile.write(f"TooManyRedirects: The request exceeded the configured number of maximum redirections, error msg:\n{e}")

        return 0

    return 1