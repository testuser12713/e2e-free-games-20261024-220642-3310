"""Tests for the Steam adapter against hand-recorded fixtures (no network)."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.adapters.base import SourceAdapter, SourceFetchError
from app.adapters.steam import APPDETAILS_URL, FEATURED_URL, SteamAdapter

FIXTURE = Path(__file__).parent / "fixtures" / "steam_specials.json"


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class FakeSteam:
    """Replays the fixture for the two Steam endpoints and records every call."""

    def __init__(self, fixture: dict[str, Any]) -> None:
        self.fixture = fixture
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, url: str, *, params: dict[str, Any] | None = None, **_: Any) -> Any:
        params = dict(params or {})
        self.calls.append((url, params))
        if url == FEATURED_URL:
            return self.fixture["featuredcategories"]
        if url == APPDETAILS_URL:
            app_id = str(params["appids"])
            return {app_id: self.fixture["appdetails"].get(app_id, {"success": False})}
        raise AssertionError(f"unexpected URL {url}")


def _fetch(fixture: dict[str, Any] | None = None) -> tuple[list[Any], FakeSteam]:
    fake = FakeSteam(fixture if fixture is not None else _load_fixture())
    return SteamAdapter(fetch_json=fake).fetch(), fake


def test_adapter_implements_interface() -> None:
    adapter = SteamAdapter(fetch_json=FakeSteam(_load_fixture()))
    assert isinstance(adapter, SourceAdapter)
    assert adapter.name == "steam"


def test_returns_only_full_discount_paid_games() -> None:
    deals, _ = _fetch()
    assert [d.source_deal_id for d in deals] == ["1001", "1002"]


def test_parses_deal_fields() -> None:
    deals, _ = _fetch()
    deal = deals[0]
    assert deal.title == "Lantern Keeper"
    assert deal.store == "Steam"
    assert deal.platform == "pc"
    assert deal.original_price == pytest.approx(19.99, abs=1e-2)
    assert deal.currency == "EUR"
    assert deal.url == "https://store.steampowered.com/app/1001/"
    assert deal.image_url == (
        "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1001/header.jpg"
    )
    assert deal.starts_at is None
    assert deal.ends_at == datetime.fromtimestamp(1798761600, tz=UTC)
    assert deals[1].original_price == pytest.approx(24.99, abs=1e-2)


def test_every_deal_is_pc_with_positive_price() -> None:
    deals, _ = _fetch()
    assert deals
    assert all(d.platform == "pc" for d in deals)
    assert all(d.original_price > 0 for d in deals)


def test_drops_partial_discount_free_to_play_demo_dlc_and_software() -> None:
    deals, fake = _fetch()
    ids = {d.source_deal_id for d in deals}
    # 1003 is a 90 % deal, 1004 free-to-play, 1005 a demo, 1006 a DLC,
    # 1007 software, 1008 not available in the region.
    assert ids.isdisjoint({"1003", "1004", "1005", "1006", "1007", "1008"})
    looked_up = [p["appids"] for url, p in fake.calls if url == APPDETAILS_URL]
    # A 90 % special never costs an appdetails request; duplicates are looked up once.
    assert "1003" not in looked_up
    assert looked_up.count("1001") == 1


def test_unsafe_image_url_becomes_none() -> None:
    fixture = _load_fixture()
    fixture["appdetails"]["1001"]["data"]["header_image"] = "javascript:alert(1)"
    fixture["featuredcategories"]["specials"]["items"][0]["header_image"] = "data:text/html,x"
    deals, _ = _fetch(fixture)
    assert deals[0].source_deal_id == "1001"
    assert deals[0].image_url is None


def test_price_detail_overrides_special_listing() -> None:
    fixture = copy.deepcopy(_load_fixture())
    # Listed as 100 % in specials but the detail says the promotion ended.
    fixture["appdetails"]["1002"]["data"]["price_overview"]["discount_percent"] = 0
    deals, _ = _fetch(fixture)
    assert [d.source_deal_id for d in deals] == ["1001"]


def test_empty_specials_returns_no_deals() -> None:
    deals, _ = _fetch({"featuredcategories": {"specials": {"items": []}}, "appdetails": {}})
    assert deals == []


def test_fetch_error_propagates() -> None:
    def failing(url: str, **_: Any) -> Any:
        raise SourceFetchError("timeout after 10s fetching Steam")

    with pytest.raises(SourceFetchError):
        SteamAdapter(fetch_json=failing).fetch()


def test_appdetails_error_propagates() -> None:
    fixture = _load_fixture()

    def flaky(url: str, *, params: dict[str, Any] | None = None, **_: Any) -> Any:
        if url == APPDETAILS_URL:
            raise SourceFetchError("HTTP 503 from store.steampowered.com")
        return fixture["featuredcategories"]

    with pytest.raises(SourceFetchError):
        SteamAdapter(fetch_json=flaky).fetch()


@pytest.mark.parametrize("payload", [None, [], {"status": 1}, {"specials": {"items": "x"}}])
def test_malformed_payload_raises_source_fetch_error(payload: Any) -> None:
    with pytest.raises(SourceFetchError):
        SteamAdapter(fetch_json=lambda url, **_: payload).fetch()
