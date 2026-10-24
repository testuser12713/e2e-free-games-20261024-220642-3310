"""GET /api/stores — distinct store names of the current deals."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import StoreListOut

router = APIRouter(prefix="/api", tags=["deals"])


@router.get("/stores", response_model=StoreListOut)
def list_stores() -> StoreListOut:
    raise HTTPException(status_code=501, detail="stores list: implemented by ticket #7")
