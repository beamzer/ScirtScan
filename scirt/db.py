"""SQLite-backed storage for scan results."""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
from typing import Any

log = logging.getLogger("scirtscan.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS website_checks
(
    websites TEXT PRIMARY KEY,
    https_reachable INT,
    grade TEXT,
    grade_check INT,
    redirect_check INT,
    cert_validity INT,
    hsts INT,
    security_txt INT,
    version_check INT,
    robots_check INT,
    error_check INT,
    remnants INT,
    debug INT,
    headers_check INT,
    check_date TEXT
)
"""

META_SCHEMA = "CREATE TABLE IF NOT EXISTS meta (structure TEXT, version TEXT)"

TABLE_STRUCTURE = """
(   websites TEXT, https_reachable INT, grade TEXT, grade_check INT, redirect_check INT, cert_validity INT, hsts INT,
    security_txt INT, version_check INT, error_check INT, remnants INT, debug INT, headers_check INT,
    check_date TEXT )
"""


class Database:
    def __init__(self, directory_path: str, version: str, db_filename: str = "websites.db") -> None:
        self.path = os.path.join(directory_path, db_filename)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.lock = threading.Lock()
        self._setup(version)

    def _setup(self, version: str) -> None:
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(SCHEMA)
            cur.execute(META_SCHEMA)
            try:
                cur.execute("INSERT INTO meta (structure) VALUES (?)", (TABLE_STRUCTURE,))
                cur.execute("INSERT INTO meta (version) VALUES (?)", (version,))
            except sqlite3.Error as e:
                log.error("failed to insert meta rows: %s", e)
            self.conn.commit()
            log.debug("connected to database %s", self.path)

    def upsert_website(self, website: str, check_date: str) -> None:
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO website_checks (websites, check_date) VALUES (?, ?) "
                "ON CONFLICT(websites) DO UPDATE SET check_date = excluded.check_date",
                (website, check_date),
            )
            self.conn.commit()

    def update(self, website: str, columns: dict[str, Any]) -> None:
        if not columns:
            return
        set_clause = ", ".join(f"{c} = ?" for c in columns)
        with self.lock:
            cur = self.conn.cursor()
            try:
                cur.execute(
                    f"UPDATE website_checks SET {set_clause} WHERE websites = ?",
                    list(columns.values()) + [website],
                )
                self.conn.commit()
                log.debug("updated %s with %s", website, columns)
            except sqlite3.Error as e:
                log.error("failed to update %s: %s", website, e)

    def close(self) -> None:
        with self.lock:
            self.conn.commit()
            self.conn.close()
