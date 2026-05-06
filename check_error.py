"""Probe a 404 page for product/version leakage in the response body."""
from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from scirt.check import CheckContext, CheckResult

log = logging.getLogger("scirtscan.check.error")

DB_RE = re.compile(r"(Oracle|MySQL|SQL Server|PostgreSQL)")
WORD_RE = re.compile(r"\b(Apache|nginx|Php)\b")
NUMBER_RE = re.compile(r"\b\d+\.\d+\b")


class ErrorCheck:
    name = "error"

    def run(self, ctx: CheckContext) -> CheckResult:
        log.debug("=== error")
        ctx.outfile.write("\n===========Error Check\n")
        try:
            response = ctx.http.get(ctx.url + "/sdfsffe978hjcf65", timeout=3)
        except requests.RequestException as e:
            log.warning("failed to fetch error page for %s: %s", ctx.website, e)
            return CheckResult(columns={"error_check": 0})

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text()

        databases = DB_RE.findall(text)
        words = WORD_RE.findall(text)
        numbers = NUMBER_RE.findall(text)

        check_error = 0
        if databases:
            log.info("error page leaks db: %s", databases)
        elif words:
            log.info("error page leaks server words: %s", words)
        elif numbers:
            log.info("error page leaks numbers: %s", numbers)
        else:
            check_error = 1

        ctx.outfile.write("OK" if check_error else "NOK")
        ctx.outfile.write(f"\n<a href=\"{ctx.website}-error.txt\">{ctx.website}-error.txt</a>\n")

        return CheckResult(
            columns={"error_check": check_error},
            extra_files={f"{ctx.website}-error.txt": str(soup)},
        )


check = ErrorCheck()
