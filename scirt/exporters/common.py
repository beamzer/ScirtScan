"""Shared helpers for the sql2csv / sql2excel / sql2html exporters."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def open_db(directory_path: str | Path, db_name: str = "websites.db") -> sqlite3.Connection:
    """Open the websites.db inside `directory_path` for reading."""
    path = Path(directory_path) / db_name
    return sqlite3.connect(path)


def db_columns(conn: sqlite3.Connection, table: str = "website_checks") -> list[str]:
    """Return the column names for `table` in declaration order via PRAGMA."""
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def fetch_rows(
    conn: sqlite3.Connection, columns: list[str], table: str = "website_checks"
) -> list[tuple[Any, ...]]:
    """Run SELECT col1, col2, ... FROM table using a column allowlist.

    Column names are validated against the actual table schema before being
    interpolated, eliminating SQL-injection risk from untrusted metadata.
    """
    valid = set(db_columns(conn, table))
    bad = [c for c in columns if c not in valid]
    if bad:
        raise ValueError(f"columns not in table {table}: {bad}")
    sql = f"SELECT {', '.join(columns)} FROM {table}"
    return conn.execute(sql).fetchall()
