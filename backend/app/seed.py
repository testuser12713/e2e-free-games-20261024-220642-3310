"""Demo seed: ``python -m app.seed`` fills the database from app/fixtures/demo_deals.json.

Times in the fixture are offsets in hours relative to the moment of seeding
(negative = in the past), so the demo deals never go stale. Seeding is
idempotent: deals are upserted by their unique key (source, source_deal_id,
platform) and source states by name, so running it twice changes no row count.
It is only ever invoked explicitly (``make seed``), never at app start.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.models import Deal, SourceState, utcnow
from app.urls import safe_http_url

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "demo_deals.json"
ALLOWED_PLATFORMS = frozenset({"pc", "ps5"})


class SeedDataError(ValueError):
    """The demo fixture is missing, unreadable or holds an invalid entry."""


@dataclass(frozen=True)
class SeedResult:
    """How many demo rows were inserted / updated by one seed run."""

    deals_inserted: int
    deals_updated: int
    deals_skipped: int
    sources: int


def load_fixture(path: Path = FIXTURE_PATH) -> dict[str, Any]:
    """Read and parse the demo fixture file."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SeedDataError(f"cannot read demo fixture {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SeedDataError(f"demo fixture {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("deals"), list):
        raise SeedDataError(f"demo fixture {path} must be an object with a 'deals' list")
    return data


def _offset(now: datetime, hours: Any) -> datetime | None:
    if hours is None:
        return None
    if isinstance(hours, bool) or not isinstance(hours, int | float):
        raise SeedDataError(f"time offset must be a number of hours, got {hours!r}")
    return now + timedelta(hours=float(hours))


def _valid_deal(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Return the cleaned deal fields, or None when the entry breaks a deal rule."""
    try:
        price = float(entry["original_price"])
        platform = str(entry["platform"])
        source = str(entry["source"]).strip()
        source_deal_id = str(entry["source_deal_id"]).strip()
        title = str(entry["title"]).strip()
        store = str(entry["store"]).strip()
        currency = str(entry["currency"]).strip().upper()
    except (KeyError, TypeError, ValueError):
        return None
    url = safe_http_url(entry.get("url"))
    if (
        price <= 0
        or platform not in ALLOWED_PLATFORMS
        or not (source and source_deal_id and title and store and currency)
        or url is None
    ):
        return None
    return {
        "source": source,
        "source_deal_id": source_deal_id,
        "title": title,
        "store": store,
        "platform": platform,
        "original_price": price,
        "currency": currency,
        "url": url,
        "image_url": safe_http_url(entry.get("image_url")),
    }


def _hours_ago(now: datetime, hours: Any) -> datetime | None:
    if hours is None:
        return None
    return _offset(now, -float(hours))


def _upsert_deal(session: Session, entry: dict[str, Any], now: datetime) -> str:
    """Insert or update one demo deal; return "inserted", "updated" or "skipped"."""
    fields = _valid_deal(entry)
    if fields is None:
        return "skipped"
    ends_at = _offset(now, entry.get("ends_in_hours"))
    expired = bool(entry.get("expired", False))

    deal = session.execute(
        select(Deal).where(
            Deal.source == fields["source"],
            Deal.source_deal_id == fields["source_deal_id"],
            Deal.platform == fields["platform"],
        )
    ).scalar_one_or_none()
    outcome = "updated"
    if deal is None:
        first_seen_at = _hours_ago(now, entry.get("first_seen_hours_ago")) or now
        deal = Deal(**fields, first_seen_at=first_seen_at)
        session.add(deal)
        outcome = "inserted"
    else:
        for key, value in fields.items():
            setattr(deal, key, value)
    deal.starts_at = _offset(now, entry.get("starts_in_hours"))
    deal.ends_at = ends_at
    deal.expired = expired
    deal.expired_at = (ends_at or now) if expired else None
    deal.last_seen_at = (ends_at or now) if expired else now
    return outcome


def _upsert_source_state(session: Session, entry: dict[str, Any], now: datetime) -> None:
    """Insert or update the state row of one source, counting its active deals."""
    name = str(entry["name"])
    state = session.get(SourceState, name)
    if state is None:
        state = SourceState(name=name)
        session.add(state)
    ok = entry.get("ok")
    state.ok = None if ok is None else bool(ok)
    state.error = entry.get("error")
    state.last_run_at = _hours_ago(now, entry.get("last_run_hours_ago")) or now
    state.last_success_at = _hours_ago(now, entry.get("last_success_hours_ago"))
    state.deal_count = len(
        session.execute(select(Deal.id).where(Deal.source == name, Deal.expired.is_(False))).all()
    )


def seed_session(
    session: Session, data: dict[str, Any] | None = None, now: datetime | None = None
) -> SeedResult:
    """Upsert the demo deals and source states into ``session`` and commit."""
    data = load_fixture() if data is None else data
    now = now or utcnow()
    outcomes = {"inserted": 0, "updated": 0, "skipped": 0}

    for entry in data.get("deals", []):
        outcome = _upsert_deal(session, entry, now) if isinstance(entry, dict) else "skipped"
        outcomes[outcome] += 1
    session.flush()

    source_entries = [e for e in data.get("sources", []) if isinstance(e, dict) and e.get("name")]
    for entry in source_entries:
        _upsert_source_state(session, entry, now)

    session.commit()
    return SeedResult(
        outcomes["inserted"], outcomes["updated"], outcomes["skipped"], len(source_entries)
    )


def main() -> int:
    """Create the schema and load the demo deals (idempotent)."""
    init_db()
    try:
        data = load_fixture()
    except SeedDataError as exc:
        print(f"seed failed: {exc}", file=sys.stderr)
        return 1
    session = SessionLocal()
    try:
        result = seed_session(session, data)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    print(
        f"seeded demo data: {result.deals_inserted} deals inserted, "
        f"{result.deals_updated} updated, {result.deals_skipped} skipped, "
        f"{result.sources} source states"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
