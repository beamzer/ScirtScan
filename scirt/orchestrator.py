"""Top-level scan orchestration: per-website pipeline + SSL score batching."""
from __future__ import annotations

import datetime
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .check import CheckContext, CheckResult
from .config import Config
from .db import Database
from .http import HttpClient
from .registry import standard_checks

log = logging.getLogger("scirtscan.orchestrator")


def read_websites(filename: str | Path) -> list[str]:
    """Read non-comment, non-blank lines from a website list file."""
    with open(filename, "r", encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]


def _write_extra_files(directory_path: str, files: dict[str, str]) -> None:
    for name, content in files.items():
        path = os.path.join(directory_path, name)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            log.error("failed to write %s: %s", path, e)


def scan_website(
    website: str,
    *,
    db: Database,
    http: HttpClient,
    directory_path: str,
    only_qualys: bool,
    only_testssl: bool,
    use_testssl: bool,
    skip_qualys: bool,
) -> bool:
    """Run the full check pipeline for one website. Returns True if HTTPS reachable."""
    from check_dns import check as dns_check
    from check_https_reachable import check as https_check
    from check_http_redirected_to_https import check as redirect_check
    from check_testssl import check as testssl_check

    https_reachable = False
    myfile = os.path.join(directory_path, f"{website}.html")
    check_date = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

    with open(myfile, "a", encoding="utf-8") as outfile:
        outfile.write("<html>\n<body>\n<pre>\n")
        outfile.write(f"{website} checks started on: {check_date}\n")
        log.info("=" * 60 + " %s", website)

        url = f"https://{website}"
        ctx = CheckContext(
            website=website,
            url=url,
            http=http,
            directory_path=directory_path,
            outfile=outfile,
        )

        dns_result = dns_check.run(ctx)
        if not dns_result.gate_passed:
            log.info("%s: DNS lookup failed, skipping further checks", website)
            outfile.write("</pre>\n</body>\n</html>")
            return False

        db.upsert_website(website, check_date)

        https_result = https_check.run(ctx)
        db.update(website, https_result.columns)
        https_reachable = https_result.gate_passed

        if not https_reachable:
            outfile.write("</pre>\n</body>\n</html>")
            return False

        if only_qualys:
            outfile.write("</pre>\n</body>\n</html>")
            return True

        if only_testssl:
            tssl = testssl_check.run(ctx)
            db.update(website, tssl.columns)
            _write_extra_files(directory_path, tssl.extra_files)
            outfile.write("</pre>\n</body>\n</html>")
            return True

        for check in standard_checks():
            try:
                result = check.run(ctx)
            except Exception as e:  # don't let one check kill the whole site
                log.error("%s: check %s raised: %s", website, check.name, e)
                continue
            db.update(website, result.columns)
            _write_extra_files(directory_path, result.extra_files)

        try:
            redir = redirect_check.run(ctx)
            db.update(website, redir.columns)
        except Exception as e:
            log.error("%s: redirect check raised: %s", website, e)

        if use_testssl:
            tssl = testssl_check.run(ctx)
            db.update(website, tssl.columns)
            _write_extra_files(directory_path, tssl.extra_files)

        if skip_qualys:
            done_date = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            outfile.write(f"{website} checks done at: {done_date}\n")

        outfile.write("</pre>\n</body>\n</html>")

    return https_reachable


def run_qualys_batch(
    websites: list[str],
    *,
    use_cache: bool,
    directory_path: str,
    db: Database,
    max_retries: int,
) -> None:
    """Run Qualys SSL Labs scoring with retry batching for sites that don't grade quickly."""
    from check_sslscore import check_sslscore

    log.info("starting Qualys SSL checks for %d sites", len(websites))
    pending = list(websites)
    rounds_left = max_retries
    while pending and rounds_left >= 0:
        log.info("Qualys round %d (pending=%d)", max_retries - rounds_left + 1, len(pending))
        results, retry = check_sslscore(pending, use_cache, directory_path, log.info)
        for website, grade, check_score in results:
            db.update(website, {"grade": grade, "grade_check": check_score})
        pending = retry
        rounds_left -= 1
    if pending:
        log.warning("Qualys SSL did not complete for: %s", pending)


def run_scan(
    *,
    config: Config,
    websites: list[str],
    directory_path: str,
    version: str,
    anon: bool,
    skip_qualys: bool,
    only_qualys: bool,
    use_testssl: bool,
    only_testssl: bool,
    use_cache: bool,
    parallel: int = 1,
) -> None:
    """Run a full scan over `websites`, writing results into `directory_path`."""
    http = HttpClient(user_agent=config.user_agent(anon=anon), timeout=config.default_timeout)
    db = Database(directory_path, version=version)

    qualys_pool: list[str] = []

    def _scan_one(website: str) -> None:
        if scan_website(
            website,
            db=db,
            http=http,
            directory_path=directory_path,
            only_qualys=only_qualys,
            only_testssl=only_testssl,
            use_testssl=use_testssl,
            skip_qualys=skip_qualys,
        ):
            qualys_pool.append(website)

    if parallel > 1:
        with ThreadPoolExecutor(max_workers=parallel) as ex:
            list(ex.map(_scan_one, websites))
    else:
        for w in websites:
            _scan_one(w)

    if not (skip_qualys or use_testssl or only_testssl):
        run_qualys_batch(
            qualys_pool,
            use_cache=use_cache,
            directory_path=directory_path,
            db=db,
            max_retries=config.sslscore_max_retries,
        )

    db.close()
    log.info("ALL DONE on: %s", datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"))
