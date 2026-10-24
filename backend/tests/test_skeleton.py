"""What the backend skeleton itself delivers: wiring, health, error shape, registry."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

CONTRACT_ROUTES = {
    ("GET", "/api/health"),
    ("GET", "/api/deals"),
    ("GET", "/api/stores"),
    ("GET", "/api/sources/status"),
    ("POST", "/api/refresh"),
}


def test_app_imports() -> None:
    from app.main import app, create_app

    assert isinstance(app, FastAPI)
    assert isinstance(create_app(), FastAPI)


def test_health_answers_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_path_returns_error_body(client: TestClient) -> None:
    response = client.get("/api/this-path-does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert isinstance(body["error"]["code"], str)
    assert isinstance(body["error"]["message"], str)


def test_every_adapter_class_is_a_registered_source_adapter() -> None:
    from app.adapters.base import SourceAdapter
    from app.adapters.epic import EpicAdapter
    from app.adapters.gamerpower import GamerPowerAdapter
    from app.adapters.gog import GogAdapter
    from app.adapters.playstation import PlayStationAdapter
    from app.adapters.registry import ADAPTER_CLASSES, get_adapters
    from app.adapters.steam import SteamAdapter

    expected = {
        EpicAdapter: "epic",
        SteamAdapter: "steam",
        GogAdapter: "gog",
        PlayStationAdapter: "playstation",
        GamerPowerAdapter: "gamerpower",
    }
    assert set(ADAPTER_CLASSES) == set(expected)
    for adapter_class, name in expected.items():
        assert issubclass(adapter_class, SourceAdapter)
        assert adapter_class.name == name
    assert all(isinstance(adapter, SourceAdapter) for adapter in get_adapters())


def test_contract_routes_are_mounted_and_nothing_else() -> None:
    from app.main import create_app

    openapi_paths = create_app().openapi()["paths"]
    mounted = {
        (method.upper(), path)
        for path, operations in openapi_paths.items()
        for method in operations
    }
    assert mounted == CONTRACT_ROUTES


def test_trailing_slash_spelling_is_not_served(client: TestClient) -> None:
    response = client.get("/api/health/", follow_redirects=False)
    assert response.status_code == 404
    assert "error" in response.json()
