"""Verify that http://<site> redirects to https://<site>."""
from __future__ import annotations

import logging

import requests

from scirt.check import CheckContext, CheckResult

log = logging.getLogger("scirtscan.check.http_redirect")


class HttpRedirectedToHttpsCheck:
    name = "http_redirected_to_https"

    def run(self, ctx: CheckContext) -> CheckResult:
        log.debug("=== http_redirected_to_https")
        ctx.outfile.write("\n===========Check for only accessible through HTTPS\n")
        http_url = f"http://{ctx.website}"

        try:
            response = ctx.http.get(http_url, allow_redirects=False)
            response.raise_for_status()
            ctx.outfile.write(f"HTTP request returns response code: {response.status_code}\n")
            no_http = False
        except requests.exceptions.ConnectionError:
            ctx.outfile.write(f"HTTP Connection failed: {http_url} not reachable on port 80.\n")
            # No HTTP listener at all is also OK from a security view.
            return CheckResult(columns={"redirect_check": 1})
        except requests.exceptions.Timeout:
            ctx.outfile.write(f"HTTP Request timed out: {http_url}.\n")
            return CheckResult(columns={"redirect_check": 1})
        except requests.exceptions.HTTPError as err:
            ctx.outfile.write(f"HTTP error: {err}\n")
            no_http = False
        except requests.exceptions.RequestException as err:
            ctx.outfile.write(f"HTTP error: {err}\n")
            return CheckResult(columns={"redirect_check": 1})

        try:
            response = ctx.http.get(http_url, allow_redirects=True)
        except requests.exceptions.RequestException as err:
            log.warning("redirect-following request failed: %s", err)
            ctx.outfile.write(f"redirect-following request failed: {err}\n")
            return CheckResult(columns={"redirect_check": 0})

        if response.history and response.url.startswith("https://"):
            ctx.outfile.write(f"{http_url} redirects HTTP to HTTPS\n")
            ctx.outfile.write(f"final URL is: {response.url}\n")
            return CheckResult(columns={"redirect_check": 1})
        ctx.outfile.write(f"ERR {http_url} does not redirect HTTP to HTTPS\n")
        ctx.outfile.write(f"final URL is: {response.url}\n")
        return CheckResult(columns={"redirect_check": 0})


check = HttpRedirectedToHttpsCheck()
