"""Shared pytest fixtures: a temporary SQLite database, a TestClient, no network.

The environment is pointed at a throw-away database BEFORE any app module is
imported, so no test can ever touch backend/data/games.db, and the scheduler
never starts a scrape.
"""

from __future__ import annotations

import os
import socket
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session


def pytest_configure(config: pytest.Config) -> None:
    """Point the app at a throw-away database before any test module imports it."""
    session_dir = tempfile.mkdtemp(prefix="free-games-tests-")
    os.environ["DATABASE_PATH"] = str(Path(session_dir) / "session.db")
    os.environ["SCRAPE_ON_START"] = "false"
    from app.config import get_settings

    get_settings.cache_clear()


_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any test that tries to open a non-loopback network connection."""
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _check(sock: socket.socket, address: Any) -> None:
        if sock.family == getattr(socket, "AF_UNIX", None):
            return
        host = address[0] if isinstance(address, tuple) and address else address
        if host not in _LOOPBACK_HOSTS:
            raise RuntimeError(f"network access is not allowed in tests (tried {address!r})")

    def guarded_connect(sock: socket.socket, address: Any) -> None:
        _check(sock, address)
        real_connect(sock, address)

    def guarded_connect_ex(sock: socket.socket, address: Any) -> int:
        _check(sock, address)
        return real_connect_ex(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)


@pytest.fixture
def test_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """A fresh SQLite file per test; SessionLocal and init_db are bound to it."""
    from app import db as app_db

    engine = app_db.make_engine(str(tmp_path / "test.db"))
    previous_bind = app_db.SessionLocal.kw.get("bind")
    monkeypatch.setattr(app_db, "engine", engine)
    app_db.SessionLocal.configure(bind=engine)
    app_db.init_db()
    try:
        yield engine
    finally:
        app_db.SessionLocal.configure(bind=previous_bind)
        engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Iterator[Session]:
    """A session on the per-test temporary database (schema already created)."""
    from app import db as app_db

    session = app_db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def no_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the lifespan from starting background runs."""
    from app import scheduler

    monkeypatch.setattr(scheduler, "start_scheduler", lambda: None)
    monkeypatch.setattr(scheduler, "stop_scheduler", lambda: None)


@pytest.fixture
def test_app(test_engine: Engine, no_scheduler: None) -> FastAPI:
    """A fresh application instance bound to the temporary database."""
    from app.main import create_app

    return create_app()


@pytest.fixture
def client(test_app: FastAPI) -> Iterator[TestClient]:
    """TestClient on the temporary database; the lifespan runs, the scheduler does not."""
    with TestClient(test_app) as test_client:
        yield test_client
