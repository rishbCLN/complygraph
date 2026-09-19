"""Common SQLAlchemy column helpers and mixins."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.types import GUID


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(GUID(), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
