"""Tests for the demo seed (app.seed)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import seed
from app.models import Deal, SourceState
from app.urls import safe_http_url

FIVE_SOURCES = {"epic", "steam", "gog", "playstation", "gamerpower"}


def _counts(session: Session) -> tuple[int, int]:
    deals = session.execute(select(func.count()).select_from(Deal)).scalar_one()
    states = session.execute(select(func.count()).select_from(SourceState)).scalar_one()
    return deals, states


def test_seeding_twice_is_idempotent(db_session: Session) -> None:
    assert _counts(db_session) == (0, 0)
    first = seed.seed_session(db_session)
    after_first = _counts(db_session)
    second = seed.seed_session(db_session)
    after_second = _counts(db_session)

    assert after_first == after_second
    assert after_first[0] >= 25
    assert after_first[1] == 5
    assert first.deals_inserted == after_first[0]
    assert second.deals_inserted == 0
    assert second.deals_updated == after_first[0]


def test_seeded_deals_obey_the_deal_rules(db_session: Session) -> None:
    seed.seed_session(db_session)
    deals = db_session.execute(select(Deal)).scalars().all()

    for deal in deals:
        assert deal.original_price > 0
        assert deal.platform in {"pc", "ps5"}
        assert deal.currency in {"EUR", "USD"}
        assert deal.title and deal.store
        assert safe_http_url(deal.url) == deal.url
        assert deal.url.startswith("https://")
        if deal.image_url is not None:
            assert deal.image_url.startswith("https://")

    assert {d.source for d in deals} == FIVE_SOURCES
    assert {d.platform for d in deals} == {"pc", "ps5"}
    assert any(d.image_url for d in deals)
    assert any(d.image_url is None for d in deals)
    now = datetime.now(UTC)
    active = [d for d in deals if not d.expired]
    assert any(d.ends_at is not None and d.ends_at > now for d in active)
    assert any(d.ends_at is None for d in active)
    assert 1 <= sum(d.expired for d in deals) <= 2


def test_source_states_cover_every_source_with_one_error(db_session: Session) -> None:
    seed.seed_session(db_session)
    states = db_session.execute(select(SourceState)).scalars().all()

    assert {s.name for s in states} == FIVE_SOURCES
    failing = [s for s in states if s.ok is False]
    assert len(failing) == 1 and failing[0].error
    assert all(s.error is None for s in states if s.ok)
    assert all(s.deal_count > 0 for s in states)


def test_invalid_entries_are_skipped(db_session: Session) -> None:
    base = {
        "source": "steam",
        "title": "Example",
        "store": "Steam",
        "platform": "pc",
        "original_price": 9.99,
        "currency": "EUR",
        "url": "https://store.steampowered.com/app/1/",
    }
    data = {
        "deals": [
            {**base, "source_deal_id": "ok", "image_url": "javascript:alert(1)"},
            {**base, "source_deal_id": "free", "original_price": 0},
            {**base, "source_deal_id": "switch", "platform": "switch"},
            {**base, "source_deal_id": "bad-url", "url": "javascript:alert(1)"},
        ],
        "sources": [],
    }
    result = seed.seed_session(db_session, data)

    assert (result.deals_inserted, result.deals_skipped) == (1, 3)
    deal = db_session.execute(select(Deal)).scalar_one()
    assert deal.source_deal_id == "ok" and deal.image_url is None


def test_main_seeds_the_configured_database(db_session: Session) -> None:
    assert seed.main() == 0
    assert seed.main() == 0
    deals, states = _counts(db_session)
    assert deals >= 25 and states == 5


def test_app_start_does_not_seed(client: object, db_session: Session) -> None:
    assert _counts(db_session) == (0, 0)
