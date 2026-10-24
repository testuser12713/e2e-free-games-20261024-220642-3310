"""Background scheduling of scraper runs (on start and every REFRESH_INTERVAL_HOURS)."""

from __future__ import annotations


def start_scheduler() -> None:
    """Start the periodic background runs."""


def stop_scheduler() -> None:
    """Stop the periodic background runs."""


def try_start_run() -> bool:
    """Start a run in a background thread; False when a run is already active."""
    return False


def is_running() -> bool:
    """True while a run is active."""
    return False
