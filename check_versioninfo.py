"""Detect leaked version info in HTTP server / framework headers."""
from __future__ import annotations

import logging
import re

import requests

from scirt.check import CheckContext, CheckResult

log = logging.getLogger("scirtscan.check.versioninfo")

HEADERS_TO_CHECK = [
    "server",
    "x-generator",
    "x-powered-by",
    "via",
    "x-aspnet-version",
    "x-aspnetmvc-version",
    "x-drupal-cache",
    "x-joomla-version",
    "x-wordpress",
    "x-engine",
]

VERSION_HINT = re.compile(r".*[0-9].*", re.IGNORECASE)


class VersioninfoCheck:
    name = "versioninfo"

    def run(self, ctx: CheckContext) -> CheckResult:
        log.debug("=== versioninfo")
        ctx.outfile.write("\n===========Version Info CHECK\n")
        try:
            response = ctx.http.head(ctx.url)
        except requests.RequestException as e:
            log.error("failed to fetch %s: %s", ctx.url, e)
            return CheckResult(columns={"version_check": 0})

        check_version = 1
        result = "OK"
        for header in HEADERS_TO_CHECK:
            if header in response.headers:
                value = response.headers[header]
                if VERSION_HINT.match(value):
                    msg = f"Might be version info: {header}: {value}"
                    log.info(msg)
                    ctx.outfile.write(msg + "\n")
                    result = "NOK"
                    check_version = 0
        ctx.outfile.write(result + "\n")
        return CheckResult(columns={"version_check": check_version})


check = VersioninfoCheck()
