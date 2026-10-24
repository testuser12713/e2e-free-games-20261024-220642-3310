"""GET /api/deals — searchable, filterable, sortable list of current free deals."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.schemas import DealListOut

router = APIRouter(prefix="/api", tags=["deals"])

SortKey = Literal["title", "original_price", "ends_at", "first_seen"]


@router.get("/deals", response_model=DealListOut)
def list_deals(
    q: str | None = Query(default=None, max_length=200),
    platform: Literal["pc", "ps5"] | None = None,
    store: str | None = Query(default=None, max_length=128),
    sort: SortKey = "first_seen",
    order: Literal["asc", "desc"] = "desc",
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> DealListOut:
    raise HTTPException(status_code=501, detail="deals list: implemented by ticket #7")
