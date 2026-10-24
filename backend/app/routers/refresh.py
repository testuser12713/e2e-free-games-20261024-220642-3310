"""POST /api/refresh — start one scraper run in the background."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import RefreshStartedOut

router = APIRouter(prefix="/api", tags=["sources"])


@router.post("/refresh", status_code=202, response_model=RefreshStartedOut)
def refresh() -> RefreshStartedOut:
    raise HTTPException(status_code=501, detail="manual refresh: implemented by ticket #12")
