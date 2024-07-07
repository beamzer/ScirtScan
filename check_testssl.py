###########################################################################################################
# This checks that the website has the right grade according to Qualys SSLtest by using testssl.sh
# 20240521
###########################################################################################################
import os
import subprocess
import re

def check_testssl(website, outfile, logger):
    """
    Args:
    website (str): The website being checked.
    outfile (file object): The file to write output to.
    logger (function pointer): Function to print debug information.
    """

    logger(f"=== testssl.sh")
    outfile.write("\n===========SSL/TLS Configuration with testssl.sh CHECK\n")

    testssl_path = "/usr/local/bin/testssl.sh"  # Replace this with the path to testssl.sh v3.2
    if not os.path.exists(testssl_path):
        print(f"Skipping testssl.sh check because the path is invalid: {testssl_path}")
        return "Z",0

    try:
        output = subprocess.check_output([testssl_path, "--color", "0", website])
        output = output.decode('utf-8')

        outfile.write(f"{output}\n")

        grade = None
        match = re.search(r"Overall\s+Grade\s+([A-F][+-]?|-)", output)

        if match:
            grade = match.group(1)
            logger(f"grade: {grade}")

    except subprocess.CalledProcessError as e:
        print(f"Error running testssl.sh: {e}")
        return "Z",0

    if grade is not None:
        regexp = re.compile(r'A')  # Anything from an A- and better is good for us
        check_score = 1 if regexp.search(grade) else 0

    return grade, check_score
