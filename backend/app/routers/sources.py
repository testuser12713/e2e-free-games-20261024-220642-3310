"""GET /api/sources/status — result of the last run per source."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import SourceStatusListOut

router = APIRouter(prefix="/api", tags=["sources"])


@router.get("/sources/status", response_model=SourceStatusListOut)
def sources_status() -> SourceStatusListOut:
    raise HTTPException(status_code=501, detail="source status: implemented by ticket #12")
