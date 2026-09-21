"""DSR fulfillment models (feature #7).

Fulfilling a data-subject request means locating the principal's personal data
across the catalogued datastores (data assets), executing the requested action
(collect for ACCESS/PORTABILITY, delete for ERASURE) against each store through a
connector adapter, and packaging the outcome.

A DSRTask is one per-datastore execution step for a request, so the workflow is
auditable store-by-store: which asset, what was found, what action ran, and
whether it succeeded. The assembled package is stored on the request itself.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._common import TimestampMixin, uuid_pk
from app.models.types import GUID, JSONB


class DSRTask(Base, TimestampMixin):
    __tablename__ = "dsr_tasks"
    __table_args__ = (
        Index("ix_dsr_tasks_request", "request_id"),
        Index("ix_dsr_tasks_status", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    request_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("data_subject_requests.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("data_assets.id", ondelete="SET NULL")
    )
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_type: Mapped[str | None] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(40), nullable=False)  # COLLECT | ERASE
    status: Mapped[str] = mapped_column(String(40), default="PENDING")  # PENDING|COMPLETED|FAILED|SKIPPED
    # PII fields located in this asset (names + categories), never raw values.
    matched_fields: Mapped[dict | None] = mapped_column(JSONB)
    records_affected: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(Text)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
