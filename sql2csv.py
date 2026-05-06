#!/usr/bin/env python3
"""Dump the website_checks table to semicolon-delimited CSV on stdout."""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import date

from scirt.exporters.common import db_columns, fetch_rows, open_db

VERSION = "v2.0"


def main(argv: list[str] | None = None) -> None:
    today = date.today().strftime("%Y%m%d")
    parser = argparse.ArgumentParser(description="dump website_checks as CSV to stdout")
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        default=today,
        help=f"directory containing websites.db (default: {today})",
    )
    parser.add_argument("-v", "--version", action="store_true")
    args = parser.parse_args(argv)

    if args.version:
        print(f"version: {VERSION}")
        return

    if not os.path.exists(args.path):
        sys.exit(f"directory {args.path} does not exist")

    with open_db(args.path) as conn:
        columns = db_columns(conn)
        rows = fetch_rows(conn, columns)

    writer = csv.writer(sys.stdout, delimiter=";")
    writer.writerow(columns)
    writer.writerows(rows)


if __name__ == "__main__":
    main()
