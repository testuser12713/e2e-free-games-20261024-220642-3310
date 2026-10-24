"""GogAdapter against a hand-recorded catalog fixture, with an injected fake fetch_json."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.adapters.base import SourceAdapter, SourceFetchError
from app.adapters.gog import CATALOG_URL, GogAdapter

FIXTURE = Path(__file__).parent / "fixtures" / "gog_catalog.json"


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class FakeFetchJson:
    """Returns queued payloads and records every call."""

    def __init__(self, *payloads: Any) -> None:
        self._payloads = list(payloads)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, url: str, *, params: Any = None, headers: Any = None) -> Any:
        self.calls.append((url, dict(params or {})))
        return self._payloads.pop(0)


def _fail_fetch_text(*_args: Any, **_kwargs: Any) -> str:
    raise AssertionError("GogAdapter must not call fetch_text")


def _adapter(fetch_json: Any) -> GogAdapter:
    return GogAdapter(fetch_json=fetch_json, fetch_text=_fail_fetch_text)


def test_is_a_source_adapter_named_gog() -> None:
    adapter = _adapter(FakeFetchJson(_load_fixture()))
    assert isinstance(adapter, SourceAdapter)
    assert adapter.name == "gog"


def test_parses_fixture_into_normalized_deals() -> None:
    fake = FakeFetchJson(_load_fixture())
    deals = _adapter(fake).fetch()

    assert [d.source_deal_id for d in deals] == ["1207658930", "1440164514"]
    witcher = deals[0]
    assert witcher.title == "The Witcher: Enhanced Edition"
    assert witcher.store == "GOG"
    assert witcher.original_price == pytest.approx(9.99, abs=1e-2)
    assert witcher.currency == "EUR"
    assert witcher.url == "https://www.gog.com/en/game/the_witcher_enhanced_edition"
    assert witcher.image_url == "https://images.gog-statics.com/witcher_horizontal.png"
    assert witcher.starts_at is None
    assert witcher.ends_at == datetime(2026, 10, 27, 13, 0, tzinfo=UTC)

    assert fake.calls[0][0] == CATALOG_URL
    assert fake.calls[0][1]["discounted"] == "eq:true"


def test_keeps_only_full_discount_with_base_price_above_zero() -> None:
    deals = _adapter(FakeFetchJson(_load_fixture())).fetch()
    titles = {d.title for d in deals}

    assert all(d.original_price > 0 for d in deals)
    assert "Free To Play Card Game" not in titles  # base price 0
    assert "Half Price Strategy" not in titles  # only 50 %
    assert "Some Game - Soundtrack" not in titles  # DLC
    assert "Broken Entry Without Price" not in titles  # no price data


def test_platform_is_always_pc() -> None:
    deals = _adapter(FakeFetchJson(_load_fixture())).fetch()
    assert deals
    assert {d.platform for d in deals} == {"pc"}


def test_unsafe_urls_drop_the_deal_or_the_image() -> None:
    deals = _adapter(FakeFetchJson(_load_fixture())).fetch()
    by_title = {d.title: d for d in deals}

    assert "Unsafe Link Game" not in by_title
    assert by_title["Retro Adventure Pack"].image_url is None
    assert all(d.url.startswith("https://") for d in deals)


def test_follows_pages_and_dedupes() -> None:
    first = _load_fixture()
    first["pages"] = 2
    second = {"pages": 2, "products": [first["products"][0]]}
    fake = FakeFetchJson(first, second)

    deals = _adapter(fake).fetch()

    assert [call[1]["page"] for call in fake.calls] == [1, 2]
    assert len(deals) == 2


def test_fetch_error_propagates() -> None:
    def failing(*_args: Any, **_kwargs: Any) -> Any:
        raise SourceFetchError("timeout after 10s")

    with pytest.raises(SourceFetchError, match="timeout"):
        _adapter(failing).fetch()


@pytest.mark.parametrize("payload", [None, [], {"products": "nope"}, {"pages": 1}])
def test_malformed_payload_raises_source_fetch_error(payload: Any) -> None:
    with pytest.raises(SourceFetchError):
        _adapter(FakeFetchJson(payload)).fetch()
