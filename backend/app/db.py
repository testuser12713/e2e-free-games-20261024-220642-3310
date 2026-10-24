"""Database engine, session factory and schema creation (SQLite via SQLAlchemy)."""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base of every ORM model."""


def make_engine(database_path: str) -> Engine:
    """Create a SQLite engine for ``database_path`` (no connection is opened yet)."""
    return create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )


def _ensure_parent_dir(database_path: str) -> None:
    if database_path == ":memory:":
        return
    Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)


engine: Engine = make_engine(get_settings().database_path)
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False
)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding one session per request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Create every table that does not exist yet (idempotent)."""
    # Importing the models module registers its tables on Base.metadata.
    importlib.import_module("app.models")

    # SessionLocal may have been re-bound (tests do), so create the schema
    # where sessions actually connect.
    bound = SessionLocal.kw.get("bind") or engine
    database = bound.url.database
    if database:
        _ensure_parent_dir(database)
    Base.metadata.create_all(bind=bound)
