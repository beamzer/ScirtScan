"""Structured logging setup for ScirtScan."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT_LOGGER_NAME = "scirtscan"


def configure(directory_path: str | Path, *, debug: bool, log_to_file: bool) -> logging.Logger:
    """Set up the scirtscan root logger. Replaces any prior configuration."""
    log = logging.getLogger(ROOT_LOGGER_NAME)
    log.setLevel(logging.DEBUG)
    log.handlers.clear()
    log.propagate = False

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    if log_to_file:
        path = Path(directory_path) / "debug.log"
        fh = RotatingFileHandler(
            str(path), maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        log.addHandler(fh)

    if debug:
        sh = logging.StreamHandler()
        sh.setLevel(logging.DEBUG)
        sh.setFormatter(fmt)
        log.addHandler(sh)

    if not log.handlers:
        log.addHandler(logging.NullHandler())

    return log
