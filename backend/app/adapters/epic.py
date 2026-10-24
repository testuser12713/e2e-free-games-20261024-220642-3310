"""Epic Games Store adapter."""

from __future__ import annotations

from app import http
from app.adapters.base import FetchJson, FetchText, NormalizedDeal, SourceAdapter


class EpicAdapter(SourceAdapter):
    """Free-to-keep deals from the Epic Games Store."""

    name = "epic"

    def __init__(
        self,
        fetch_json: FetchJson = http.fetch_json,
        fetch_text: FetchText = http.fetch_text,
    ) -> None:
        self._fetch_json = fetch_json
        self._fetch_text = fetch_text

    def fetch(self) -> list[NormalizedDeal]:
        return []
