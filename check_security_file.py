"""Check for /.well-known/security.txt (CVD contact)."""
from __future__ import annotations

import logging
from pprint import pformat

import requests

from scirt.check import CheckContext, CheckResult
from scirt.http import safe_content_type

log = logging.getLogger("scirtscan.check.security_file")


class SecurityFileCheck:
    name = "security_file"

    def run(self, ctx: CheckContext) -> CheckResult:
        log.debug("=== security_file")
        ctx.outfile.write("\n===========Security.txt Check\n")
        try:
            response = ctx.http.get(f"{ctx.url}/.well-known/security.txt")
        except requests.RequestException as e:
            log.error("error fetching security.txt for %s: %s", ctx.website, e)
            ctx.outfile.write(f"Error: {e}\n")
            return CheckResult(columns={"security_txt": 0})

        if 200 <= response.status_code < 300 and safe_content_type(response).startswith("text/plain"):
            ctx.outfile.write("OK\n")
            ctx.outfile.write(response.text)
            return CheckResult(columns={"security_txt": 1})

        ctx.outfile.write("NOK\n")
        ctx.outfile.write(f"HTTP response code: {response.status_code}\n")
        ctx.outfile.write(f"{pformat(dict(response.headers))}\n")
        return CheckResult(columns={"security_txt": 0})


check = SecurityFileCheck()
