"""Epic Games Store adapter.

Reads Epic's public ``freeGamesPromotions`` feed — the endpoint behind the store's
"Free Games" section — and keeps the offers that are free to keep right now: a
promotion window that contains the current moment, a discounted price of 0 and an
original price above 0. Upcoming promotions, permanently free (free-to-play or
zero-priced) entries and malformed elements are skipped.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
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

FREE_GAMES_URL = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
FREE_GAMES_PARAMS = {"locale": "de", "country": "DE", "allowCountries": "DE"}
PRODUCT_URL_TEMPLATE = "https://store.epicgames.com/de/p/{slug}"
STORE_NAME = "Epic Games Store"

# Key image types in order of preference for a landscape deal card.
_IMAGE_PREFERENCE = (
    "OfferImageWide",
    "DieselStoreFrontWide",
    "featuredMedia",
    "Thumbnail",
    "OfferImageTall",
    "DieselStoreFrontTall",
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _parse_datetime(value: Any) -> datetime | None:
    """Parse Epic's ISO 8601 timestamps (``2026-10-22T15:00:00.000Z``) as aware UTC."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _elements(payload: Any) -> list[Any]:
    """Return the offer list of the feed, or raise when the payload has the wrong shape."""
    try:
        elements = payload["data"]["Catalog"]["searchStore"]["elements"]
    except (KeyError, TypeError) as exc:
        raise SourceFetchError("Epic feed has no data.Catalog.searchStore.elements") from exc
    if not isinstance(elements, list):
        raise SourceFetchError("Epic feed elements is not a list")
    return elements


def _promotion_windows(element: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield the currently published (not upcoming) promotional offers of an element."""
    promotions = element.get("promotions")
    if not isinstance(promotions, dict):
        return
    groups = promotions.get("promotionalOffers")
    if not isinstance(groups, list):
        return
    for group in groups:
        if not isinstance(group, dict):
            continue
        offers = group.get("promotionalOffers")
        if not isinstance(offers, list):
            continue
        for offer in offers:
            if isinstance(offer, dict):
                yield offer


def _active_free_window(
    element: dict[str, Any], now: datetime
) -> tuple[datetime | None, datetime | None] | None:
    """Return (start, end) of a 100 % promotion running at ``now``, else None."""
    for offer in _promotion_windows(element):
        starts_at = _parse_datetime(offer.get("startDate"))
        ends_at = _parse_datetime(offer.get("endDate"))
        if starts_at is not None and starts_at > now:
            continue
        if ends_at is not None and ends_at <= now:
            continue
        setting = offer.get("discountSetting")
        # Epic encodes the price you PAY as a percentage: 0 means 100 % off.
        if (
            isinstance(setting, dict)
            and setting.get("discountType") == "PERCENTAGE"
            and setting.get("discountPercentage") != 0
        ):
            continue
        return starts_at, ends_at
    return None


def _price(element: dict[str, Any]) -> tuple[float, str] | None:
    """Return (original price in major units, currency) for a free offer, else None."""
    price = element.get("price")
    if not isinstance(price, dict):
        return None
    total = price.get("totalPrice")
    if not isinstance(total, dict):
        return None
    original = total.get("originalPrice")
    discounted = total.get("discountPrice")
    currency = total.get("currencyCode")
    if isinstance(original, bool) or not isinstance(original, int | float):
        return None
    if isinstance(discounted, bool) or not isinstance(discounted, int | float):
        return None
    if not isinstance(currency, str) or not currency.strip():
        return None
    if discounted != 0 or original <= 0:
        return None
    decimals = 2
    info = total.get("currencyInfo")
    if isinstance(info, dict):
        raw = info.get("decimals")
        if isinstance(raw, int) and not isinstance(raw, bool) and 0 <= raw <= 4:
            decimals = raw
    return round(original / (10**decimals), decimals), currency.strip().upper()


def _slug(element: dict[str, Any]) -> str | None:
    """Find the product page slug: catalog mapping, offer mapping, then legacy slugs."""
    for key in ("catalogNs", "offerMappings"):
        container = element.get(key)
        mappings = container.get("mappings") if isinstance(container, dict) else container
        if not isinstance(mappings, list):
            continue
        for mapping in mappings:
            if (
                isinstance(mapping, dict)
                and mapping.get("pageType") == "productHome"
                and isinstance(mapping.get("pageSlug"), str)
                and mapping["pageSlug"].strip()
            ):
                return mapping["pageSlug"].strip()
    for key in ("productSlug", "urlSlug"):
        value = element.get(key)
        if isinstance(value, str) and value.strip() and value.strip() != "[]":
            slug = value.strip()
            return slug[: -len("/home")] if slug.endswith("/home") else slug
    return None


def _image_url(element: dict[str, Any]) -> str | None:
    images = element.get("keyImages")
    if not isinstance(images, list):
        return None
    by_type: dict[str, str] = {}
    for image in images:
        if isinstance(image, dict) and isinstance(image.get("type"), str):
            url = safe_http_url(image.get("url"))
            if url is not None:
                by_type.setdefault(image["type"], url)
    for image_type in _IMAGE_PREFERENCE:
        if image_type in by_type:
            return by_type[image_type]
    return next(iter(by_type.values()), None)


class EpicAdapter(SourceAdapter):
    """Free-to-keep deals from the Epic Games Store."""

    name = "epic"

    def __init__(
        self,
        fetch_json: FetchJson = http.fetch_json,
        fetch_text: FetchText = http.fetch_text,
        *,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._fetch_json = fetch_json
        self._fetch_text = fetch_text
        self._now = now

    def fetch(self) -> list[NormalizedDeal]:
        payload = self._fetch_json(FREE_GAMES_URL, params=dict(FREE_GAMES_PARAMS))
        now = self._now()
        deals: list[NormalizedDeal] = []
        seen: set[str] = set()
        for element in _elements(payload):
            deal = self._normalize(element, now)
            if deal is not None and deal.source_deal_id not in seen:
                seen.add(deal.source_deal_id)
                deals.append(deal)
        return deals

    @staticmethod
    def _normalize(element: Any, now: datetime) -> NormalizedDeal | None:
        """Turn one feed element into a deal, or None when it is not a current free offer."""
        if not isinstance(element, dict):
            return None
        offer_id = element.get("id")
        title = element.get("title")
        if not isinstance(offer_id, str) or not offer_id.strip():
            return None
        if not isinstance(title, str) or not title.strip():
            return None
        window = _active_free_window(element, now)
        if window is None:
            return None
        price = _price(element)
        if price is None:
            return None
        slug = _slug(element)
        if slug is None:
            return None
        url = safe_http_url(PRODUCT_URL_TEMPLATE.format(slug=slug))
        if url is None:
            return None
        original_price, currency = price
        starts_at, ends_at = window
        return NormalizedDeal(
            source_deal_id=offer_id.strip(),
            title=title.strip(),
            store=STORE_NAME,
            platform="pc",
            original_price=original_price,
            currency=currency,
            url=url,
            image_url=_image_url(element),
            starts_at=starts_at,
            ends_at=ends_at,
        )
