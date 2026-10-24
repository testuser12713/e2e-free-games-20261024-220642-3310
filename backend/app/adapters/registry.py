"""The list of active source adapters.

Adding a source: write one module under ``app/adapters/`` whose class implements
``SourceAdapter``, then add that class to ``ADAPTER_CLASSES`` below. The run
engine, the scheduler and the API pick it up without any further change.
"""

from __future__ import annotations

from app.adapters.base import SourceAdapter
from app.adapters.epic import EpicAdapter
from app.adapters.gamerpower import GamerPowerAdapter
from app.adapters.gog import GogAdapter
from app.adapters.playstation import PlayStationAdapter
from app.adapters.steam import SteamAdapter

ADAPTER_CLASSES: list[type[SourceAdapter]] = [
    EpicAdapter,
    SteamAdapter,
    GogAdapter,
    PlayStationAdapter,
    GamerPowerAdapter,
]


def get_adapters() -> list[SourceAdapter]:
    """Instantiate every registered adapter with its default (live) HTTP functions."""
    return [adapter_class() for adapter_class in ADAPTER_CLASSES]
