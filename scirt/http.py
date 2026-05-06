"""Shared HTTP client and helpers used by all check modules."""
from __future__ import annotations

import logging
from typing import Optional

import requests

DEFAULT_TIMEOUT = 5.0

log = logging.getLogger("scirtscan.http")


class HttpClient:
    """Thin wrapper around requests.Session enforcing timeouts and a User-Agent."""

    def __init__(self, user_agent: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self.timeout = timeout

    def get(
        self,
        url: str,
        *,
        allow_redirects: bool = True,
        timeout: Optional[float] = None,
        headers: Optional[dict] = None,
    ) -> requests.Response:
        return self.session.get(
            url,
            allow_redirects=allow_redirects,
            timeout=timeout if timeout is not None else self.timeout,
            headers=headers,
        )

    def head(
        self,
        url: str,
        *,
        allow_redirects: bool = True,
        timeout: Optional[float] = None,
        headers: Optional[dict] = None,
    ) -> requests.Response:
        return self.session.head(
            url,
            allow_redirects=allow_redirects,
            timeout=timeout if timeout is not None else self.timeout,
            headers=headers,
        )


def safe_content_type(response: requests.Response) -> str:
    """Return Content-Type header or empty string if missing."""
    return response.headers.get("Content-Type", "")
