"""Run testssl.sh against a site and parse the overall grade out of its output."""
from __future__ import annotations

import logging
import os
import re
import subprocess

from scirt.check import CheckContext, CheckResult

log = logging.getLogger("scirtscan.check.testssl")

GRADE_RE = re.compile(r"Overall\s+Grade\s+([A-F][+-]?|-)")


class TestsslCheck:
    name = "testssl"

    def __init__(self, testssl_path: str = "/usr/local/bin/testssl.sh") -> None:
        self.testssl_path = testssl_path

    def run(self, ctx: CheckContext) -> CheckResult:
        log.debug("=== testssl")
        ctx.outfile.write("\n===========SSL/TLS Configuration with testssl.sh CHECK\n")

        if not os.path.exists(self.testssl_path):
            log.warning("testssl.sh not found at %s; skipping", self.testssl_path)
            ctx.outfile.write(f"testssl.sh not found at {self.testssl_path}\n")
            return CheckResult(columns={"grade": "Z", "grade_check": 0})

        try:
            output = subprocess.check_output(
                [self.testssl_path, "--color", "0", ctx.website],
                timeout=600,
            ).decode("utf-8", errors="replace")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            log.error("testssl.sh failed for %s: %s", ctx.website, e)
            ctx.outfile.write(f"testssl.sh error: {e}\n")
            return CheckResult(columns={"grade": "Z", "grade_check": 0})

        ctx.outfile.write(f"{output}\n")

        match = GRADE_RE.search(output)
        if not match:
            log.warning("could not parse grade from testssl.sh output for %s", ctx.website)
            return CheckResult(columns={"grade": "Z", "grade_check": 0})

        grade = match.group(1)
        log.debug("testssl grade for %s: %s", ctx.website, grade)
        check_score = 1 if "A" in grade else 0
        return CheckResult(columns={"grade": grade, "grade_check": check_score})


check = TestsslCheck()
