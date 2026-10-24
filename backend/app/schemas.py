"""Pydantic response models of the HTTP API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class DealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    store: str
    platform: Literal["pc", "ps5"]
    original_price: float
    currency: str
    url: str
    image_url: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    first_seen_at: datetime
    last_seen_at: datetime


class DealListOut(BaseModel):
    items: list[DealOut]
    total: int
    limit: int
    offset: int


class SourceStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    last_run_at: datetime | None = None
    ok: bool | None = None
    error: str | None = None
    deal_count: int = 0
    last_success_at: datetime | None = None


class SourceStatusListOut(BaseModel):
    items: list[SourceStatusOut]
    last_updated_at: datetime | None = None
    running: bool


class StoreListOut(BaseModel):
    items: list[str]


class HealthOut(BaseModel):
    status: Literal["ok"]


class RefreshStartedOut(BaseModel):
    status: Literal["started"]


class ErrorInfo(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorBody(BaseModel):
    """Uniform body of every non-2xx response."""

    error: ErrorInfo
