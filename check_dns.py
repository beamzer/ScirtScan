"""DNS check: must succeed before any other check is attempted."""
from __future__ import annotations

import logging

import dns.exception
import dns.resolver

from scirt.check import CheckContext, CheckResult

log = logging.getLogger("scirtscan.check.dns")


def _resolve_optional(website: str, rtype: str, label: str, outfile, missing_msg: str) -> None:
    try:
        for answer in dns.resolver.resolve(website, rtype):
            if rtype == "TXT":
                for txt_string in answer.strings:
                    text = txt_string.decode("utf-8", errors="replace")
                    log.debug("%s: %s", label, text)
                    outfile.write(f"{label}: {text}\n")
            elif rtype == "CNAME":
                target = answer.target.to_text()
                log.debug("%s: %s", label, target)
                outfile.write(f"{label}: {target}\n")
            elif rtype == "MX":
                exchange = answer.exchange.to_text()
                log.debug("%s: %s", label, exchange)
                outfile.write(f"{label}: {exchange}\n")
            else:
                log.debug("%s", answer.address)
                outfile.write(f"{answer.address}\n")
    except dns.resolver.NoAnswer:
        log.debug(missing_msg)
        outfile.write(missing_msg + "\n")


class DNSCheck:
    name = "dns"

    def run(self, ctx: CheckContext) -> CheckResult:
        log.debug("=== dns")
        ctx.outfile.write("\n===========DNS Check\n")

        try:
            for answer in dns.resolver.resolve(ctx.website, "A"):
                log.debug("%s", answer.address)
                ctx.outfile.write(f"{answer.address}\n")
        except dns.resolver.NoNameservers:
            msg = f"DNS lookup for {ctx.website} failed with SERVFAIL"
            log.warning(msg)
            ctx.outfile.write(msg + "\n")
            return CheckResult(gate_passed=False)
        except dns.resolver.NXDOMAIN:
            msg = f"NXDOMAIN; Website {ctx.website} not found"
            log.warning(msg)
            ctx.outfile.write(msg + "\n")
            return CheckResult(gate_passed=False)
        except dns.resolver.LifetimeTimeout as e:
            msg = f"DNS resolution for {ctx.website} timed out: {e}"
            log.warning(msg)
            ctx.outfile.write(msg + "\n")
            return CheckResult(gate_passed=False)
        except dns.exception.DNSException as e:
            log.error("DNS error for %s: %s", ctx.website, e)
            ctx.outfile.write(f"DNS error: {e}\n")
            return CheckResult(gate_passed=False)

        _resolve_optional(ctx.website, "AAAA", "ipv6", ctx.outfile, "no IPv6 addresses")
        _resolve_optional(ctx.website, "CNAME", "cname", ctx.outfile, "no CNAMEs")
        _resolve_optional(ctx.website, "MX", "mx", ctx.outfile, "no MX records")
        _resolve_optional(ctx.website, "TXT", "TXT", ctx.outfile, "no TXT records")

        return CheckResult(gate_passed=True)


check = DNSCheck()
