"""The scraper run engine: fetches every adapter and stores its deals."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session, sessionmaker

from app.adapters.base import SourceAdapter
from app.db import SessionLocal


@dataclass
class SourceResult:
    name: str
    ok: bool
    error: str | None
    deal_count: int


@dataclass
class RunSummary:
    results: list[SourceResult] = field(default_factory=list)


def run_all(
    session_factory: sessionmaker[Session] = SessionLocal,
    adapters: list[SourceAdapter] | None = None,
) -> RunSummary:
    """Run every adapter (``None`` -> the registered ones) and persist the results."""
    return RunSummary(results=[])
