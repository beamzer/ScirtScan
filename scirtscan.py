#!/usr/bin/env python3
"""ScirtScan entry point.

The heavy lifting lives in `scirt/`. This script is now just a CLI shell that
parses arguments, loads config, sets up logging + the YYYYMMDD output directory,
and then hands control to `scirt.orchestrator.run_scan`.
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys

from scirt import __version__ as version
from scirt.config import load_config
from scirt.log import configure as configure_logging
from scirt.orchestrator import read_websites, run_scan


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="check websites")
    parser.add_argument("-d", "--debug", action="store_true", help="print debug messages to stderr")
    parser.add_argument("-a", "--anon", action="store_true", help="don't tag User-Agent with CERT name")
    parser.add_argument("-v", "--version", action="store_true", help="show version info and exit")
    parser.add_argument("-nq", "--no_qualys", action="store_true", help="exclude Qualys SSLtest")
    parser.add_argument("-oq", "--only_qualys", action="store_true", help="only run Qualys SSLtest")
    parser.add_argument("-t", "--testssl", action="store_true", help="use locally installed testssl.sh instead of Qualys")
    parser.add_argument("-ot", "--only_testssl", action="store_true", help="only run testssl.sh checks")
    parser.add_argument("-nc", "--no_cache", action="store_true", help="always request fresh tests from Qualys")
    parser.add_argument(
        "-ndf",
        "--no_debugfile",
        action="store_true",
        help="don't write debug.log into the YYYYMMDD directory",
    )
    parser.add_argument(
        "-p",
        "--parallel",
        type=int,
        default=None,
        help="number of websites to scan concurrently (overrides config)",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="scirtscan.toml",
        help="path to TOML config file",
    )
    parser.add_argument("filename", metavar="FILENAME", type=str, nargs="?", help="file with website list")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.version and not args.filename:
        print(f"version: {version}")
        return

    if not args.filename:
        sys.exit("ERROR: missing FILENAME")

    config = load_config(args.config)
    parallel = args.parallel if args.parallel is not None else config.parallel_websites

    today = datetime.date.today().strftime("%Y%m%d")
    if not os.path.exists(today):
        try:
            os.makedirs(today)
        except OSError as e:
            sys.exit(f"Error trying to create {today}: {e}")

    log = configure_logging(today, debug=args.debug, log_to_file=not args.no_debugfile)
    if not args.no_debugfile:
        print(f"debug.log output written to {os.path.join(today, 'debug.log')}")

    log.info("ScirtScan %s starting at %s", version, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    if not os.path.exists(args.filename):
        sys.exit(f"The file {args.filename} does not exist.")
    websites = read_websites(args.filename)
    log.info("read %d websites from %s", len(websites), args.filename)

    try:
        run_scan(
            config=config,
            websites=websites,
            directory_path=today,
            version=version,
            anon=args.anon,
            skip_qualys=args.no_qualys,
            only_qualys=args.only_qualys,
            use_testssl=args.testssl,
            only_testssl=args.only_testssl,
            use_cache=not args.no_cache,
            parallel=parallel,
        )
    except KeyboardInterrupt:
        sys.exit("as you wish, aborting...")


if __name__ == "__main__":
    main()
