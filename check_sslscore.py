###########################################################################################################
# This checks that the websites have the right grade according to Qualys SSLscore
# 20240521
###########################################################################################################
import os
import requests
import re
import time
import datetime

def check_sslscore(websites, use_cache, directory_path, logger):
    """
    Args:
    websites (list): The websites to be checked.
    use_cache (boolean): Wether to accept cached results or request a fresh test
    directory_path (str): where to store detail/debug output
    logger (function pointer): Function to print debug information.
    """

    base_url = "https://api.ssllabs.com/api/v3"
    info_url = f"{base_url}/info"
    retry = []
    results = []

    # Define maximum retry attempts and the wait time for rate limit errors
    max_retries = 4
    wait_time = 30

    for website in websites:
        retry_count = 0
        myfile = os.path.join(directory_path, f"{website}.html")
        with open(myfile, "a") as outfile:
            outfile.write("===========Qualys SSLscan\n")

            while retry_count < max_retries:
                try:
                    logger(f"\ncheck_sslscore for: {website}")
                    # Get rate limits
                    rate_limit_response = requests.head(info_url)
                    rate_limit_response.raise_for_status()
                    max_assessments = int(rate_limit_response.headers.get('X-Max-Assessments', 0))
                    current_assessments = int(rate_limit_response.headers.get('X-Current-Assessments', 0))
                    logger(f"SSLlabs API: max and current assessment values are: {max_assessments} {current_assessments}")

                    if current_assessments < max_assessments:
                        time.sleep(5)
                        check_score = 0
                        # analyze_url = f"{base_url}/analyze?host={website}&all=done&publish=off&fromCache={'on' if use_cache else 'off'}"
                        if use_cache:
                            analyze_url = f"{base_url}/analyze?host={website}&all=done&publish=off&fromCache=on&maxAge=18"
                        else:
                            analyze_url = f"{base_url}/analyze?host={website}&all=done&publish=off&fromCache=off"
                        response = requests.get(analyze_url)
                        response.raise_for_status()

                        analysis_result = response.json()
                        endpoints = analysis_result.get("endpoints", [])
                        if endpoints:
                            for endpoint in endpoints:
                                grade = endpoint.get("grade", "N/A")
                                if grade != "N/A":
                                    ipaddr = endpoint.get("ipAddress", "N/A")
                                    logger(f"Website: {website}, endpoint: {ipaddr} Grade: {grade}")
                                    regexp = re.compile(r'A')
                                    check_score = 1 if regexp.search(grade) else 0
                                    outfile.write(f"{'OK' if check_score == 1 else 'NOK'}\nSSLscan grade for {ipaddr}: {grade}")

                                    sslscanfile = os.path.join(directory_path, f"{website}-sslscan.json")
                                    with open(sslscanfile, "w") as sfile:
                                        try:
                                            sfile.write(f"{response.text}")
                                            outfile.write(f"\n<a href=\"{website}-sslscan.json\">{website}-sslscan.json</a>\n")
                                        except OSError as e:
                                            sys.exit(f"Error trying to open for writing {sslscanfile}: {e}")
                                    sfile.close()

                                    done_date = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                                    outfile.write(f"{website} checks done at: {done_date} \n")
                                    results.append((website, grade, check_score))

                                else:
                                    logger(f"{website} did not return a grade, will retry")
                                    if website not in retry:
                                        retry.append(website)

                        else:
                            logger(f"No endpoints found for {website} yet")
                            if website not in retry:
                                retry.append(website)

                        break

                    logger(f"Rate limit reached, waiting {wait_time} seconds before retrying")
                    time.sleep(wait_time)

                except requests.exceptions.HTTPError as e:
                    if e.response.status_code in [429, 529]:
                        retry_count += 1
                        logger(f"Received {e.response.status_code} error, retry {retry_count}/{max_retries}. Waiting {wait_time} seconds before retrying")
                        time.sleep(wait_time)
                    else:
                        logger(f"HTTP Error: {e}")
                        break
                except requests.exceptions.RequestException as e:
                    logger(f"Request Error: {e}")
                    break

            if retry_count == max_retries:
                logger(f"Max retries reached for {website}")
                retry.append(website)

    return results, retry
