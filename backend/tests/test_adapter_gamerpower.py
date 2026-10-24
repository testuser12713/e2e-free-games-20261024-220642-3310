"""AC-03/AC-15: the GamerPower adapter parses, filters and maps giveaways from a fixture."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.adapters.base import NormalizedDeal, SourceFetchError
from app.adapters.gamerpower import (
    API_URL,
    GamerPowerAdapter,
    map_platforms,
    parse_date,
    parse_worth,
)

FIXTURE = Path(__file__).parent / "fixtures" / "gamerpower_giveaways.json"


class FakeFetchJson:
    """Replays a payload and records the calls instead of touching the network."""

    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, url: str, **kwargs: Any) -> Any:
        self.calls.append((url, kwargs))
        return self.payload


def _fake_fetch_text(url: str, **kwargs: Any) -> str:
    raise AssertionError("GamerPower adapter must not fetch text")


def _load_fixture() -> list[dict[str, Any]]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _fetch(payload: Any) -> tuple[list[NormalizedDeal], FakeFetchJson]:
    fake = FakeFetchJson(payload)
    adapter = GamerPowerAdapter(fetch_json=fake, fetch_text=_fake_fetch_text)
    return adapter.fetch(), fake


def _by_key(deals: list[NormalizedDeal]) -> dict[tuple[str, str], NormalizedDeal]:
    return {(d.source_deal_id, d.platform): d for d in deals}


def test_adapter_name_and_endpoint() -> None:
    deals, fake = _fetch(_load_fixture())
    assert GamerPowerAdapter.name == "gamerpower"
    assert len(fake.calls) == 1
    assert fake.calls[0][0] == API_URL
    assert API_URL.startswith("https://")
    assert deals


def test_fixture_yields_only_pc_and_ps5_games_with_positive_worth() -> None:
    deals, _ = _fetch(_load_fixture())
    assert set(_by_key(deals)) == {
        ("3101", "pc"),
        ("3102", "pc"),
        ("3102", "ps5"),
        ("3103", "pc"),
    }
    for deal in deals:
        assert deal.platform in ("pc", "ps5")
        assert deal.original_price > 0
        assert deal.currency == "USD"
        assert deal.url.startswith("https://")


def test_dlc_early_access_other_platforms_na_zero_expired_and_unsafe_dropped() -> None:
    deals, _ = _fetch(_load_fixture())
    ids = {d.source_deal_id for d in deals}
    assert "3201" not in ids  # DLC
    assert "3202" not in ids  # Android
    assert "3203" not in ids  # worth N/A
    assert "3204" not in ids  # worth $0.00
    assert "3205" not in ids  # Early Access
    assert "3206" not in ids  # Xbox / PS4 only
    assert "3207" not in ids  # expired
    assert "3208" not in ids  # javascript: link


def test_entry_fields_are_parsed() -> None:
    deal = _by_key(_fetch(_load_fixture())[0])[("3101", "pc")]
    assert deal.title == "Starbound Voyager (Epic Games) Giveaway"
    assert deal.store == "Epic Games Store"
    assert deal.original_price == pytest.approx(24.99, abs=1e-2)
    assert deal.url == "https://www.gamerpower.com/open/starbound-voyager-epic-games-giveaway"
    assert deal.image_url == "https://www.gamerpower.com/offers/1/3101-starbound-voyager.jpg"
    assert deal.starts_at == datetime(2026, 10, 20, 15, 0, tzinfo=UTC)
    assert deal.ends_at == datetime(2099, 10, 29, 23, 59, tzinfo=UTC)


def test_multi_platform_entry_yields_one_deal_per_platform() -> None:
    deals = _by_key(_fetch(_load_fixture())[0])
    pc = deals[("3102", "pc")]
    ps5 = deals[("3102", "ps5")]
    assert pc.store == "Steam"
    assert ps5.store == "PlayStation Store"
    assert pc.original_price == pytest.approx(1019.50, abs=1e-2)
    assert pc.ends_at is None  # "N/A" end date
    assert ps5.title == pc.title


def test_unsafe_image_becomes_none_and_bare_pc_falls_back() -> None:
    deal = _by_key(_fetch(_load_fixture())[0])[("3103", "pc")]
    assert deal.image_url is None
    assert deal.store == "PC"


def test_no_active_giveaways_object_returns_empty() -> None:
    deals, _ = _fetch({"status": 0, "status_message": "No active giveaways available."})
    assert deals == []


@pytest.mark.parametrize("payload", [{"unexpected": True}, "oops", None, 42])
def test_unexpected_payload_raises_source_fetch_error(payload: Any) -> None:
    with pytest.raises(SourceFetchError):
        _fetch(payload)


def test_malformed_entries_are_skipped() -> None:
    good = _load_fixture()[0]
    payload = ["not a dict", {"type": "Game"}, {**good, "id": None}, {**good, "title": ""}, good]
    deals, _ = _fetch(payload)
    assert [d.source_deal_id for d in deals] == ["3101"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("$29.99", 29.99), ("$5", 5.0), ("$1,299.00", 1299.0), (" $3.5 ", 3.5)],
)
def test_parse_worth_valid(raw: str, expected: float) -> None:
    assert parse_worth(raw) == pytest.approx(expected, abs=1e-2)


@pytest.mark.parametrize("raw", ["N/A", "$0.00", "$0", "", "29.99", "€9.99", None, 12])
def test_parse_worth_invalid(raw: Any) -> None:
    assert parse_worth(raw) is None


def test_parse_date() -> None:
    assert parse_date("2026-01-02 03:04:05") == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    assert parse_date("N/A") is None
    assert parse_date(None) is None


def test_map_platforms() -> None:
    assert map_platforms("PC, GOG") == [("pc", "GOG")]
    assert map_platforms("Steam") == [("pc", "Steam")]
    assert map_platforms("PS4, Playstation 5") == [("ps5", "PlayStation Store")]
    assert map_platforms("Android, iOS") == []
    assert map_platforms("Nintendo Switch, Xbox One") == []
    assert map_platforms(None) == []
