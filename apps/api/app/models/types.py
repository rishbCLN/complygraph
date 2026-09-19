"""Portable SQLAlchemy column types.

ComplyGraph targets PostgreSQL in production (Docker) but must also run locally
with zero external services. These types compile to native PostgreSQL types
(UUID, JSONB) and to SQLite-compatible types (CHAR(32), JSON) transparently so
the same models and migrations work in both environments.
"""

from __future__ import annotations

import uuid

from sqlalchemy import CHAR, JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class GUID(TypeDecorator):
    """Platform-independent UUID type.

    Uses PostgreSQL's UUID type when available, otherwise stores as a 32-char hex
    string. Always returns uuid.UUID instances from the database.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):  # noqa: ANN001, ANN201
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):  # noqa: ANN001, ANN201
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        if isinstance(value, uuid.UUID):
            return value.hex
        return uuid.UUID(str(value)).hex

    def process_result_value(self, value, dialect):  # noqa: ANN001, ANN201
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class JSONB(TypeDecorator):
    """JSONB on PostgreSQL, generic JSON elsewhere."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):  # noqa: ANN001, ANN201
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())
        return dialect.type_descriptor(JSON())
