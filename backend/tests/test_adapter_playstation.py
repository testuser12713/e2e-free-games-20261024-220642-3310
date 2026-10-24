"""PlayStation Store adapter, replayed against a hand-recorded page fixture."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.adapters.base import SourceFetchError
from app.adapters.playstation import (
    STORE_NAME,
    PlayStationAdapter,
    category_page_url,
)

FIXTURE = Path(__file__).parent / "fixtures" / "playstation_deals.json"


def _payload() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _page(payload: dict[str, Any]) -> str:
    """Wrap the recorded __NEXT_DATA__ payload in the store's HTML shell."""
    return (
        "<!DOCTYPE html><html lang='de'><head><title>Angebote</title></head><body>"
        "<div id='__next'></div>"
        '<script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(payload)}</script></body></html>"
    )


class FakeFetchText:
    def __init__(self, pages: list[str]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    def __call__(self, url: str, **_: Any) -> str:
        self.calls.append(url)
        return self.pages[len(self.calls) - 1]


def _unused_fetch_json(*_: Any, **__: Any) -> Any:
    raise AssertionError("the PlayStation adapter reads the page text only")


def _adapter(pages: list[str]) -> tuple[PlayStationAdapter, FakeFetchText]:
    fake = FakeFetchText(pages)
    return PlayStationAdapter(fetch_json=_unused_fetch_json, fetch_text=fake), fake


def test_parses_fixture_into_ps5_deals() -> None:
    adapter, fake = _adapter([_page(_payload())])
    deals = adapter.fetch()

    assert fake.calls == [category_page_url(1)]
    by_id = {d.source_deal_id: d for d in deals}
    assert set(by_id) == {
        "EP4062-PPSA02105_00-MOVINGOUT2000000",
        "EP0700-PPSA01542_00-LITTLENIGHTMARE2",
        "EP0007-PPSA04444_00-UNSAFEIMAGE00000",
    }

    moving = by_id["EP4062-PPSA02105_00-MOVINGOUT2000000"]
    assert moving.title == "Moving Out 2"
    assert moving.store == STORE_NAME == "PlayStation Store"
    assert moving.platform == "ps5"
    assert moving.original_price == pytest.approx(29.99, abs=1e-2)
    assert moving.currency == "EUR"
    assert moving.url == (
        "https://store.playstation.com/de-de/product/EP4062-PPSA02105_00-MOVINGOUT2000000"
    )
    assert moving.image_url is not None and moving.image_url.endswith("moving-out-2-master.png")
    assert moving.starts_at is None
    assert moving.ends_at == datetime.fromtimestamp(1730512740, tz=UTC)


def test_resolves_apollo_references_and_dedupes() -> None:
    adapter, _ = _adapter([_page(_payload())])
    deals = adapter.fetch()

    nightmares = [d for d in deals if d.title == "Little Nightmares II"]
    assert len(nightmares) == 1
    assert nightmares[0].original_price == pytest.approx(29.99, abs=1e-2)
    assert nightmares[0].ends_at is None
    assert nightmares[0].image_url is not None
    assert nightmares[0].image_url.endswith("little-nightmares-2-master.png")


def test_keeps_only_full_discounts_with_real_base_price() -> None:
    deals = _adapter([_page(_payload())])[0].fetch()
    titles = {d.title for d in deals}

    assert "Sniper Elite 5" not in titles  # 50 % off only
    assert "Arena Legends" not in titles  # free-to-play
    assert "Zero Price Puzzle" not in titles  # base price 0
    assert "Members Only Racer" not in titles  # free with PS Plus only
    assert all(d.original_price > 0 for d in deals)


def test_maps_ps5_only_and_drops_ps4_only_and_add_ons() -> None:
    deals = _adapter([_page(_payload())])[0].fetch()
    titles = {d.title for d in deals}

    assert "Last Gen Adventure" not in titles  # PS4 only
    assert "Space Saga: Expansion Pack" not in titles  # add-on
    assert {d.platform for d in deals} == {"ps5"}
    assert {d.store for d in deals} == {"PlayStation Store"}


def test_unsafe_image_url_becomes_none() -> None:
    deals = _adapter([_page(_payload())])[0].fetch()
    harbour = next(d for d in deals if d.title == "Harbour Tales")
    assert harbour.image_url is None
    assert harbour.url.startswith("https://store.playstation.com/")


def test_empty_valid_listing_returns_empty_list() -> None:
    payload = _payload()
    state = payload["props"]["apolloState"]
    grid_key = next(k for k in state if k.startswith("CategoryGrid:"))
    state[grid_key]["products"] = []
    assert _adapter([_page(payload)])[0].fetch() == []


def test_follows_pages_until_last() -> None:
    first = _payload()
    state = first["props"]["apolloState"]
    grid_key = next(k for k in state if k.startswith("CategoryGrid:"))
    state[grid_key]["pageInfo"]["isLast"] = False

    second = _payload()
    state2 = second["props"]["apolloState"]
    state2[grid_key]["products"] = [{"__ref": "Product:EP0700-PPSA01542_00-LITTLENIGHTMARE2:de-de"}]

    adapter, fake = _adapter([_page(first), _page(second)])
    deals = adapter.fetch()

    assert fake.calls == [category_page_url(1), category_page_url(2)]
    assert len(deals) == 3  # the repeated product on page 2 is not duplicated


@pytest.mark.parametrize(
    "html",
    [
        "<html><body><h1>Wartungsarbeiten</h1></body></html>",
        '<script id="__NEXT_DATA__" type="application/json">{not json</script>',
        '<script id="__NEXT_DATA__" type="application/json">{"props": {}}</script>',
        '<script id="__NEXT_DATA__" type="application/json">'
        '{"props": {"apolloState": {"ROOT_QUERY": {}}}}</script>',
        '<script id="__NEXT_DATA__" type="application/json">'
        '{"props": {"apolloState": {"CategoryGrid:x": {"__typename": "CategoryGrid"}}}}'
        "</script>",
    ],
)
def test_unparseable_page_raises_source_fetch_error(html: str) -> None:
    with pytest.raises(SourceFetchError):
        _adapter([html])[0].fetch()


def test_fetch_errors_propagate() -> None:
    def failing(*_: Any, **__: Any) -> str:
        raise SourceFetchError("timeout after 10s")

    adapter = PlayStationAdapter(fetch_json=_unused_fetch_json, fetch_text=failing)
    with pytest.raises(SourceFetchError):
        adapter.fetch()
