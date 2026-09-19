"""Evidence and control-evidence linkage models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._common import TimestampMixin, uuid_pk
from app.models.types import GUID


class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"
    __table_args__ = (
        Index("ix_evidence_org", "organization_id"),
        Index("ix_evidence_status", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(120))
    source_url: Mapped[str | None] = mapped_column(String(512))
    file_path: Mapped[str | None] = mapped_column(String(512))
    hash: Mapped[str | None] = mapped_column(String(80))
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), default="UNKNOWN")
    owner: Mapped[str | None] = mapped_column(String(255))


class ControlEvidence(Base):
    __tablename__ = "control_evidence"
    __table_args__ = (
        Index("ix_ce_control", "control_id"),
        Index("ix_ce_evidence", "evidence_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    control_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False
    )
    relation_type: Mapped[str] = mapped_column(String(40), default="SUPPORTS")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
