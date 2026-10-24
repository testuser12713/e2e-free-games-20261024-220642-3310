"""Application settings, read from the environment.

Every value has a working default, so the API boots without any manual setup.
Settings are read lazily (on the first call of ``get_settings``) and validated
once at startup by the lifespan hook in ``app.main``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = str(BACKEND_DIR / "data" / "games.db")
DEFAULT_CORS_ORIGINS: tuple[str, ...] = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
)
DEFAULT_REFRESH_INTERVAL_HOURS = 6.0
DEFAULT_HTTP_TIMEOUT_SECONDS = 15.0
DEFAULT_HTTP_MAX_BYTES = 10 * 1024 * 1024


class ConfigError(ValueError):
    """Raised when an environment variable holds an unusable value."""


@dataclass(frozen=True)
class Settings:
    database_path: str = DEFAULT_DATABASE_PATH
    refresh_interval_hours: float = DEFAULT_REFRESH_INTERVAL_HOURS
    scrape_on_start: bool = True
    cors_origins: list[str] = field(default_factory=lambda: list(DEFAULT_CORS_ORIGINS))
    http_timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS
    http_max_bytes: int = DEFAULT_HTTP_MAX_BYTES


def _env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _positive_float(name: str, default: float) -> float:
    raw = _env(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc
    if not value > 0:
        raise ConfigError(f"{name} must be greater than 0, got {raw!r}")
    return value


def _positive_int(name: str, default: int) -> int:
    raw = _env(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise ConfigError(f"{name} must be greater than 0, got {raw!r}")
    return value


def _bool(name: str, default: bool) -> bool:
    raw = _env(name)
    if raw is None:
        return default
    lowered = raw.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{name} must be true or false, got {raw!r}")


def _normalize_origin(value: str) -> str | None:
    """Return ``scheme://host[:port]`` for an explicit http(s) origin, else None."""
    candidate = value.strip().rstrip("/")
    if not candidate or candidate == "*":
        return None
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    if parts.path or parts.query or parts.fragment or "$" in candidate:
        return None
    return f"{parts.scheme}://{parts.netloc}"


def parse_cors_origins(raw: str | None) -> list[str]:
    """Parse the comma-separated CORS_ORIGINS list into explicit origins.

    A wildcard or anything that is not an http(s) origin is dropped: the API
    only ever answers an explicit list of origins. When nothing usable is
    left, the local development defaults apply.
    """
    if raw is None:
        return list(DEFAULT_CORS_ORIGINS)
    origins: list[str] = []
    for entry in raw.split(","):
        if not entry.strip():
            continue
        origin = _normalize_origin(entry)
        if origin is None:
            logger.warning(
                "CORS_ORIGINS: ignoring entry %r (not an explicit http(s) origin)", entry
            )
            continue
        if origin not in origins:
            origins.append(origin)
    if not origins:
        logger.warning("CORS_ORIGINS holds no usable origin; using the local development defaults")
        return list(DEFAULT_CORS_ORIGINS)
    return origins


def load_settings() -> Settings:
    """Build a fresh Settings object from the current environment."""
    return Settings(
        database_path=_env("DATABASE_PATH") or DEFAULT_DATABASE_PATH,
        refresh_interval_hours=_positive_float(
            "REFRESH_INTERVAL_HOURS", DEFAULT_REFRESH_INTERVAL_HOURS
        ),
        scrape_on_start=_bool("SCRAPE_ON_START", True),
        cors_origins=parse_cors_origins(_env("CORS_ORIGINS")),
        http_timeout_seconds=_positive_float("HTTP_TIMEOUT_SECONDS", DEFAULT_HTTP_TIMEOUT_SECONDS),
        http_max_bytes=_positive_int("HTTP_MAX_BYTES", DEFAULT_HTTP_MAX_BYTES),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings (cached; ``get_settings.cache_clear()`` reloads)."""
    return load_settings()
