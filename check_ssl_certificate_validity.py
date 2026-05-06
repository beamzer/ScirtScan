"""Check days remaining on the website's SSL/TLS certificate."""
from __future__ import annotations

import datetime
import logging
import socket
import ssl

from scirt.check import CheckContext, CheckResult

log = logging.getLogger("scirtscan.check.ssl_cert")


class SslCertificateValidityCheck:
    name = "ssl_certificate_validity"

    def run(self, ctx: CheckContext) -> CheckResult:
        log.debug("=== ssl_certificate_validity")
        ctx.outfile.write("\n===========Certificate validity Check\n")
        try:
            context = ssl.create_default_context()
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED

            with socket.create_connection((ctx.website, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=ctx.website) as ssock:
                    cert_info = ssock.getpeercert()

            cert_expiration = datetime.datetime.strptime(
                cert_info["notAfter"], "%b %d %H:%M:%S %Y %Z"
            ).replace(tzinfo=datetime.timezone.utc)
            cert_ca = cert_info["issuer"]
            now = datetime.datetime.now(datetime.timezone.utc)
            days_left = (cert_expiration - now).days

            ctx.outfile.write(f"certificate expiration: {cert_expiration}\n")
            ctx.outfile.write(f"time of check (utc)   : {now}\n")
            ctx.outfile.write(f"certificate days left : {days_left}\n")
            ctx.outfile.write(f"certificate issuer    : {cert_ca}\n")
            ctx.outfile.write("OK\n" if days_left > 29 else "NOK\n")
            return CheckResult(columns={"cert_validity": days_left})
        except (ssl.SSLError, socket.error, OSError) as e:
            log.error("SSL error for %s: %s", ctx.website, e)
            ctx.outfile.write(f"SSL Error: {e}\n")
            return CheckResult(columns={"cert_validity": 0})


check = SslCertificateValidityCheck()
