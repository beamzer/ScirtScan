###########################################################################################################
# Check that certain security headers are present in the HTTP header
# 20240521
###########################################################################################################
import requests
from pprint import pformat

def check_http_headers(website, url, outfile, logger, myheaders):
    """
    Args:
    website (str): The website being checked.
    url (str): The URL to check.
    outfile (file object): The file to write output to.
    logger (function pointer): to function printing debug information
    myheaders (dict): The headers to send with the request.
    """

    logger(f"=== check_http_headers")
    outfile.write(f'\n===========HTTP Headers Check\n')

    headers_to_check = {
        "X-XSS-Protection",
        "X-Frame-Options",
        "X-Content-Type-Options",
        "Strict-Transport-Security",
        "Referrer-Policy"
    }

    try:
        response = requests.get(url, headers = myheaders, allow_redirects=True, timeout=5)
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to {website}: {e}")
        outfile.write(f"Error connecting to {website}: {e}\n")
        return 0,0

    missing_headers = []
    hsts_duration = None
    hsts_duration_days = None
    check_header = 1

    for header in headers_to_check:
        outfile.write(f'checking presence of: {header} ')
        logger(f"checking presence of: {header}")
        if header in response.headers:
            outfile.write('PRESENT\n')
            if header == "Strict-Transport-Security":
                # Sometimes there are multiple Strict-Transport-Security headers present
                # RFC6797 states that only the first should be used
                if hasattr(response.headers, 'get_all'):
                    hsts_headers = response.headers.get_all('Strict-Transport-Security')
                else:
                    hsts_headers = response.headers.get('Strict-Transport-Security').split(',')

                if len(hsts_headers) > 1:
                    logger("ERROR: More than one Strict-Transport-Security header present")

                if hsts_headers:
                    hsts_value = hsts_headers[0]  # Get only the first occurrence
                    hsts_parts = hsts_value.split(";")
                    max_age = next((part for part in hsts_parts if "max-age" in part), None)
                    if max_age:
                        hsts_duration = int(max_age.split("=")[1].strip())
                        logger(f"hsts_duration: {hsts_duration}")

        else:
            outfile.write('NOT PRESENT\n')
            missing_headers.append(header)

    if missing_headers:
        outfile.write(f"ERR Missing headers for {website}: {', '.join(missing_headers)}\n")
        check_header = 0

    if hsts_duration is not None:
        hsts_duration_days = int(hsts_duration / (24 * 3600))
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

    return check_header, hsts_duration_days
