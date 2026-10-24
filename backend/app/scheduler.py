"""Background scheduling of scraper runs (on start and every REFRESH_INTERVAL_HOURS).

Scheduling uses a plain daemon thread (no scheduler library). Every run —
whether started by the startup, the interval or ``POST /api/refresh`` — goes
through :func:`try_start_run`, which takes ONE process-wide lock, so at most
one run is active at any time.
"""

from __future__ import annotations

import logging
import threading

from app.config import get_settings
from app.runner import run_all

logger = logging.getLogger(__name__)

# The single process-wide run lock: held for exactly as long as a run is active.
_run_lock = threading.Lock()

# Guards the scheduler thread bookkeeping below.
_state_lock = threading.Lock()
_scheduler_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _execute_run() -> None:
    """Run every source once; releases the run lock when finished (lock already held)."""
    try:
        logger.info("scraper run started")
        summary = run_all()
        for result in summary.results:
            if result.ok:
                logger.info("source %s: ok, %d deals", result.name, result.deal_count)
            else:
                logger.warning("source %s: failed: %s", result.name, result.error)
        logger.info("scraper run finished (%d sources)", len(summary.results))
    except Exception:
        logger.exception("scraper run failed")
    finally:
        _run_lock.release()


def try_start_run() -> bool:
    """Start a run in a background thread; False when a run is already active."""
    if not _run_lock.acquire(blocking=False):
        return False
    try:
        thread = threading.Thread(target=_execute_run, name="scraper-run", daemon=True)
        thread.start()
    except Exception:
        _run_lock.release()
        raise
    return True


def is_running() -> bool:
    """True while a run is active."""
    return _run_lock.locked()


def _scheduler_loop(stop_event: threading.Event, run_on_start: bool, interval: float) -> None:
    if run_on_start and not try_start_run():
        logger.info("startup run skipped: a run is already active")
    while not stop_event.wait(interval):
        if not try_start_run():
            logger.info("scheduled run skipped: a run is already active")


def start_scheduler() -> None:
    """Start the periodic background runs (idempotent).

    Runs once right away when ``Settings.scrape_on_start`` is true, then every
    ``Settings.refresh_interval_hours``.
    """
    global _scheduler_thread, _stop_event
    settings = get_settings()
    with _state_lock:
        if _scheduler_thread is not None and _scheduler_thread.is_alive():
            return
        _stop_event = threading.Event()
        interval = settings.refresh_interval_hours * 3600.0
        _scheduler_thread = threading.Thread(
            target=_scheduler_loop,
            args=(_stop_event, settings.scrape_on_start, interval),
            name="scraper-scheduler",
            daemon=True,
        )
        _scheduler_thread.start()
    logger.info(
        "scheduler started: scrape_on_start=%s interval_hours=%g",
        settings.scrape_on_start,
        settings.refresh_interval_hours,
    )


def stop_scheduler() -> None:
    """Stop the periodic background runs; an active run finishes on its own."""
    global _scheduler_thread
    with _state_lock:
        thread = _scheduler_thread
        _scheduler_thread = None
        _stop_event.set()
    if thread is not None and thread is not threading.current_thread():
        thread.join(timeout=5)
