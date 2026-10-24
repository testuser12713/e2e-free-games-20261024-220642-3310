"""POST /api/refresh — start one scraper run in the background.

The endpoint is unauthenticated, so it is protected twice (AC-14):

* at most one run is active process-wide (``scheduler.try_start_run``); a call
  during a run answers 409 and starts nothing;
* every client is rate limited in memory; above the limit it answers 429.

Privacy (AC-20): the client address is only used to derive an in-memory key
(a keyed hash with a per-process random salt). It is never logged, never
written to the database and forgotten when its window expires.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Request

from app import scheduler
from app.schemas import ErrorBody, RefreshStartedOut

router = APIRouter(prefix="/api", tags=["sources"])

RATE_LIMIT_MAX_CALLS = 5
RATE_LIMIT_WINDOW_SECONDS = 60.0


class RateLimiter:
    """Sliding-window limiter: at most ``max_calls`` per client in ``window_seconds``."""

    def __init__(
        self,
        max_calls: int = RATE_LIMIT_MAX_CALLS,
        window_seconds: float = RATE_LIMIT_WINDOW_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._clock = clock
        self._salt = secrets.token_bytes(32)
        self._calls: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _key(self, client: str) -> str:
        return hmac.new(self._salt, client.encode("utf-8"), hashlib.sha256).hexdigest()

    def allow(self, client: str) -> bool:
        """Record one call of ``client``; False when it exceeds the limit."""
        now = self._clock()
        cutoff = now - self.window_seconds
        key = self._key(client)
        with self._lock:
            # Forget every client whose window has passed, so nothing piles up.
            for stale in [k for k, calls in self._calls.items() if calls and calls[-1] <= cutoff]:
                del self._calls[stale]
            calls = self._calls.setdefault(key, deque())
            while calls and calls[0] <= cutoff:
                calls.popleft()
            if len(calls) >= self.max_calls:
                return False
            calls.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._calls.clear()


rate_limiter = RateLimiter()


def _client_id(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post(
    "/refresh",
    status_code=202,
    response_model=RefreshStartedOut,
    responses={409: {"model": ErrorBody}, 429: {"model": ErrorBody}},
)
def refresh(request: Request) -> RefreshStartedOut:
    if not rate_limiter.allow(_client_id(request)):
        raise HTTPException(
            status_code=429,
            detail={
                "code": "rate_limited",
                "message": "Too many refresh requests, please try again later.",
            },
            headers={"Retry-After": str(int(rate_limiter.window_seconds))},
        )
    if not scheduler.try_start_run():
        raise HTTPException(
            status_code=409,
            detail={"code": "run_active", "message": "A refresh run is already in progress."},
        )
    return RefreshStartedOut(status="started")
