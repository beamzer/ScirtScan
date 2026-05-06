"""Check protocol, context, and result types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import IO, Any, Protocol, runtime_checkable

from .http import HttpClient


@dataclass
class CheckContext:
    """Everything a check needs to do its work."""

    website: str
    url: str
    http: HttpClient
    directory_path: str
    outfile: IO[str]


@dataclass
class CheckResult:
    """What a check produces. Columns are merged into the website_checks DB row.

    `gate_passed` is consulted only for the DNS and HTTPS-reachability gate
    checks; for every other check it is ignored.
    """

    columns: dict[str, Any] = field(default_factory=dict)
    extra_files: dict[str, str] = field(default_factory=dict)
    gate_passed: bool = True


@runtime_checkable
class Check(Protocol):
    """A single security/health check for one website."""

    name: str

    def run(self, ctx: CheckContext) -> CheckResult:
        ...
