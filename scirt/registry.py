"""Registry of all checks the orchestrator runs against each website."""
from __future__ import annotations

from .check import Check


def standard_checks() -> list[Check]:
    """The set of regular per-website checks that run after HTTPS reachability passes.

    The DNS gate, HTTPS-reachability gate, HTTP→HTTPS redirect check, and SSL
    Labs scoring are run separately by the orchestrator (each has special
    sequencing or batching needs).
    """
    from check_http_headers import check as http_headers
    from check_versioninfo import check as versioninfo
    from check_robots import check as robots
    from check_error import check as error
    from check_security_file import check as security_file
    from check_remnants import check as remnants
    from check_ssl_certificate_validity import check as cert_validity
    from check_debug_in_headers import check as debug_in_headers

    return [
        http_headers,
        versioninfo,
        robots,
        error,
        security_file,
        remnants,
        cert_validity,
        debug_in_headers,
    ]
