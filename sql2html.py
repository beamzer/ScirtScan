#!/usr/bin/env python3
"""Render website_checks into a sortable index.html."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from scirt.exporters.common import db_columns, fetch_rows, open_db

VERSION = "v3.0"

THIS_DIR = Path(__file__).resolve().parent

TABLE_HEADERS = [
    ("website", "sortTable", 0),
    ("https", "sortTable", 1),
    ("grade", "sortGrades", 2),
    ("grade<br>check", "sortTable", 3),
    ("HTTPS<br>redirect", "sortTable", 4),
    ("cert<br>validity", "sortTable", 5),
    ("HSTS<br>(days)", "sortTable", 6),
    ("security<br>.txt", "sortTable", 7),
    ("version", "sortTable", 8),
    ("error", "sortTable", 9),
    ("remnants", "sortTable", 10),
    ("debug", "sortTable", 11),
    ("headers", "sortTable", 12),
    ("detailed log", "sortTable", 13),
]


def _bool_cell(value: object) -> str:
    if value == 1:
        return '<td class="green">&#x2705;</td>'
    if value == 0:
        return '<td class="red">&#10006;</td>'
    return '<td class="orange"><b>&quest;</b></td>'


def _grade_cell(grade: object, grad_check: object, website: str) -> str:
    if grad_check == 1:
        klass = "green"
    elif grad_check == 0:
        klass = "red"
    else:
        klass = "orange"
    if grad_check in (0, 1):
        link = f'<a href="https://www.ssllabs.com/ssltest/analyze.html?d={website}&hideResults=on">{grade}</a>'
    else:
        link = '<b>&quest;</b>'
    return f'<td class="{klass}">{link}</td>'


def _cert_cell(cert_valid: object) -> str:
    if cert_valid is None:
        return '<td class="orange"><b>&quest;</b></td>'
    if cert_valid > 29:
        return f'<td class="green">{cert_valid}</td>'
    return f'<td class="red">{cert_valid}</td>'


def _hsts_cell(hsts: object) -> str:
    if hsts is None:
        return '<td class="red">&#10006;</td>'
    if hsts >= 365:
        return f'<td class="green">{hsts}</td>'
    return f'<td class="red">{hsts}</td>'


def _security_cell(value: object, website: str) -> str:
    if value == 1:
        link = f'<a class="check" href="https://{website}/.well-known/security.txt">&#x2705;</a>'
        return f'<td class="green">{link}</td>'
    if value == 0:
        return '<td class="red">&#10006;</td>'
    return '<td class="orange"><b>&quest;</b></td>'


def render_row(row: tuple) -> str:
    (
        website,
        https_check,
        grade,
        grad_check,
        redirect_check,
        cert_valid,
        hsts,
        security_txt,
        vers_check,
        _robots_check,  # not currently shown in the rendered table
        err_check,
        remnants,
        debug_value,
        head_check,
        date_check,
    ) = row

    cells = [
        f'<td><a class="check" href=https://{website}>{website}</a></td>',
        _bool_cell(https_check),
        _grade_cell(grade, grad_check, str(website)),
        _bool_cell(grad_check),
        _bool_cell(redirect_check),
        _cert_cell(cert_valid),
        _hsts_cell(hsts),
        _security_cell(security_txt, str(website)),
        _bool_cell(vers_check),
        _bool_cell(err_check),
        _bool_cell(remnants),
        _bool_cell(debug_value),
        _bool_cell(head_check),
        f'<td><a class="check" href={website}.html>{date_check}</a></td>',
    ]
    return f"<tr>{''.join(cells)}</tr>\n"


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
    <title>ScirtScan</title>
    <link rel="stylesheet" href="../styles.css">
</head>
<body>
  <script src="../sort.js"></script>
  <table border="1" class="dataframe mystyle" id="myTable">
  <thead>
    <tr style="text-align: right;">
{header_row}
    </tr>
  </thead>
  <tbody>
    {body}
  </tbody>
  </table>
  <br />
  This overview is generated with: <a href="https://github.com/beamzer/ScirtScan">https://github.com/beamzer/ScirtScan</a><br /><br />
  Clicks on table headers will result in sorting or reverse sorting on that column content <br />
  &#187; Click on the date in the detailed log column to see the detailed logs for that website<br />
  In the security.txt column clicks on green checkbox will show the contents of that URL <br />
  Click here for a: <a href="website_checks.xlsx">Excel file with the contents of this table</a><br />
  Click here for a: <a href="debug.log">debug.log</a> unless scirtscan was run with --no_debugfile<br />
</body>
</html>
"""


def render_header_row() -> str:
    return "\n".join(
        f'    <th onclick="{fn}({idx})">{label}<div class="explanation">click to sort</div></th>'
        for label, fn, idx in TABLE_HEADERS
    )


def main(argv: list[str] | None = None) -> None:
    today = date.today().strftime("%Y%m%d")
    parser = argparse.ArgumentParser(description="render website_checks as index.html")
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

    body = "".join(render_row(r) for r in rows)
    html = HTML_TEMPLATE.format(header_row=render_header_row(), body=body)

    out = Path(args.path) / "index.html"
    try:
        out.write_text(html, encoding="utf-8")
    except OSError as e:
        sys.exit(f"failed to write {out}: {e}")
    print(f"HTML table written to {out}")


if __name__ == "__main__":
    main()
