"""GamerPower giveaway aggregator adapter.

Reads GamerPower's public giveaways API (``/api/giveaways``) and keeps only
active, free-to-keep full games on PC or PS5 that carry a positive USD worth.
DLC, early-access and loot entries, other platforms (Android, Xbox, ...) and
entries without a worth ("N/A", "$0.00") are dropped. An entry that lists
several relevant platforms yields one deal per platform.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app import http
from app.adapters.base import (
    FetchJson,
    FetchText,
    NormalizedDeal,
    Platform,
    SourceAdapter,
    SourceFetchError,
)
from app.urls import safe_http_url

API_URL = "https://www.gamerpower.com/api/giveaways"

# Platform tokens in GamerPower's comma-separated ``platforms`` field that mean a
# PC copy, mapped to the store name shown to users.
_PC_STORES: dict[str, str] = {
    "steam": "Steam",
    "epic games store": "Epic Games Store",
    "gog": "GOG",
    "itch.io": "itch.io",
    "ubisoft": "Ubisoft Connect",
    "origin": "EA App",
    "ea app": "EA App",
    "battle.net": "Battle.net",
    "drm-free": "DRM-free",
}
_PC_TOKENS = frozenset({"pc"})
_PS5_TOKENS = frozenset({"ps5", "playstation 5"})
_PS5_STORE = "PlayStation Store"
_PC_FALLBACK_STORE = "PC"

_WORTH_RE = re.compile(r"^\$\s*(\d{1,3}(?:,\d{3})*|\d+)(?:\.(\d{1,2}))?$")
_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def parse_worth(value: Any) -> float | None:
    """Parse a GamerPower worth such as ``"$29.99"`` into a positive USD amount.

    Returns None for "N/A", zero, negative or otherwise unparseable values.
    """
    if not isinstance(value, str):
        return None
    match = _WORTH_RE.match(value.strip())
    if not match:
        return None
    whole = match.group(1).replace(",", "")
    cents = (match.group(2) or "0").ljust(2, "0")
    amount = float(f"{whole}.{cents}")
    return amount if amount > 0 else None


def parse_date(value: Any) -> datetime | None:
    """Parse a GamerPower date (``"YYYY-MM-DD HH:MM:SS"``) as UTC, or None."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def map_platforms(value: Any) -> list[tuple[Platform, str]]:
    """Map the ``platforms`` text to ``(platform, store)`` pairs, one per platform."""
    if not isinstance(value, str):
        return []
    tokens = [token.strip().lower() for token in value.split(",") if token.strip()]
    result: list[tuple[Platform, str]] = []
    pc_store = next((_PC_STORES[t] for t in tokens if t in _PC_STORES), None)
    if pc_store is not None or any(t in _PC_TOKENS for t in tokens):
        result.append(("pc", pc_store or _PC_FALLBACK_STORE))
    if any(t in _PS5_TOKENS for t in tokens):
        result.append(("ps5", _PS5_STORE))
    return result


class GamerPowerAdapter(SourceAdapter):
    """Free-to-keep deals from the GamerPower giveaway aggregator."""

    name = "gamerpower"

    def __init__(
        self,
        fetch_json: FetchJson = http.fetch_json,
        fetch_text: FetchText = http.fetch_text,
    ) -> None:
        self._fetch_json = fetch_json
        self._fetch_text = fetch_text

    def fetch(self) -> list[NormalizedDeal]:
        payload = self._fetch_json(API_URL, params={"type": "game"})
        if isinstance(payload, dict):
            # GamerPower answers {"status": 0, "status_message": "..."} when it
            # has no active giveaways at all.
            if payload.get("status") == 0:
                return []
            raise SourceFetchError("unexpected GamerPower response: object without giveaways")
        if not isinstance(payload, list):
            raise SourceFetchError("unexpected GamerPower response: not a list")

        now = datetime.now(UTC)
        deals: list[NormalizedDeal] = []
        for entry in payload:
            if isinstance(entry, dict):
                deals.extend(self._parse_entry(entry, now))
        return deals

    @staticmethod
    def _parse_entry(entry: dict[str, Any], now: datetime) -> list[NormalizedDeal]:
        if str(entry.get("type", "")).strip().lower() != "game":
            return []
        if str(entry.get("status", "")).strip().lower() != "active":
            return []
        giveaway_id = entry.get("id")
        title = entry.get("title")
        if giveaway_id is None or not isinstance(title, str) or not title.strip():
            return []
        worth = parse_worth(entry.get("worth"))
        if worth is None:
            return []
        url = safe_http_url(entry.get("open_giveaway_url"))
        if url is None:
            return []
        ends_at = parse_date(entry.get("end_date"))
        if ends_at is not None and ends_at <= now:
            return []
        starts_at = parse_date(entry.get("published_date"))
        image_url = safe_http_url(entry.get("thumbnail")) or safe_http_url(entry.get("image"))

        return [
            NormalizedDeal(
                source_deal_id=str(giveaway_id),
                title=title.strip(),
                store=store,
                platform=platform,
                original_price=worth,
                currency="USD",
                url=url,
                image_url=image_url,
                starts_at=starts_at,
                ends_at=ends_at,
            )
            for platform, store in map_platforms(entry.get("platforms"))
        ]
