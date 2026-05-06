"""Runtime configuration for ScirtScan."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]


DEFAULT_USER_AGENT_BASE = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
)


@dataclass
class Config:
    cert_name: str = "Your CERT here"
    user_agent_base: str = DEFAULT_USER_AGENT_BASE
    default_timeout: float = 5.0
    sslscore_max_retries: int = 10
    testssl_path: str = "/usr/local/bin/testssl.sh"
    parallel_websites: int = 1

    def user_agent(self, anon: bool = False) -> str:
        if anon:
            return self.user_agent_base
        return f"{self.user_agent_base} ({self.cert_name})"


def load_config(path: str | Path = "scirtscan.toml") -> Config:
    p = Path(path)
    if not p.exists():
        return Config()
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    scan = data.get("scan", {})
    paths = data.get("paths", {})
    return Config(
        cert_name=scan.get("cert_name", Config.cert_name),
        user_agent_base=scan.get("user_agent_base", DEFAULT_USER_AGENT_BASE),
        default_timeout=scan.get("default_timeout", 5.0),
        sslscore_max_retries=scan.get("sslscore_max_retries", 10),
        testssl_path=paths.get("testssl", "/usr/local/bin/testssl.sh"),
        parallel_websites=scan.get("parallel_websites", 1),
    )
