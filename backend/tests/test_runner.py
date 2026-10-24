"""Tests for the scraper run engine (fake adapters, no network)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app import db as app_db
from app.adapters import registry
from app.adapters.base import NormalizedDeal, SourceAdapter, SourceFetchError
from app.models import Deal, SourceState
from app.runner import run_all


def make_deal(source_deal_id: str, **overrides: Any) -> NormalizedDeal:
    base = NormalizedDeal(
        source_deal_id=source_deal_id,
        title=f"Game {source_deal_id}",
        store="Test Store",
        platform="pc",
        original_price=19.99,
        currency="EUR",
        url=f"https://store.example.com/{source_deal_id}",
        image_url=f"https://img.example.com/{source_deal_id}.jpg",
        starts_at=None,
        ends_at=datetime.now(UTC) + timedelta(days=3),
    )
    return replace(base, **overrides)


class FakeAdapter(SourceAdapter):
    def __init__(self, name: str, deals: list[NormalizedDeal] | None = None) -> None:
        self.name = name
        self.deals = deals or []
        self.error: Exception | None = None

    def fetch(self) -> list[NormalizedDeal]:
        if self.error is not None:
            raise self.error
        return list(self.deals)


def deals_of(session: Session, source: str) -> list[Deal]:
    session.expire_all()
    return list(session.scalars(select(Deal).where(Deal.source == source)).all())


def state_of(session: Session, name: str) -> SourceState | None:
    session.expire_all()
    return session.get(SourceState, name)


def test_repeated_run_creates_no_duplicates(db_session: Session) -> None:
    adapter = FakeAdapter("fake", [make_deal("a"), make_deal("b"), make_deal("a", platform="ps5")])
    run_all(app_db.SessionLocal, [adapter])
    first = {(d.source_deal_id, d.platform): d.first_seen_at for d in deals_of(db_session, "fake")}

    adapter.deals = [
        make_deal("a", title="Renamed"),
        make_deal("b"),
        make_deal("a", platform="ps5"),
    ]
    summary = run_all(app_db.SessionLocal, [adapter])

    rows = deals_of(db_session, "fake")
    assert len(rows) == 3
    assert summary.results[0].ok is True
    assert summary.results[0].deal_count == 3
    for row in rows:
        assert row.first_seen_at == first[(row.source_deal_id, row.platform)]
        assert row.last_seen_at >= row.first_seen_at
        assert row.expired is False
    assert {r.title for r in rows if r.source_deal_id == "a" and r.platform == "pc"} == {"Renamed"}


def test_vanished_deal_expires_and_reappearing_deal_unexpires(db_session: Session) -> None:
    adapter = FakeAdapter("fake", [make_deal("a"), make_deal("b")])
    run_all(app_db.SessionLocal, [adapter])

    adapter.deals = [make_deal("a")]
    run_all(app_db.SessionLocal, [adapter])
    rows = {d.source_deal_id: d for d in deals_of(db_session, "fake")}
    assert rows["a"].expired is False
    assert rows["b"].expired is True
    assert rows["b"].expired_at is not None
    state = state_of(db_session, "fake")
    assert state is not None and state.deal_count == 1

    adapter.deals = [make_deal("a"), make_deal("b")]
    run_all(app_db.SessionLocal, [adapter])
    rows = {d.source_deal_id: d for d in deals_of(db_session, "fake")}
    assert rows["b"].expired is False
    assert rows["b"].expired_at is None
    assert len(rows) == 2


def test_past_ends_at_expires(db_session: Session) -> None:
    past = datetime.now(UTC) - timedelta(hours=1)
    adapter = FakeAdapter("fake", [make_deal("old", ends_at=past), make_deal("new")])
    summary = run_all(app_db.SessionLocal, [adapter])

    rows = {d.source_deal_id: d for d in deals_of(db_session, "fake")}
    assert rows["old"].expired is True
    assert rows["new"].expired is False
    assert summary.results[0].deal_count == 1


def test_failing_adapter_keeps_stock_while_others_save(db_session: Session) -> None:
    flaky = FakeAdapter("flaky", [make_deal("x"), make_deal("y")])
    steady = FakeAdapter("steady", [make_deal("s1")])
    run_all(app_db.SessionLocal, [flaky, steady])

    flaky.error = SourceFetchError("HTTP 503 from upstream")
    steady.deals = [make_deal("s1"), make_deal("s2")]
    summary = run_all(app_db.SessionLocal, [flaky, steady])

    by_name = {r.name: r for r in summary.results}
    assert by_name["flaky"].ok is False
    assert "HTTP 503" in (by_name["flaky"].error or "")
    assert by_name["flaky"].deal_count == 2
    assert by_name["steady"].ok is True

    flaky_rows = deals_of(db_session, "flaky")
    assert len(flaky_rows) == 2
    assert all(not d.expired for d in flaky_rows)
    assert len(deals_of(db_session, "steady")) == 2

    state = state_of(db_session, "flaky")
    assert state is not None
    assert state.ok is False
    assert "HTTP 503" in (state.error or "")
    assert state.last_run_at is not None
    assert state.last_success_at is not None
    assert state.last_run_at > state.last_success_at


def test_unexpected_exception_is_isolated_and_error_truncated(db_session: Session) -> None:
    broken = FakeAdapter("broken")
    broken.error = ValueError("x" * 5000)
    ok = FakeAdapter("ok", [make_deal("o")])
    summary = run_all(app_db.SessionLocal, [broken, ok])

    assert [r.ok for r in summary.results] == [False, True]
    state = state_of(db_session, "broken")
    assert state is not None and state.ok is False
    assert state.error is not None and len(state.error) <= 500
    assert state.last_success_at is None
    assert len(deals_of(db_session, "ok")) == 1


def test_invalid_deals_are_dropped_and_unsafe_image_nulled(db_session: Session) -> None:
    adapter = FakeAdapter(
        "fake",
        [
            make_deal("zero", original_price=0),
            make_deal("negative", original_price=-5.0),
            make_deal("js", url="javascript:alert(1)"),
            make_deal("switch", platform="switch"),
            make_deal("badimg", image_url="javascript:alert(1)"),
            make_deal("good"),
        ],
    )
    summary = run_all(app_db.SessionLocal, [adapter])

    rows = {d.source_deal_id: d for d in deals_of(db_session, "fake")}
    assert set(rows) == {"badimg", "good"}
    assert rows["badimg"].image_url is None
    assert rows["good"].image_url == "https://img.example.com/good.jpg"
    assert all(d.original_price > 0 for d in rows.values())
    assert summary.results[0].deal_count == 2


class DummyAdapter(SourceAdapter):
    name = "dummy"

    def fetch(self) -> list[NormalizedDeal]:
        return [make_deal("dummy-1", store="Dummy Store")]


def test_registered_dummy_adapter_is_included(
    test_engine: Engine, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(registry, "ADAPTER_CLASSES", [*registry.ADAPTER_CLASSES, DummyAdapter])

    def offline_fetch(self: SourceAdapter) -> list[NormalizedDeal]:
        raise SourceFetchError("offline in tests")

    for cls in registry.ADAPTER_CLASSES[:-1]:
        # The real adapters would go to the network; make them fail fast instead.
        monkeypatch.setattr(cls, "fetch", offline_fetch)

    summary = run_all()

    names = [r.name for r in summary.results]
    assert "dummy" in names
    dummy = next(r for r in summary.results if r.name == "dummy")
    assert dummy.ok is True and dummy.deal_count == 1
    assert [d.store for d in deals_of(db_session, "dummy")] == ["Dummy Store"]
