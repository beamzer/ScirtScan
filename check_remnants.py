"""Probe for leftover CMS install files (config-installer.php, etc.)."""
from __future__ import annotations

import logging
from pathlib import Path

import requests

from scirt.check import CheckContext, CheckResult

log = logging.getLogger("scirtscan.check.remnants")

REMNANTS_FILE = "remnants.txt"
PROBE_RANDOM_PATH = "iu87h8hkhkgigy"


def _read_remnant_names(path: str = REMNANTS_FILE) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    return [
        line.strip()
        for line in p.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


class RemnantsCheck:
    name = "remnants"

    def run(self, ctx: CheckContext) -> CheckResult:
        log.debug("=== remnants")
        ctx.outfile.write("\n===========Check for installation files left behind\n")

        filenames = _read_remnant_names()
        if not filenames:
            ctx.outfile.write("remnants.txt missing or empty\n")
            return CheckResult(columns={"remnants": 0})

        # If the server returns 200 for any random path, treat as catch-all
        # and skip the check (otherwise every probe falsely "succeeds").
        try:
            probe = ctx.http.get(f"{ctx.url}/{PROBE_RANDOM_PATH}")
        except requests.RequestException as e:
            log.warning("probe request failed for %s: %s", ctx.website, e)
            return CheckResult(columns={"remnants": 0})

        if probe.status_code == 200:
            ctx.outfile.write("Server returns 200 for arbitrary paths; skipping\n")
            return CheckResult(columns={"remnants": 1})

        found: list[str] = []
        for fname in filenames:
            file_url = f"{ctx.url}/{fname}"
            try:
                resp = ctx.http.get(file_url)
                if resp.status_code == 200:
                    found.append(file_url)
            except requests.RequestException as e:
                log.warning("error checking %s: %s", file_url, e)

        if found:
            ctx.outfile.write(f"The following files gave a 200 response from {ctx.website}:\n")
            for f in found:
                ctx.outfile.write(f"- {f}\n")
            return CheckResult(columns={"remnants": 0})

        ctx.outfile.write(f"No files from remnants.txt were found on {ctx.url}.\n")
        return CheckResult(columns={"remnants": 1})


check = RemnantsCheck()
