"""GET /api/sources/status — result of the last run per source."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import scheduler
from app.db import get_session
from app.models import SourceState
from app.schemas import SourceStatusListOut, SourceStatusOut

router = APIRouter(prefix="/api", tags=["sources"])


@router.get("/sources/status", response_model=SourceStatusListOut)
def sources_status(session: Session = Depends(get_session)) -> SourceStatusListOut:
    rows = session.scalars(select(SourceState).order_by(SourceState.name)).all()
    items = [SourceStatusOut.model_validate(row) for row in rows]
    successes = [item.last_success_at for item in items if item.last_success_at is not None]
    return SourceStatusListOut(
        items=items,
        last_updated_at=max(successes) if successes else None,
        running=scheduler.is_running(),
    )
