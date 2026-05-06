#!/usr/bin/env python3
"""Render website_checks into a colored Excel workbook."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

import openpyxl
from openpyxl.styles import Font, PatternFill

from scirt.exporters.common import db_columns, fetch_rows, open_db

VERSION = "v3.0"

EXCEL_HEADERS = [
    "website",
    "https",
    "grade",
    "grade check",
    "HTTPS redirect",
    "certificate validity",
    "HSTS",
    "headers",
    "security.txt",
    "robots.txt",
    "version",
    "error",
    "remnants",
    "debug",
    "detailed log",
]

# Columns whose 0/1 values render as red/green NotOK/OK cells. The rest
# (website, grade, validity, hsts, date) stay raw.
BOOLEAN_COL_INDEXES = {1, 3, 4, 7, 8, 9, 10, 11, 12, 13}


def main(argv: list[str] | None = None) -> None:
    today = date.today().strftime("%Y%m%d")
    parser = argparse.ArgumentParser(description="render website_checks as a colored Excel workbook")
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

    workbook = openpyxl.Workbook()
    worksheet = workbook.active

    header_style = Font(bold=True)
    ok_fill = PatternFill(start_color="00FF89", end_color="00FF89", fill_type="solid")
    notok_fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")

    for col, header in enumerate(EXCEL_HEADERS, start=1):
        worksheet.cell(row=1, column=col, value=header).font = header_style
        worksheet.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 15

    for row_idx, data in enumerate(rows, start=2):
        for col_idx, value in enumerate(data):
            cell = worksheet.cell(row=row_idx, column=col_idx + 1, value=value)
            if col_idx in BOOLEAN_COL_INDEXES:
                if value == 1:
                    cell.fill = ok_fill
                    cell.value = "OK"
                else:
                    cell.fill = notok_fill
                    cell.value = "NotOK"

    excelfile = os.path.join(args.path, "website_checks.xlsx")
    try:
        workbook.save(excelfile)
        print(f"saving to: {excelfile}")
    except OSError as e:
        sys.exit(f"Error saving excel file: {e}")


if __name__ == "__main__":
    main()
