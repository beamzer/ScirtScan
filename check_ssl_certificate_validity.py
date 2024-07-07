###########################################################################################################
# SSL/TLS Certificate Check 
# 20240707
###########################################################################################################
import ssl
import socket
import datetime

def check_ssl_certificate_validity(website, outfile, logger):
    """
    Args:
    website (str): The website being checked.
    outfile (file object): The file to write output to.
    logger (function pointer): Function to print debug information.
    """

    logger(f"=== check_ssl_certificate_validity")
    outfile.write("\n===========Certificate validity Check\n")

    try:
        # Establish a secure connection to the website and retrieve its SSL certificate information
        cert = ssl.get_server_certificate((website, 443))

        # Verify the certificate
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        # Create a socket and wrap it with an SSL context
        with socket.create_connection((website, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=website) as ssock:
                # Get the certificate information
                cert_info = ssock.getpeercert()

        # Get the expiration date of the certificate
        cert_expiration = datetime.datetime.strptime(cert_info['notAfter'], '%b %d %H:%M:%S %Y %Z')

        # Get the issuer information of the certificate
        cert_ca = cert_info['issuer']

        current_time = datetime.datetime.now(datetime.timezone.utc)
        days_left = (cert_expiration - current_time).days
        outfile.write(f"certificate expiration: {cert_expiration}\n")
        outfile.write(f"time of check (utc)   : {current_time}\n")
        outfile.write(f"certificate days left : {days_left}\n")
        outfile.write(f"certificate issuer    : {cert_ca}\n")

        if days_left > 29:
            outfile.write("OK\n")
        else:
            outfile.write("NOK\n")
        return days_left

    except ssl.SSLError as e:
        print(f"SSL Error: {e}")
        # If the certificate is invalid, return False
        return 0
