"""Detect 'debug' substring in HTTP header names/values (e.g. phpdebugbar-id)."""
from __future__ import annotations

import logging

import requests

from scirt.check import CheckContext, CheckResult

log = logging.getLogger("scirtscan.check.debug_in_headers")


class DebugInHeadersCheck:
    name = "debug_in_headers"

    def run(self, ctx: CheckContext) -> CheckResult:
        log.debug("=== debug_in_headers")
        ctx.outfile.write('\n===========Check for "debug" in HTTP header info\n')
        try:
            response = ctx.http.get(ctx.url)
        except requests.exceptions.RequestException as e:
            log.error("connection error to %s: %s", ctx.url, e)
            ctx.outfile.write(f"Error connecting to {ctx.url}: {e}\n")
            return CheckResult(columns={"debug": 1})

        for key, value in response.headers.items():
            if "debug" in key.lower() or "debug" in (value or "").lower():
                msg = f"'debug' found in {key} header for {ctx.url}"
                log.info(msg)
                ctx.outfile.write(f"NOK\n{msg}\n")
                return CheckResult(columns={"debug": 0})

        ctx.outfile.write("OK\ndebug not found in HTTP headers\n")
        return CheckResult(columns={"debug": 1})


check = DebugInHeadersCheck()
