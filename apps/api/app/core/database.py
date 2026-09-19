"""SQLAlchemy engine, session factory, and declarative base."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, mapped_column, sessionmaker

from app.core.config import settings

def _make_engine():
    url = settings.database_url
    if url.startswith("sqlite"):
        # SQLite: single-file local fallback. Allow cross-thread use for the
        # worker/eager tasks and enable a shared connection pool.
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            future=True,
        )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        future=True,
    )


engine = _make_engine()

if settings.database_url.startswith("sqlite"):
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, connection_record):  # noqa: ANN001, ANN202
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
