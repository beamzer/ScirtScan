"""Verify robots.txt only uses Allow (or a single Disallow: /); Disallow lines leak structure."""
from __future__ import annotations

import logging
import re

import requests

from scirt.check import CheckContext, CheckResult
from scirt.http import safe_content_type

log = logging.getLogger("scirtscan.check.robots")

DISALLOW_RE = re.compile(r"^Disallow:", re.I)
ALLOW_RE = re.compile(r"^Allow:", re.I)
DISALLOW_ALL_RE = re.compile(r"^Disallow:\s*/$", re.I)


def _evaluate(text: str) -> str:
    allow = disallow = disallow_all = 0
    for line in text.splitlines():
        if ALLOW_RE.match(line):
            allow += 1
        elif DISALLOW_ALL_RE.match(line):
            disallow_all += 1
        elif DISALLOW_RE.match(line):
            disallow += 1
    if disallow == 0 and allow > 0:
        return "OK"
    if disallow_all > 0 and disallow == 0:
        return "OK"
    return "NOK"


class RobotsCheck:
    name = "robots"

    def run(self, ctx: CheckContext) -> CheckResult:
        log.debug("=== robots")
        ctx.outfile.write("\n===========Robots Check\n")
        try:
            response = ctx.http.get(ctx.url + "/robots.txt")
        except requests.RequestException as e:
            log.warning("failed to fetch robots.txt for %s: %s", ctx.website, e)
            return CheckResult(columns={"robots_check": 0})

        ok = (
            200 <= response.status_code < 300
            and safe_content_type(response).startswith("text/plain")
        )
        if not ok:
            ctx.outfile.write("NOK\nrobots.txt missing or wrong Content-Type\n")
            return CheckResult(columns={"robots_check": 0})

        verdict = _evaluate(response.text)
        ctx.outfile.write(f"{verdict}\n{response.text}")
        return CheckResult(columns={"robots_check": 1 if verdict == "OK" else 0})


check = RobotsCheck()
