"""GOG adapter.

Reads GOG's public catalog endpoint (the one gog.com's own store pages use),
asking only for discounted games whose final price is 0. Every product is still
checked locally: only a 100 % discount on a base price above 0 is kept, so
permanently free games, DLC and entries with base price 0 are dropped.
"""

from __future__ import annotations

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

CATALOG_URL = "https://catalog.gog.com/v1/catalog"
STORE_NAME = "GOG"
PAGE_SIZE = 48
MAX_PAGES = 5
# Product types that are full games; "dlc" and anything else is dropped.
GAME_PRODUCT_TYPES = frozenset({"game", "pack"})
# The catalog does not always announce when a promotion ends; when it does, it
# uses one of these keys (on the product or on its price object).
_END_DATE_KEYS = ("promoEndDate", "discountEndDate", "endDate")


def _parse_amount(value: Any) -> float | None:
    """Parse a money amount ("9.99" or 9.99) into a float, None when unusable."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().replace(",", "."))
        except ValueError:
            return None
    return None


def _parse_datetime(value: Any) -> datetime | None:
    """Parse an ISO 8601 timestamp into an aware UTC datetime, None when unusable."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _store_url(product: dict[str, Any]) -> str | None:
    link = product.get("storeLink")
    if link is not None:
        # A link the shop delivered but that is unsafe drops the deal.
        return safe_http_url(link)
    slug = product.get("slug")
    if isinstance(slug, str) and slug.strip():
        return safe_http_url(f"https://www.gog.com/en/game/{slug.strip()}")
    return None


def _image_url(product: dict[str, Any]) -> str | None:
    for key in ("coverHorizontal", "coverVertical"):
        url = safe_http_url(product.get(key))
        if url:
            return url
    return None


def _ends_at(product: dict[str, Any], price: dict[str, Any]) -> datetime | None:
    for source in (product, price):
        for key in _END_DATE_KEYS:
            parsed = _parse_datetime(source.get(key))
            if parsed is not None:
                return parsed
    return None


def _identity(product: dict[str, Any]) -> tuple[str, str] | None:
    """Return (product id, title) of a full game, None for DLC or incomplete entries."""
    product_id = product.get("id")
    title = product.get("title")
    if product_id is None or isinstance(product_id, bool) or not str(product_id).strip():
        return None
    if not isinstance(title, str) or not title.strip():
        return None
    product_type = product.get("productType")
    if not isinstance(product_type, str) or product_type.lower() not in GAME_PRODUCT_TYPES:
        return None
    return str(product_id).strip(), title.strip()


def _free_price(price: dict[str, Any]) -> tuple[float, str] | None:
    """Return (base price, currency) when the price is a 100 % discount on base > 0."""
    base_money = price.get("baseMoney")
    final_money = price.get("finalMoney")
    if not isinstance(base_money, dict) or not isinstance(final_money, dict):
        return None
    base = _parse_amount(base_money.get("amount"))
    final = _parse_amount(final_money.get("amount"))
    # 100 % discount on a game that normally costs money: final 0, base > 0.
    if base is None or final is None or base <= 0 or final != 0:
        return None
    currency = base_money.get("currency") or final_money.get("currency")
    if not isinstance(currency, str) or not currency.strip():
        return None
    return base, currency.strip().upper()


def parse_product(product: Any) -> NormalizedDeal | None:
    """Turn one catalog product into a deal, or None when it is not a free-to-keep game."""
    if not isinstance(product, dict):
        return None
    identity = _identity(product)
    price = product.get("price")
    if identity is None or not isinstance(price, dict):
        return None
    money = _free_price(price)
    url = _store_url(product)
    if money is None or url is None:
        return None
    product_id, title = identity
    base, currency = money

    return NormalizedDeal(
        source_deal_id=product_id,
        title=title,
        store=STORE_NAME,
        platform="pc",
        original_price=base,
        currency=currency,
        url=url,
        image_url=_image_url(product),
        starts_at=None,
        ends_at=_ends_at(product, price),
    )


class GogAdapter(SourceAdapter):
    """Free-to-keep deals from the GOG store."""

    name = "gog"

    def __init__(
        self,
        fetch_json: FetchJson = http.fetch_json,
        fetch_text: FetchText = http.fetch_text,
    ) -> None:
        self._fetch_json = fetch_json
        self._fetch_text = fetch_text

    def _params(self, page: int) -> dict[str, Any]:
        return {
            "limit": PAGE_SIZE,
            "page": page,
            "order": "desc:trending",
            "discounted": "eq:true",
            "productType": "in:game,pack",
            "price": "between:0,0",
            "countryCode": "DE",
            "currencyCode": "EUR",
            "locale": "en-US",
        }

    def fetch(self) -> list[NormalizedDeal]:
        deals: list[NormalizedDeal] = []
        seen: set[str] = set()
        page = 1
        while page <= MAX_PAGES:
            payload = self._fetch_json(CATALOG_URL, params=self._params(page))
            if not isinstance(payload, dict) or not isinstance(payload.get("products"), list):
                raise SourceFetchError("unexpected GOG catalog response: no product list")
            for product in payload["products"]:
                deal = parse_product(product)
                if deal is not None and deal.source_deal_id not in seen:
                    seen.add(deal.source_deal_id)
                    deals.append(deal)
            pages = payload.get("pages")
            if not isinstance(pages, int) or isinstance(pages, bool) or page >= pages:
                break
            page += 1
        return deals
