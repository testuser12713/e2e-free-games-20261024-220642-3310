"""Steam adapter.

Two public, key-less Steam store endpoints are used:

1. ``/api/featuredcategories`` — its ``specials`` list names the currently
   discounted apps with their discount percentage and end of the promotion.
2. ``/api/appdetails?appids=<id>`` — called only for the 100 % candidates, it
   tells the app's type (game, dlc, demo, …), whether it is free-to-play and its
   regular (initial) price in minor units.

Only apps of type ``game`` that are not free-to-play, have an initial price above
0 and a discount of exactly 100 % become deals. Every deal is platform ``pc``.
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

FEATURED_URL = "https://store.steampowered.com/api/featuredcategories"
APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
STORE_PAGE_URL = "https://store.steampowered.com/app/{app_id}/"
# Prices and currency are requested for the German storefront (EUR).
COUNTRY_CODE = "de"
LANGUAGE = "english"
STORE_NAME = "Steam"
# Upper bound for appdetails look-ups per run, so a malformed specials list can
# never turn one run into hundreds of requests.
MAX_DETAIL_LOOKUPS = 50
# Steam lists software (editors, utilities, …) with type "game"; these genre ids
# mark it. An app whose genres are ALL software genres is not a game.
SOFTWARE_GENRE_IDS = frozenset({"51", "52", "53", "54", "55", "56", "57", "58", "59", "60"})


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _timestamp(value: Any) -> datetime | None:
    seconds = _as_int(value)
    if seconds is None or seconds <= 0:
        return None
    try:
        return datetime.fromtimestamp(seconds, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


def _is_software(genres: Any) -> bool:
    if not isinstance(genres, list):
        return False
    ids = {str(g.get("id")) for g in genres if isinstance(g, dict) and g.get("id") is not None}
    return bool(ids) and ids <= SOFTWARE_GENRE_IDS


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _is_paid_game(data: dict[str, Any]) -> bool:
    """True for a full game that is not free-to-play and not software.

    Demos, DLC, soundtracks, videos … all carry a type other than "game".
    """
    if data.get("type") != "game" or data.get("is_free") is True:
        return False
    return not _is_software(data.get("genres"))


def _free_price(price: Any, special: dict[str, Any]) -> tuple[float, str] | None:
    """Return (original price in major units, currency) for a 100 % discount, else None."""
    if not isinstance(price, dict) or _as_int(price.get("discount_percent")) != 100:
        return None
    initial = _as_int(price.get("initial"))
    if initial is None or initial <= 0:
        return None
    currency = _text(price.get("currency")) or _text(special.get("currency"))
    if currency is None:
        return None
    return round(initial / 100, 2), currency.upper()


class SteamAdapter(SourceAdapter):
    """Free-to-keep deals (100 % discount on paid games) from the Steam store."""

    name = "steam"

    def __init__(
        self,
        fetch_json: FetchJson = http.fetch_json,
        fetch_text: FetchText = http.fetch_text,
    ) -> None:
        self._fetch_json = fetch_json
        self._fetch_text = fetch_text

    def fetch(self) -> list[NormalizedDeal]:
        candidates = self._free_candidates()
        deals: list[NormalizedDeal] = []
        for app_id, special in candidates[:MAX_DETAIL_LOOKUPS]:
            deal = self._deal_for(app_id, special)
            if deal is not None:
                deals.append(deal)
        return deals

    def _free_candidates(self) -> list[tuple[str, dict[str, Any]]]:
        """Return (app id, specials entry) for every 100 % special, deduplicated."""
        payload = self._fetch_json(FEATURED_URL, params={"cc": COUNTRY_CODE, "l": LANGUAGE})
        if not isinstance(payload, dict):
            raise SourceFetchError("Steam featuredcategories: unexpected payload")
        specials = payload.get("specials")
        if not isinstance(specials, dict) or not isinstance(specials.get("items"), list):
            raise SourceFetchError("Steam featuredcategories: no specials list")

        seen: set[str] = set()
        candidates: list[tuple[str, dict[str, Any]]] = []
        for item in specials["items"]:
            if not isinstance(item, dict):
                continue
            app_id = _as_int(item.get("id"))
            if app_id is None or app_id <= 0:
                continue
            if _as_int(item.get("discount_percent")) != 100:
                continue
            key = str(app_id)
            if key in seen:
                continue
            seen.add(key)
            candidates.append((key, item))
        return candidates

    def _deal_for(self, app_id: str, special: dict[str, Any]) -> NormalizedDeal | None:
        data = self._app_details(app_id)
        if data is None or not _is_paid_game(data):
            return None
        price = _free_price(data.get("price_overview"), special)
        if price is None:
            return None
        title = _text(data.get("name")) or _text(special.get("name"))
        url = safe_http_url(STORE_PAGE_URL.format(app_id=app_id))
        if title is None or url is None:
            return None
        image_url = safe_http_url(data.get("header_image")) or safe_http_url(
            special.get("header_image")
        )
        original_price, currency = price
        return NormalizedDeal(
            source_deal_id=app_id,
            title=title,
            store=STORE_NAME,
            platform="pc",
            original_price=original_price,
            currency=currency,
            url=url,
            image_url=image_url,
            starts_at=None,
            ends_at=_timestamp(special.get("discount_expiration")),
        )

    def _app_details(self, app_id: str) -> dict[str, Any] | None:
        """Return the appdetails ``data`` object, or None when Steam has none."""
        payload = self._fetch_json(
            APPDETAILS_URL,
            params={"appids": app_id, "cc": COUNTRY_CODE, "l": LANGUAGE},
        )
        if not isinstance(payload, dict):
            raise SourceFetchError(f"Steam appdetails {app_id}: unexpected payload")
        entry = payload.get(app_id)
        if not isinstance(entry, dict) or entry.get("success") is not True:
            return None
        data = entry.get("data")
        return data if isinstance(data, dict) else None
