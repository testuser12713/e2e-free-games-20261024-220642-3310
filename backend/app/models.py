"""ORM models: scraped deals and the per-source run state."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Dialect,
    Float,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Stores datetimes as naive UTC in SQLite and returns them timezone-aware (UTC)."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Deal(Base):
    """One free-to-keep offer of one game on one platform from one source."""

    __tablename__ = "deals"
    __table_args__ = (
        UniqueConstraint("source", "source_deal_id", "platform", name="uq_deal_source_platform"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    source_deal_id: Mapped[str] = mapped_column(String(255))
    store: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    platform: Mapped[str] = mapped_column(String(8), index=True)
    original_price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8))
    url: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    expired: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    expired_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class SourceState(Base):
    """Outcome of the most recent run of one source adapter."""

    __tablename__ = "source_states"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_run_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    deal_count: Mapped[int] = mapped_column(Integer, default=0)
