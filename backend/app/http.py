"""Outgoing HTTP for the scrapers, with a timeout and a response-size cap.

Both limits come from Settings (``HTTP_TIMEOUT_SECONDS``, ``HTTP_MAX_BYTES``).
Every failure — timeout, connection error, non-2xx status, oversized body,
undecodable payload — is raised as ``SourceFetchError``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import httpx

from app.adapters.base import SourceFetchError
from app.config import get_settings

USER_AGENT = "GratisSpieleScraper/1.0 (+self-hosted free games list)"
MAX_REDIRECTS = 5


def _fetch_bytes(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> tuple[bytes, str | None]:
    settings = get_settings()
    max_bytes = settings.http_max_bytes
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    try:
        with (
            httpx.Client(
                timeout=settings.http_timeout_seconds,
                follow_redirects=True,
                max_redirects=MAX_REDIRECTS,
            ) as client,
            client.stream("GET", url, params=params, headers=request_headers) as response,
        ):
            if response.status_code < 200 or response.status_code >= 300:
                raise SourceFetchError(f"HTTP {response.status_code} from {response.url.host}")
            declared = response.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > max_bytes:
                raise SourceFetchError(
                    f"response of {declared} bytes exceeds the limit of {max_bytes} bytes"
                )
            chunks: list[bytes] = []
            received = 0
            for chunk in response.iter_bytes():
                received += len(chunk)
                if received > max_bytes:
                    raise SourceFetchError(f"response exceeds the limit of {max_bytes} bytes")
                chunks.append(chunk)
            return b"".join(chunks), response.encoding
    except SourceFetchError:
        raise
    except httpx.TimeoutException as exc:
        raise SourceFetchError(
            f"timeout after {settings.http_timeout_seconds:g}s fetching {url}"
        ) from exc
    except httpx.HTTPError as exc:
        raise SourceFetchError(f"{type(exc).__name__} fetching {url}: {exc}") from exc


def fetch_text(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> str:
    """GET ``url`` and return the decoded body text."""
    body, encoding = _fetch_bytes(url, params=params, headers=headers)
    try:
        return body.decode(encoding or "utf-8")
    except (LookupError, UnicodeDecodeError) as exc:
        raise SourceFetchError(f"undecodable response from {url}") from exc


def fetch_json(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> Any:
    """GET ``url`` and return the parsed JSON body."""
    merged = {"Accept": "application/json"}
    if headers:
        merged.update(headers)
    body, _ = _fetch_bytes(url, params=params, headers=merged)
    try:
        return json.loads(body)
    except (UnicodeDecodeError, ValueError) as exc:
        raise SourceFetchError(f"invalid JSON from {url}") from exc
