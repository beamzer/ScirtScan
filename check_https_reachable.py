"""Check whether the site is reachable over HTTPS. Gates further HTTP-based checks."""
from __future__ import annotations

import logging

import requests

from scirt.check import CheckContext, CheckResult

log = logging.getLogger("scirtscan.check.https_reachable")


class HttpsReachableCheck:
    name = "https_reachable"

    def run(self, ctx: CheckContext) -> CheckResult:
        log.debug("=== https_reachable")
        ctx.outfile.write("\n===========HTTPS reachable check\n")
        try:
            response = ctx.http.get(ctx.url)
            response.raise_for_status()
            log.debug("Response Code: %s", response.status_code)
            ctx.outfile.write(f"Response Code: {response.status_code}")
            return CheckResult(columns={"https_reachable": 1}, gate_passed=True)
        except requests.exceptions.HTTPError as e:
            # 4xx/5xx still proves HTTPS is reachable.
            log.debug("HTTPS reachable but error code: %s", e.response.status_code)
            ctx.outfile.write(f"Response is {e}")
            return CheckResult(columns={"https_reachable": 1}, gate_passed=True)
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.TooManyRedirects,
        ) as e:
            log.warning("%s unreachable over HTTPS: %s", ctx.website, type(e).__name__)
            ctx.outfile.write(f"{type(e).__name__}: {e}")
            return CheckResult(columns={"https_reachable": 0}, gate_passed=False)


check = HttpsReachableCheck()
