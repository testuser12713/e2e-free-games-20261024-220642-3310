"""Run control: scheduler lock, POST /api/refresh, CLI refresh and source status."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import cli, scheduler
from app.config import Settings
from app.models import SourceState
from app.routers import refresh as refresh_router
from app.runner import RunSummary, SourceResult


def _wait_until(predicate: Callable[[], bool], timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


class FakeRun:
    """Stands in for run_all: counts calls and blocks until released."""

    def __init__(self, block: bool = True) -> None:
        self.calls = 0
        self.started = threading.Event()
        self.release = threading.Event()
        if not block:
            self.release.set()

    def __call__(self, *args: object, **kwargs: object) -> RunSummary:
        self.calls += 1
        self.started.set()
        self.release.wait(timeout=10)
        return RunSummary(results=[SourceResult(name="fake", ok=True, error=None, deal_count=1)])


@pytest.fixture
def fake_run(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeRun]:
    fake = FakeRun()
    monkeypatch.setattr(scheduler, "run_all", fake)
    yield fake
    fake.release.set()
    assert _wait_until(lambda: not scheduler.is_running())


@pytest.fixture(autouse=True)
def _fresh_rate_limiter() -> Iterator[None]:
    refresh_router.rate_limiter.reset()
    yield
    refresh_router.rate_limiter.reset()


def test_refresh_starts_then_conflicts_while_running(client: TestClient, fake_run: FakeRun) -> None:
    first = client.post("/api/refresh")
    assert first.status_code == 202
    assert first.json() == {"status": "started"}
    assert fake_run.started.wait(timeout=5)
    assert scheduler.is_running()

    second = client.post("/api/refresh")
    assert second.status_code == 409
    assert set(second.json()["error"]) == {"code", "message", "details"}

    fake_run.release.set()
    assert _wait_until(lambda: not scheduler.is_running())
    assert fake_run.calls == 1

    # Once the run is over a new one may start again.
    third = client.post("/api/refresh")
    assert third.status_code == 202
    assert _wait_until(lambda: fake_run.calls == 2)


def test_refresh_is_rate_limited_per_client(client: TestClient, fake_run: FakeRun) -> None:
    limit = refresh_router.rate_limiter.max_calls
    codes = [client.post("/api/refresh").status_code for _ in range(limit)]
    assert codes[0] == 202
    assert all(code == 409 for code in codes[1:])

    limited = client.post("/api/refresh")
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert fake_run.calls == 1


def test_rate_limiter_window_expires_and_clients_are_separate() -> None:
    now = [0.0]
    limiter = refresh_router.RateLimiter(max_calls=2, window_seconds=10, clock=lambda: now[0])
    assert limiter.allow("a") and limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")
    now[0] = 11.0
    assert limiter.allow("a")


def test_rate_limiter_does_not_keep_raw_client_address() -> None:
    limiter = refresh_router.RateLimiter()
    limiter.allow("203.0.113.7")
    assert all("203.0.113.7" not in key for key in limiter._calls)


def test_try_start_run_allows_only_one_active_run(fake_run: FakeRun) -> None:
    assert scheduler.try_start_run() is True
    assert fake_run.started.wait(timeout=5)
    assert scheduler.try_start_run() is False
    assert scheduler.is_running()
    fake_run.release.set()
    assert _wait_until(lambda: not scheduler.is_running())
    assert fake_run.calls == 1


def test_failing_run_releases_the_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: object, **kwargs: object) -> RunSummary:
        raise RuntimeError("boom")

    monkeypatch.setattr(scheduler, "run_all", broken)
    assert scheduler.try_start_run() is True
    assert _wait_until(lambda: not scheduler.is_running())


def _use_settings(
    monkeypatch: pytest.MonkeyPatch, scrape_on_start: bool, refresh_interval_hours: float
) -> None:
    settings = Settings(
        scrape_on_start=scrape_on_start, refresh_interval_hours=refresh_interval_hours
    )
    monkeypatch.setattr(scheduler, "get_settings", lambda: settings)


def test_startup_run_when_enabled(monkeypatch: pytest.MonkeyPatch, fake_run: FakeRun) -> None:
    fake_run.release.set()
    _use_settings(monkeypatch, scrape_on_start=True, refresh_interval_hours=6.0)
    scheduler.start_scheduler()
    try:
        assert fake_run.started.wait(timeout=5)
        assert fake_run.calls == 1
    finally:
        scheduler.stop_scheduler()


def test_no_startup_run_when_disabled(monkeypatch: pytest.MonkeyPatch, fake_run: FakeRun) -> None:
    fake_run.release.set()
    _use_settings(monkeypatch, scrape_on_start=False, refresh_interval_hours=6.0)
    scheduler.start_scheduler()
    try:
        assert not fake_run.started.wait(timeout=0.3)
        assert fake_run.calls == 0
    finally:
        scheduler.stop_scheduler()


def test_interval_runs_repeat(monkeypatch: pytest.MonkeyPatch, fake_run: FakeRun) -> None:
    fake_run.release.set()
    _use_settings(monkeypatch, scrape_on_start=False, refresh_interval_hours=0.05 / 3600)
    scheduler.start_scheduler()
    try:
        assert _wait_until(lambda: fake_run.calls >= 2)
    finally:
        scheduler.stop_scheduler()


def test_cli_refresh_runs_and_prints(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], test_engine: object
) -> None:
    calls: list[int] = []

    def fake_run_all(*args: object, **kwargs: object) -> RunSummary:
        calls.append(1)
        return RunSummary(
            results=[
                SourceResult(name="epic", ok=True, error=None, deal_count=3),
                SourceResult(name="steam", ok=False, error="timeout", deal_count=0),
            ]
        )

    monkeypatch.setattr(cli, "run_all", fake_run_all)
    assert cli.main(["refresh"]) == 0
    assert calls == [1]
    out = capsys.readouterr().out
    assert "epic: ok, 3 deals" in out
    assert "steam" in out and "timeout" in out


def test_sources_status_lists_last_run_per_source(client: TestClient, db_session: Session) -> None:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    db_session.add_all(
        [
            SourceState(
                name="steam",
                last_run_at=now,
                ok=False,
                error="HTTP 503",
                last_success_at=now - timedelta(hours=6),
                deal_count=0,
            ),
            SourceState(
                name="epic",
                last_run_at=now,
                ok=True,
                error=None,
                last_success_at=now,
                deal_count=2,
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/sources/status")
    assert response.status_code == 200
    body = response.json()
    assert body["running"] is False
    assert [item["name"] for item in body["items"]] == ["epic", "steam"]
    epic, steam = body["items"]
    assert epic["ok"] is True and epic["deal_count"] == 2
    assert steam["ok"] is False and steam["error"] == "HTTP 503"
    assert datetime.fromisoformat(steam["last_run_at"]) == now
    assert datetime.fromisoformat(body["last_updated_at"]) == now


def test_sources_status_empty(client: TestClient) -> None:
    body = client.get("/api/sources/status").json()
    assert body == {"items": [], "last_updated_at": None, "running": False}
