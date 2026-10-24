"""The scraper run engine: fetches every adapter and stores its deals.

Each adapter runs in isolation: a failure in one source (``SourceFetchError`` or
any other exception, including while saving) is recorded only in that source's
``SourceState`` and leaves its stored deals untouched, while every other source
is still fetched and saved.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.adapters import registry
from app.adapters.base import NormalizedDeal, SourceAdapter
from app.db import SessionLocal
from app.models import Deal, SourceState
from app.urls import safe_http_url

logger = logging.getLogger(__name__)

ALLOWED_PLATFORMS = frozenset({"pc", "ps5"})
MAX_ERROR_LENGTH = 500


@dataclass
class SourceResult:
    name: str
    ok: bool
    error: str | None
    deal_count: int


@dataclass
class RunSummary:
    results: list[SourceResult] = field(default_factory=list)


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _truncate_error(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}".strip()
    if len(text) > MAX_ERROR_LENGTH:
        text = text[: MAX_ERROR_LENGTH - 1] + "…"
    return text


def validate_deal(deal: NormalizedDeal) -> NormalizedDeal | None:
    """Re-check one adapter result; return a sanitized copy or None to drop it.

    Dropped: original price not a finite number above 0, platform other than
    pc/ps5, empty id/title/store, or a link that is not http/https. An image URL
    that is not http/https is replaced by None.
    """
    price = deal.original_price
    if isinstance(price, bool) or not isinstance(price, int | float):
        return None
    if not math.isfinite(price) or price <= 0:
        return None
    if deal.platform not in ALLOWED_PLATFORMS:
        return None
    source_deal_id = str(deal.source_deal_id or "").strip()
    title = (deal.title or "").strip()
    store = (deal.store or "").strip()
    if not source_deal_id or not title or not store:
        return None
    url = safe_http_url(deal.url)
    if url is None:
        return None
    return NormalizedDeal(
        source_deal_id=source_deal_id,
        title=title,
        store=store,
        platform=deal.platform,
        original_price=float(price),
        currency=(deal.currency or "").strip().upper() or "EUR",
        url=url,
        image_url=safe_http_url(deal.image_url),
        starts_at=_as_utc(deal.starts_at),
        ends_at=_as_utc(deal.ends_at),
    )


def _get_state(session: Session, name: str) -> SourceState:
    state = session.get(SourceState, name)
    if state is None:
        state = SourceState(name=name, deal_count=0)
        session.add(state)
    return state


def _active_count(session: Session, name: str) -> int:
    rows = session.scalars(
        select(Deal.id).where(Deal.source == name, Deal.expired.is_(False))
    ).all()
    return len(rows)


def _save_success(
    session: Session, name: str, deals: list[NormalizedDeal], run_at: datetime
) -> int:
    """Upsert the source's deals, expire vanished/ended ones, update its state."""
    unique: dict[tuple[str, str], NormalizedDeal] = {}
    for raw in deals:
        valid = validate_deal(raw)
        if valid is not None:
            unique[(valid.source_deal_id, valid.platform)] = valid

    existing = {
        (d.source_deal_id, d.platform): d
        for d in session.scalars(select(Deal).where(Deal.source == name)).all()
    }
    seen_ids: set[int] = set()
    for key, item in unique.items():
        row = existing.get(key)
        if row is None:
            row = Deal(
                source=name,
                source_deal_id=item.source_deal_id,
                platform=item.platform,
                first_seen_at=run_at,
            )
            session.add(row)
        row.store = item.store
        row.title = item.title
        row.original_price = item.original_price
        row.currency = item.currency
        row.url = item.url
        row.image_url = item.image_url
        row.starts_at = item.starts_at
        row.ends_at = item.ends_at
        row.last_seen_at = run_at
        row.expired = False
        row.expired_at = None
        session.flush()
        seen_ids.add(row.id)

    # Deals of this source not delivered in this successful run are gone.
    for row in existing.values():
        if row.id not in seen_ids and not row.expired:
            row.expired = True
            row.expired_at = run_at
    session.flush()

    # Deals whose offer period has ended disappear as well.
    session.execute(
        update(Deal)
        .where(
            Deal.source == name,
            Deal.expired.is_(False),
            Deal.ends_at.is_not(None),
            Deal.ends_at < run_at,
        )
        .values(expired=True, expired_at=run_at)
        .execution_options(synchronize_session="fetch")
    )

    count = _active_count(session, name)
    state = _get_state(session, name)
    state.ok = True
    state.error = None
    state.last_run_at = run_at
    state.last_success_at = run_at
    state.deal_count = count
    return count


def _save_failure(
    session_factory: sessionmaker[Session], name: str, error: str, run_at: datetime
) -> int:
    """Record a failed run; the source's stored deals stay untouched."""
    with session_factory() as session:
        state = _get_state(session, name)
        state.ok = False
        state.error = error
        state.last_run_at = run_at
        count = _active_count(session, name)
        state.deal_count = count
        session.commit()
        return count


def _run_one(session_factory: sessionmaker[Session], adapter: SourceAdapter) -> SourceResult:
    name = str(getattr(adapter, "name", "") or type(adapter).__name__)
    run_at = _now()
    try:
        deals = adapter.fetch()
        with session_factory() as session:
            try:
                count = _save_success(session, name, list(deals or []), run_at)
                session.commit()
            except Exception:
                session.rollback()
                raise
    except Exception as exc:
        error = _truncate_error(exc)
        logger.warning("%s source=%s failed: %s", run_at.isoformat(), name, error)
        try:
            count = _save_failure(session_factory, name, error, run_at)
        except Exception as state_exc:
            logger.error(
                "%s source=%s could not record failure: %s",
                _now().isoformat(),
                name,
                _truncate_error(state_exc),
            )
            count = 0
        return SourceResult(name=name, ok=False, error=error, deal_count=count)

    logger.info("%s source=%s ok deals=%d", run_at.isoformat(), name, count)
    return SourceResult(name=name, ok=True, error=None, deal_count=count)


def run_all(
    session_factory: sessionmaker[Session] = SessionLocal,
    adapters: list[SourceAdapter] | None = None,
) -> RunSummary:
    """Run every adapter (``None`` -> the registered ones) and persist the results."""
    if adapters is None:
        try:
            adapters = registry.get_adapters()
        except Exception as exc:
            logger.error(
                "%s could not instantiate adapters: %s", _now().isoformat(), _truncate_error(exc)
            )
            adapters = []
    summary = RunSummary()
    for adapter in adapters:
        summary.results.append(_run_one(session_factory, adapter))
    return summary
