###########################################################################################################
# check if the word "debug" is present in HTTP header info,
# for instance laravel has a HTTP header "phpdebugbar-id:" when debug is enabled
# 20240521
###########################################################################################################
import requests

def check_debug_in_headers(website, url, outfile, logger, myheaders):
    """
    Args:
    website (str): The website being checked.
    url (str): The URL to check.
    outfile (file object): The file to write output to.
    logger (function pointer): Function to print debug information.
    myheaders (dict): The headers to send with the request.
    """
    
    logger(f"=== check_debug_in_headers")
    outfile.write('\n===========Check for the word "debug" in HTTP header info\n')

    try:
        response = requests.get(url, headers = myheaders, timeout=5)
        headers = response.headers
        for key, value in headers.items():
            if 'debug' in key.lower() or 'debug' in value.lower():
                logger(f"'debug' found in {key} header for {url}")
                outfile.write(f"NOK\n'debug' found in {key} header for {url}\n")
                return 0

    except requests.exceptions.RequestException as e:
        logger(f"Error while connecting to {url}: {str(e)}")
        outfile.write(f"Error while connecting to {url}: {str(e)}\n")

    logger("debug not found in HTTP headers")
    outfile.write("OK\ndebug not found in HTTP headers\n")

    return 1
