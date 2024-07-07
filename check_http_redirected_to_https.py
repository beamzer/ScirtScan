###########################################################################################################
# check if the website is reachable over HTTP and if so, if requests are redirected to HTTPS
# 20240521
###########################################################################################################
import requests
from pprint import pformat

def check_http_redirected_to_https(website, outfile, logger, myheaders):
    """
    Args:
    website (str): The website being checked.
    outfile (file object): The file to write output to.
    logger (function pointer): Function to print debug information.
    myheaders (dict): The headers to send with the request.
    """
    
    logger(f"=== check only accessible through HTTPS")
    outfile.write("\n===========Check for only accessible through HTTPS\n")

    httperr = 0
    check_redirect = 0

    try:
        http_url = f'http://{website}'
        response = requests.get(http_url, allow_redirects=0, timeout=3, headers=myheaders)
        response.raise_for_status()
        headers_formatted = pformat(dict(response.headers))
        response_code = response.status_code
        outfile.write(f"HTTP request returns response code: {response_code}\n")
        outfile.write(f"HTTP headers are: {headers_formatted}\n")
    except requests.exceptions.ConnectionError:
        httperr = 1
        logger(f"HTTP Connection failed: {http_url} is not reachable over HTTP (port 80).")
        outfile.write(f"HTTP Connection failed: {http_url} is not reachable over HTTP (port 80).")
    except requests.exceptions.Timeout:
        httperr = 1
        logger(f"HTTP Request timed out: {http_url} took too long to respond.")
        outfile.write(f"HTTP Request timed out: {http_url} took too long to respond.")
    except requests.exceptions.HTTPError as err:
        httperr = 1
        logger(f"HTTP error occurred: {err}")
        outfile.write(f"HTTP error occurred: {err}")
    except requests.exceptions.RequestException as err:
        httperr = 1
        logger(f"Error occurred: {err}")
        outfile.write(f"Error occurred: {err}")

    if httperr:
        check_redirect = 1  # From a security perspective, this is also OK because no unencrypted connection
    else:
        try:
            response = requests.get(http_url, allow_redirects=1, timeout=3, headers=myheaders)

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
            return 0

    return 1