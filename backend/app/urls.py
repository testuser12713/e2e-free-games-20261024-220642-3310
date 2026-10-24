"""URL safety helpers for data delivered by shops and aggregators."""

from __future__ import annotations

from urllib.parse import urlsplit

_ALLOWED_SCHEMES = frozenset({"http", "https"})


def safe_http_url(value: str | None) -> str | None:
    """Return ``value`` (trimmed) only if it is an absolute http/https URL, else None.

    Anything else — ``javascript:``, ``data:``, protocol-relative ``//host``,
    relative paths, URLs with embedded whitespace or control characters — is
    rejected so it can never be stored or rendered as a link.
    """
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in candidate):
        return None
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return None
    if parts.scheme.lower() not in _ALLOWED_SCHEMES or not parts.hostname:
        return None
    return candidate
