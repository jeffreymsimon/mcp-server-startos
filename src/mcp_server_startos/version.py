"""Lazy-cached start-cli version detection."""

from .cli import run_cli

_cached_version: str | None = None


async def get_cli_version() -> str:
    global _cached_version
    if _cached_version is None:
        try:
            raw = await run_cli("git-info")
            _cached_version = raw.strip()
        except Exception:
            _cached_version = "unknown"
    return _cached_version
