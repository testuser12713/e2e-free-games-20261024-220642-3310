"""PlayStation Store adapter.

The PlayStation Store renders its category grids server-side with Next.js and
embeds the full data of the page as JSON in ``<script id="__NEXT_DATA__">``.
Under ``props.apolloState`` that JSON holds a normalized Apollo cache: one
``CategoryGrid:…`` entry per grid page (its ``products`` are references) and one
``Product:…`` entry per product with ``platforms``, ``storeDisplayClassification``,
``price`` (``basePriceValue`` / ``discountedValue`` in minor units, ``currencyCode``,
``isFree``, ``endTime`` in epoch milliseconds) and ``media``.

The adapter reads the deals category page by page and keeps only full PS5 games
whose discounted price is 0 while the base price is above 0. PS4-only entries,
add-ons, demos, free-to-play titles (``isFree`` or base price 0) and prices that
are only free with a PlayStation Plus subscription are dropped.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app import http
from app.adapters.base import (
    FetchJson,
    FetchText,
    NormalizedDeal,
    SourceAdapter,
    SourceFetchError,
)
from app.urls import safe_http_url

STORE_NAME = "PlayStation Store"
STORE_BASE_URL = "https://store.playstation.com"
LOCALE = "de-de"
DEFAULT_CURRENCY = "EUR"
# The store's "Angebote" (all deals) category grid.
DEALS_CATEGORY_ID = "3f772501-f6f8-49b7-abac-874a88ca4897"
MAX_PAGES = 10

# Store classifications that are a complete game (not an add-on, demo, theme …).
GAME_CLASSIFICATIONS = frozenset({"FULL_GAME", "GAME_BUNDLE", "PREMIUM_EDITION"})
# Service brandings under which the shown price applies to subscribers only.
SUBSCRIPTION_BRANDINGS = frozenset({"PS_PLUS", "PS_PLUS_EXTRA", "PS_PLUS_PREMIUM", "EA_ACCESS"})

_NEXT_DATA_RE = re.compile(
    r"<script[^>]*\bid=[\"']__NEXT_DATA__[\"'][^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)


def category_page_url(page: int) -> str:
    """URL of one page of the deals category grid (pages start at 1)."""
    return f"{STORE_BASE_URL}/{LOCALE}/category/{DEALS_CATEGORY_ID}/{page}"


def product_url(product_id: str) -> str:
    """Public store page of one product."""
    return f"{STORE_BASE_URL}/{LOCALE}/product/{product_id}"


def extract_apollo_state(html: str) -> dict[str, Any]:
    """Return the Apollo cache embedded in a store page, or raise SourceFetchError."""
    match = _NEXT_DATA_RE.search(html)
    if match is None:
        raise SourceFetchError("PlayStation Store page carries no __NEXT_DATA__ block")
    try:
        data = json.loads(match.group(1))
    except ValueError as exc:
        raise SourceFetchError("PlayStation Store page data is not valid JSON") from exc
    props = data.get("props") if isinstance(data, dict) else None
    state = props.get("apolloState") if isinstance(props, dict) else None
    if not isinstance(state, dict):
        raise SourceFetchError("PlayStation Store page data has no apolloState")
    return state


def _resolve(state: dict[str, Any], value: Any) -> Any:
    """Follow an Apollo ``{"__ref": key}`` reference; other values pass through."""
    if isinstance(value, dict) and set(value) == {"__ref"}:
        return state.get(value["__ref"])
    return value


def _find_grid(state: dict[str, Any]) -> dict[str, Any]:
    grids = [
        value
        for key, value in state.items()
        if isinstance(value, dict)
        and (value.get("__typename") == "CategoryGrid" or key.startswith("CategoryGrid:"))
    ]
    if not grids:
        raise SourceFetchError("PlayStation Store page has no category grid")
    grid = grids[0]
    if not isinstance(grid.get("products"), list):
        raise SourceFetchError("PlayStation Store category grid has no product list")
    return grid


def _parse_end_time(value: Any) -> datetime | None:
    """``endTime`` is epoch milliseconds, delivered as a string or a number."""
    if value is None or isinstance(value, bool):
        return None
    try:
        millis = int(value)
    except (TypeError, ValueError):
        return None
    if millis <= 0:
        return None
    try:
        return datetime.fromtimestamp(millis / 1000, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


def _minor_units(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return int(value)


def _master_image(state: dict[str, Any], media: Any) -> str | None:
    if not isinstance(media, list):
        return None
    images = [_resolve(state, item) for item in media]
    images = [m for m in images if isinstance(m, dict) and m.get("type", "IMAGE") == "IMAGE"]
    for role in ("MASTER", "GAMEHUB_COVER_ART", "EDITION_KEY_ART"):
        for image in images:
            if image.get("role") == role:
                url = safe_http_url(image.get("url"))
                if url:
                    return url
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _is_ps5_game(product: dict[str, Any]) -> bool:
    platforms = product.get("platforms")
    if not isinstance(platforms, list) or "PS5" not in platforms:
        return False
    return product.get("storeDisplayClassification") in GAME_CLASSIFICATIONS


def _free_base_price(price: Any) -> int | None:
    """Base price in minor units when the price is a 100 % discount for everyone."""
    if not isinstance(price, dict) or price.get("isFree") is True:
        return None
    brandings = price.get("serviceBranding") or []
    if isinstance(brandings, list) and SUBSCRIPTION_BRANDINGS.intersection(brandings):
        return None
    base = _minor_units(price.get("basePriceValue"))
    discounted = _minor_units(price.get("discountedValue"))
    if base is None or discounted is None or base <= 0 or discounted != 0:
        return None
    return base


def _normalize(state: dict[str, Any], product: dict[str, Any]) -> NormalizedDeal | None:
    """Map one product to a deal, or None when it is not a free-to-keep PS5 game."""
    product_id = _text(product.get("id"))
    title = _text(product.get("name"))
    if product_id is None or title is None or not _is_ps5_game(product):
        return None
    price = _resolve(state, product.get("price"))
    base = _free_base_price(price)
    if base is None:
        return None

    url = safe_http_url(product_url(product_id))
    if url is None:
        return None
    currency = _text(price.get("currencyCode")) or DEFAULT_CURRENCY

    return NormalizedDeal(
        source_deal_id=product_id,
        title=title,
        store=STORE_NAME,
        platform="ps5",
        original_price=round(base / 100, 2),
        currency=currency.upper(),
        url=url,
        image_url=_master_image(state, product.get("media")),
        starts_at=None,
        ends_at=_parse_end_time(price.get("endTime")),
    )


def parse_listing(html: str) -> tuple[list[NormalizedDeal], bool]:
    """Parse one category page into (free PS5 deals, whether it was the last page)."""
    state = extract_apollo_state(html)
    grid = _find_grid(state)
    deals: list[NormalizedDeal] = []
    for ref in grid["products"]:
        product = _resolve(state, ref)
        if not isinstance(product, dict):
            continue
        deal = _normalize(state, product)
        if deal is not None:
            deals.append(deal)
    page_info = _resolve(state, grid.get("pageInfo"))
    is_last = not grid["products"]
    if isinstance(page_info, dict) and isinstance(page_info.get("isLast"), bool):
        is_last = is_last or page_info["isLast"]
    return deals, is_last


class PlayStationAdapter(SourceAdapter):
    """Free-to-keep deals from the PlayStation Store."""

    name = "playstation"

    def __init__(
        self,
        fetch_json: FetchJson = http.fetch_json,
        fetch_text: FetchText = http.fetch_text,
    ) -> None:
        self._fetch_json = fetch_json
        self._fetch_text: Callable[..., str] = fetch_text

    def fetch(self) -> list[NormalizedDeal]:
        deals: dict[str, NormalizedDeal] = {}
        for page in range(1, MAX_PAGES + 1):
            html = self._fetch_text(category_page_url(page))
            if not isinstance(html, str):
                raise SourceFetchError("PlayStation Store returned no page text")
            page_deals, is_last = parse_listing(html)
            for deal in page_deals:
                deals.setdefault(deal.source_deal_id, deal)
            if is_last:
                break
        return list(deals.values())
