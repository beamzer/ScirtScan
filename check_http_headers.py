"""Check that required HTTP security headers are present (HSTS, X-Frame-Options, etc.)."""
from __future__ import annotations

import logging
from pprint import pformat

import requests

from scirt.check import CheckContext, CheckResult

log = logging.getLogger("scirtscan.check.http_headers")

REQUIRED_HEADERS = {
    "X-XSS-Protection",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Strict-Transport-Security",
    "Referrer-Policy",
}

ONE_YEAR_SECONDS = 31_536_000


def _hsts_max_age(headers) -> int | None:
    if hasattr(headers, "get_all"):
        hsts_headers = headers.get_all("Strict-Transport-Security")
    else:
        raw = headers.get("Strict-Transport-Security", "")
        hsts_headers = raw.split(",") if raw else []
    if not hsts_headers:
        return None
    if len(hsts_headers) > 1:
        log.warning("more than one Strict-Transport-Security header present")
    parts = hsts_headers[0].split(";")
    max_age = next((p for p in parts if "max-age" in p), None)
    if not max_age:
        return None
    try:
        return int(max_age.split("=")[1].strip())
    except (IndexError, ValueError):
        return None


class HttpHeadersCheck:
    name = "http_headers"

    def run(self, ctx: CheckContext) -> CheckResult:
        log.debug("=== http_headers")
        ctx.outfile.write("\n===========HTTP Headers Check\n")

        try:
            response = ctx.http.get(ctx.url)
        except requests.exceptions.RequestException as e:
            log.error("connection error to %s: %s", ctx.website, e)
            ctx.outfile.write(f"Error connecting to {ctx.website}: {e}\n")
            return CheckResult(columns={"headers_check": 0, "hsts": None})

        missing = []
        for header in REQUIRED_HEADERS:
            present = header in response.headers
            ctx.outfile.write(f"checking presence of: {header} {'PRESENT' if present else 'NOT PRESENT'}\n")
            if not present:
                missing.append(header)

        check_header = 1
        hsts_duration_days: int | None = None

        if missing:
            ctx.outfile.write(f"ERR Missing headers for {ctx.website}: {', '.join(missing)}\n")
            check_header = 0

        hsts_seconds = _hsts_max_age(response.headers)
        if hsts_seconds is not None:
            hsts_duration_days = hsts_seconds // (24 * 3600)
            if hsts_seconds >= ONE_YEAR_SECONDS:
                ctx.outfile.write(
                    f"OK, {ctx.website} has HSTS value of at least one year: {hsts_duration_days} days\n"
                )
            else:
                ctx.outfile.write(
                    f"ERR, {ctx.website} HSTS value is LESS than one year: {hsts_duration_days} days\n"
                )
                check_header = 0
        else:
            ctx.outfile.write(f"ERR {ctx.website} is missing Strict-Transport-Security header\n")
            check_header = 0

        ctx.outfile.write(f"{pformat(dict(response.headers))}\n")

        return CheckResult(columns={"headers_check": check_header, "hsts": hsts_duration_days})


check = HttpHeadersCheck()
