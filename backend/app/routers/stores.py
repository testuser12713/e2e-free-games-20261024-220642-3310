"""GET /api/stores — distinct store names of the current deals."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Deal
from app.routers.deals import current_deal_conditions
from app.schemas import StoreListOut

router = APIRouter(prefix="/api", tags=["deals"])


@router.get("/stores", response_model=StoreListOut)
def list_stores(session: Session = Depends(get_session)) -> StoreListOut:
    names = session.scalars(
        select(Deal.store).where(*current_deal_conditions()).distinct().order_by(Deal.store)
    ).all()
    return StoreListOut(items=[name for name in names if name])
