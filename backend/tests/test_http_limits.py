"""AC-15/AC-18: outgoing fetches are bounded and only http(s) URLs pass; CORS is explicit."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app import http as app_http
from app.adapters.base import SourceFetchError
from app.config import Settings, parse_cors_origins
from app.urls import safe_http_url

_REAL_CLIENT = httpx.Client


def _use_transport(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Route app.http through an in-memory transport and record the client options."""
    created: list[dict[str, Any]] = []

    def client_factory(**kwargs: Any) -> httpx.Client:
        created.append(kwargs)
        return _REAL_CLIENT(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(app_http.httpx, "Client", client_factory)
    monkeypatch.setattr(app_http, "get_settings", lambda: settings or Settings())
    return created


def test_fetch_json_parses_and_applies_the_configured_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = _use_transport(
        monkeypatch,
        lambda request: httpx.Response(200, json={"ok": True}),
        Settings(http_timeout_seconds=3.5),
    )
    assert app_http.fetch_json("https://example.test/api") == {"ok": True}
    assert created[0]["timeout"] == 3.5


def test_oversized_response_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_transport(
        monkeypatch,
        lambda request: httpx.Response(200, content=b"x" * 2048),
        Settings(http_max_bytes=1024),
    )
    with pytest.raises(SourceFetchError):
        app_http.fetch_text("https://example.test/big")


def test_timeout_becomes_source_fetch_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    _use_transport(monkeypatch, handler)
    with pytest.raises(SourceFetchError):
        app_http.fetch_text("https://example.test/slow")


def test_http_error_status_and_bad_json_become_source_fetch_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_transport(monkeypatch, lambda request: httpx.Response(503, text="down"))
    with pytest.raises(SourceFetchError):
        app_http.fetch_text("https://example.test/down")

    _use_transport(monkeypatch, lambda request: httpx.Response(200, text="<html>"))
    with pytest.raises(SourceFetchError):
        app_http.fetch_json("https://example.test/not-json")


@pytest.mark.parametrize(
    "value",
    ["https://store.example/game", "http://store.example/img.png", "  https://a.example/x  "],
)
def test_safe_http_url_accepts_http_and_https(value: str) -> None:
    assert safe_http_url(value) == value.strip()


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "javascript:alert(1)",
        "JAVASCRIPT:alert(1)",
        "data:text/html,hi",
        "ftp://store.example/x",
        "//store.example/x",
        "/relative/path",
        "https://",
        "https://store.example/a b",
    ],
)
def test_safe_http_url_rejects_everything_else(value: str | None) -> None:
    assert safe_http_url(value) is None


def test_cors_origins_are_explicit_and_never_a_wildcard() -> None:
    assert parse_cors_origins("https://a.example, http://localhost:5173/") == [
        "https://a.example",
        "http://localhost:5173",
    ]
    assert "*" not in parse_cors_origins("*")
    assert parse_cors_origins("*") == parse_cors_origins(None)
    assert parse_cors_origins("${service:web.origin}") == parse_cors_origins(None)
