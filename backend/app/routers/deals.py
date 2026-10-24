"""GET /api/deals — searchable, filterable, sortable list of current free deals."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Deal
from app.schemas import DealListOut, DealOut

router = APIRouter(prefix="/api", tags=["deals"])

SortKey = Literal["title", "original_price", "ends_at", "first_seen"]

PLATFORMS: tuple[str, ...] = ("pc", "ps5")
_LIKE_ESCAPE = "\\"


def escape_like(value: str) -> str:
    """Escape LIKE wildcards so ``value`` matches literally (used with ESCAPE '\\')."""
    return (
        value.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
        .replace("%", _LIKE_ESCAPE + "%")
        .replace("_", _LIKE_ESCAPE + "_")
    )


def current_deal_conditions(now: datetime | None = None) -> list[ColumnElement[bool]]:
    """Conditions every listed deal fulfils: not expired, price > 0, platform pc/ps5."""
    moment = now or datetime.now(UTC)
    return [
        Deal.expired.is_(False),
        Deal.original_price > 0,
        Deal.platform.in_(PLATFORMS),
        or_(Deal.ends_at.is_(None), Deal.ends_at > moment),
    ]


def _order_by(sort: SortKey, order: Literal["asc", "desc"]) -> list[ColumnElement[object]]:
    descending = order == "desc"

    def direction(column: ColumnElement[object]) -> ColumnElement[object]:
        return column.desc() if descending else column.asc()

    tiebreak = direction(Deal.id)
    if sort == "title":
        return [direction(func.lower(Deal.title)), direction(Deal.title), tiebreak]
    if sort == "original_price":
        return [direction(Deal.original_price), tiebreak]
    if sort == "ends_at":
        # Deals without an end date go last in both directions.
        return [Deal.ends_at.is_(None).asc(), direction(Deal.ends_at), tiebreak]
    return [direction(Deal.first_seen_at), tiebreak]


@router.get("/deals", response_model=DealListOut)
def list_deals(
    q: str | None = Query(default=None, max_length=200),
    platform: Literal["pc", "ps5"] | None = None,
    store: str | None = Query(default=None, max_length=128),
    sort: SortKey = "first_seen",
    order: Literal["asc", "desc"] = "desc",
    min_price: float | None = Query(default=None, ge=0, allow_inf_nan=False),
    max_price: float | None = Query(default=None, ge=0, allow_inf_nan=False),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> DealListOut:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise RequestValidationError(
            [
                {
                    "loc": ("query", "min_price"),
                    "msg": "min_price must not be greater than max_price",
                    "type": "value_error",
                }
            ]
        )

    conditions = current_deal_conditions()
    search = (q or "").strip()
    if search:
        conditions.append(Deal.title.ilike(f"%{escape_like(search)}%", escape=_LIKE_ESCAPE))
    if platform is not None:
        conditions.append(Deal.platform == platform)
    if store:
        conditions.append(Deal.store == store)
    if min_price is not None:
        conditions.append(Deal.original_price >= min_price)
    if max_price is not None:
        conditions.append(Deal.original_price <= max_price)

    total = session.scalar(select(func.count(Deal.id)).where(*conditions)) or 0
    rows = session.scalars(
        select(Deal)
        .where(*conditions)
        .order_by(*_order_by(sort, order))
        .limit(limit)
        .offset(offset)
    ).all()
    return DealListOut(
        items=[DealOut.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
