"""EpicAdapter against a hand-recorded freeGamesPromotions payload (no network)."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.adapters.base import NormalizedDeal, SourceFetchError
from app.adapters.epic import FREE_GAMES_URL, EpicAdapter

FIXTURE = Path(__file__).parent / "fixtures" / "epic_free_games.json"
NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


def _payload() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _adapter(payload: Any, calls: list[tuple[str, Any]] | None = None) -> EpicAdapter:
    def fake_fetch_json(url: str, *, params: Any = None, headers: Any = None) -> Any:
        if calls is not None:
            calls.append((url, params))
        return copy.deepcopy(payload)

    def fake_fetch_text(url: str, *, params: Any = None, headers: Any = None) -> str:
        raise AssertionError("EpicAdapter must not use fetch_text")

    return EpicAdapter(fetch_json=fake_fetch_json, fetch_text=fake_fetch_text, now=lambda: NOW)


def _by_title(deals: list[NormalizedDeal]) -> dict[str, NormalizedDeal]:
    return {deal.title: deal for deal in deals}


def test_name_is_epic() -> None:
    assert EpicAdapter.name == "epic"


def test_fetches_the_free_games_endpoint() -> None:
    calls: list[tuple[str, Any]] = []
    _adapter(_payload(), calls).fetch()
    assert len(calls) == 1
    assert calls[0][0] == FREE_GAMES_URL


def test_parses_active_free_offer_into_normalized_pc_deal() -> None:
    deals = _by_title(_adapter(_payload()).fetch())
    deal = deals["Wildlands Courier"]
    assert deal == NormalizedDeal(
        source_deal_id="4f1c2a9e7b8d4e3fa6b1c0d9e8f7a6b5",
        title="Wildlands Courier",
        store="Epic Games Store",
        platform="pc",
        original_price=24.99,
        currency="EUR",
        url="https://store.epicgames.com/de/p/wildlands-courier",
        image_url="https://cdn1.epicgames.com/offer/c3d4e5f6a7b8/wildlands-wide.jpg",
        starts_at=datetime(2026, 10, 22, 15, 0, tzinfo=UTC),
        ends_at=datetime(2026, 10, 29, 15, 0, tzinfo=UTC),
    )


def test_legacy_slug_unsafe_image_and_lowercase_currency() -> None:
    deal = _by_title(_adapter(_payload()).fetch())["Harbor Lights"]
    assert deal.url == "https://store.epicgames.com/de/p/harbor-lights"
    # The javascript: wide image is rejected, the safe tall image is used instead.
    assert deal.image_url == "https://cdn1.epicgames.com/offer/f1e2d3c4b5a6/harbor-tall.png"
    assert deal.currency == "EUR"
    assert deal.original_price == pytest.approx(19.99, abs=1e-2)


def test_only_current_100_percent_offers_with_price_survive() -> None:
    deals = _adapter(_payload()).fetch()
    titles = {deal.title for deal in deals}
    assert titles == {"Wildlands Courier", "Harbor Lights"}
    # upcoming promotion, free-to-play (price 0), malformed, 50 % off, ended promotion
    for dropped in (
        "Starfall Tactics",
        "Arena Clash Online",
        "Mystery Game",
        "Canyon Rally Deluxe",
        "Frostbound Saga",
    ):
        assert dropped not in titles
    for deal in deals:
        assert deal.platform == "pc"
        assert deal.store == "Epic Games Store"
        assert deal.original_price > 0


def test_upcoming_promo_becomes_a_deal_once_it_is_active() -> None:
    payload = _payload()
    starfall = payload["data"]["Catalog"]["searchStore"]["elements"][2]
    promotions = starfall["promotions"]
    promotions["promotionalOffers"] = promotions.pop("upcomingPromotionalOffers")
    promotions["upcomingPromotionalOffers"] = []
    starfall["price"]["totalPrice"]["discountPrice"] = 0
    adapter = EpicAdapter(
        fetch_json=lambda url, **kwargs: payload,
        now=lambda: datetime(2026, 10, 30, 12, 0, tzinfo=UTC),
    )
    titles = {deal.title for deal in adapter.fetch()}
    assert "Starfall Tactics" in titles
    assert "Wildlands Courier" not in titles  # its window has ended by then


def test_unsafe_product_slug_drops_the_deal() -> None:
    payload = _payload()
    element = payload["data"]["Catalog"]["searchStore"]["elements"][0]
    element["catalogNs"]["mappings"][0]["pageSlug"] = "bad slug with spaces"
    titles = {deal.title for deal in _adapter(payload).fetch()}
    assert "Wildlands Courier" not in titles


def test_duplicate_offer_ids_are_returned_once() -> None:
    payload = _payload()
    elements = payload["data"]["Catalog"]["searchStore"]["elements"]
    elements.append(copy.deepcopy(elements[0]))
    deals = _adapter(payload).fetch()
    assert [d.title for d in deals].count("Wildlands Courier") == 1


def test_empty_feed_returns_no_deals() -> None:
    payload = {"data": {"Catalog": {"searchStore": {"elements": []}}}}
    assert _adapter(payload).fetch() == []


@pytest.mark.parametrize(
    "payload",
    [None, [], {"data": None}, {"data": {"Catalog": {"searchStore": {"elements": "x"}}}}],
)
def test_wrong_payload_shape_raises_source_fetch_error(payload: Any) -> None:
    with pytest.raises(SourceFetchError):
        _adapter(payload).fetch()


def test_fetch_error_propagates() -> None:
    def failing_fetch_json(url: str, *, params: Any = None, headers: Any = None) -> Any:
        raise SourceFetchError("timeout after 10s fetching epic")

    adapter = EpicAdapter(fetch_json=failing_fetch_json, now=lambda: NOW)
    with pytest.raises(SourceFetchError, match="timeout"):
        adapter.fetch()


def test_default_constructor_matches_registry_contract() -> None:
    from app.adapters.registry import get_adapters

    assert any(isinstance(adapter, EpicAdapter) for adapter in get_adapters())
