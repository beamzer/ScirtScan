"""Qualys SSL Labs grade lookup (batched, with retry semantics).

Kept as a plain function rather than a Check protocol implementation because
the orchestrator runs Qualys scoring as a batched second pass with retry
logic — the per-site Check pipeline doesn't fit that shape.
"""
from __future__ import annotations

import datetime
import logging
import os
import re
import time
from typing import Callable

import requests

log = logging.getLogger("scirtscan.check.sslscore")

BASE_URL = "https://api.ssllabs.com/api/v3"
INFO_URL = f"{BASE_URL}/info"
MAX_RETRIES = 4
RATE_LIMIT_WAIT = 30
GRADE_A = re.compile(r"A")


def _build_analyze_url(website: str, use_cache: bool) -> str:
    if use_cache:
        return f"{BASE_URL}/analyze?host={website}&all=done&publish=off&fromCache=on&maxAge=18"
    return f"{BASE_URL}/analyze?host={website}&all=done&publish=off&fromCache=off"


def check_sslscore(
    websites: list[str],
    use_cache: bool,
    directory_path: str,
    logger: Callable[[str], None] | None = None,
) -> tuple[list[tuple[str, str, int]], list[str]]:
    """Look up the Qualys SSL Labs grade for each website.

    Args:
        websites: list of websites to check
        use_cache: whether to accept Qualys cached results
        directory_path: where to drop the per-site sslscan.json
        logger: optional callable for backward compatibility (defaults to module logger)

    Returns:
        tuple of (results, retry) where results is a list of
        (website, grade, check_score) and retry is the list of websites
        that didn't grade and should be tried again later.
    """
    if logger is None:
        logger = log.info  # type: ignore[assignment]

    retry: list[str] = []
    results: list[tuple[str, str, int]] = []

    for website in websites:
        retry_count = 0
        myfile = os.path.join(directory_path, f"{website}.html")
        with open(myfile, "a", encoding="utf-8") as outfile:
            outfile.write("===========Qualys SSLscan\n")

            while retry_count < MAX_RETRIES:
                try:
                    logger(f"check_sslscore for: {website}")
                    rate_limit = requests.head(INFO_URL, timeout=10)
                    rate_limit.raise_for_status()
                    max_assess = int(rate_limit.headers.get("X-Max-Assessments", 0))
                    cur_assess = int(rate_limit.headers.get("X-Current-Assessments", 0))
                    logger(f"SSLlabs API max/current assessments: {max_assess} {cur_assess}")

                    if cur_assess < max_assess:
                        time.sleep(5)
                        analyze_url = _build_analyze_url(website, use_cache)
                        response = requests.get(analyze_url, timeout=30)
                        response.raise_for_status()

                        analysis = response.json()
                        endpoints = analysis.get("endpoints", [])
                        if not endpoints:
                            logger(f"No endpoints found for {website} yet")
                            if website not in retry:
                                retry.append(website)
                            break

                        for endpoint in endpoints:
                            grade = endpoint.get("grade", "N/A")
                            if grade == "N/A":
                                logger(f"{website} did not return a grade, will retry")
                                if website not in retry:
                                    retry.append(website)
                                continue
                            ipaddr = endpoint.get("ipAddress", "N/A")
                            logger(f"Website: {website} endpoint: {ipaddr} Grade: {grade}")
                            check_score = 1 if GRADE_A.search(grade) else 0
                            outfile.write(
                                f"{'OK' if check_score else 'NOK'}\nSSLscan grade for {ipaddr}: {grade}"
                            )

                            sslscanfile = os.path.join(directory_path, f"{website}-sslscan.json")
                            try:
                                with open(sslscanfile, "w", encoding="utf-8") as sfile:
                                    sfile.write(response.text)
                                outfile.write(
                                    f"\n<a href=\"{website}-sslscan.json\">{website}-sslscan.json</a>\n"
                                )
                            except OSError as e:
                                log.error("could not write %s: %s", sslscanfile, e)

                            done_date = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                            outfile.write(f"{website} checks done at: {done_date}\n")
                            results.append((website, grade, check_score))
                        break

                    logger(f"Rate limit reached, waiting {RATE_LIMIT_WAIT}s")
                    time.sleep(RATE_LIMIT_WAIT)

                except requests.exceptions.HTTPError as e:
                    if e.response is not None and e.response.status_code in (429, 529):
                        retry_count += 1
                        logger(
                            f"Got {e.response.status_code}, retry {retry_count}/{MAX_RETRIES}; "
                            f"waiting {RATE_LIMIT_WAIT}s"
                        )
                        time.sleep(RATE_LIMIT_WAIT)
                    else:
                        logger(f"HTTP Error: {e}")
                        break
                except requests.exceptions.RequestException as e:
                    logger(f"Request Error: {e}")
                    break

            if retry_count == MAX_RETRIES and website not in retry:
                logger(f"Max retries reached for {website}")
                retry.append(website)

    return results, retry
