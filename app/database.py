"""Database setup and SQLAlchemy session management."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Base class for application models."""


def build_engine(database_url: str) -> Engine:
    """Create an engine with SQLite-friendly connection settings."""
    connect_args: dict[str, object] = {}
    engine_options: dict[str, object] = {}

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            engine_options["poolclass"] = StaticPool

    return create_engine(
        database_url,
        connect_args=connect_args,
        **engine_options,
    )


def build_session_factory(engine: Engine) -> sessionmaker:
    """Return a factory for short-lived database sessions."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
