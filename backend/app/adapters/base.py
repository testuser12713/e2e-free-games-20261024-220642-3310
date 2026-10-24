"""The shared interface every source adapter implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

Platform = Literal["pc", "ps5"]

# Signatures of app.http.fetch_json / app.http.fetch_text, injected into adapters
# so tests can replay recorded fixtures without any network access.
FetchJson = Callable[..., Any]
FetchText = Callable[..., str]


class SourceFetchError(Exception):
    """A source could not be fetched or parsed (timeout, HTTP error, bad payload)."""


@dataclass
class NormalizedDeal:
    """One deal in the source-independent shape the run engine stores."""

    source_deal_id: str
    title: str
    store: str
    platform: Platform
    original_price: float
    currency: str
    url: str
    image_url: str | None
    starts_at: datetime | None
    ends_at: datetime | None


class SourceAdapter(ABC):
    """A source of free-to-keep deals.

    ``fetch`` returns only deals with a 100 % discount, an original price above 0,
    platform ``pc`` or ``ps5`` and http(s) URLs. It raises ``SourceFetchError``
    when the source cannot be fetched or parsed.
    """

    name: str

    @abstractmethod
    def fetch(self) -> list[NormalizedDeal]:
        """Fetch the source and return its normalized free deals."""
