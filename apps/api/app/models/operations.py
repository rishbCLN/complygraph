"""Operational workflow models: data subject requests, breach incidents, AI investigations."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._common import TimestampMixin, uuid_pk
from app.models.types import GUID, JSONB


class DataSubjectRequest(Base, TimestampMixin):
    __tablename__ = "data_subject_requests"
    __table_args__ = (Index("ix_dsr_org", "organization_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    requester_identifier: Mapped[str] = mapped_column(String(320), nullable=False)
    request_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="REQUESTED")
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(GUID())
    verification_status: Mapped[str] = mapped_column(String(40), default="PENDING")
    notes: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BreachIncident(Base, TimestampMixin):
    __tablename__ = "breach_incidents"
    __table_args__ = (Index("ix_breach_org", "organization_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    affected_assets: Mapped[dict | None] = mapped_column(JSONB)
    affected_records_estimate: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40), default="DETECTED")
    board_notification_status: Mapped[str] = mapped_column(String(40), default="PENDING")
    principal_notification_status: Mapped[str] = mapped_column(String(40), default="PENDING")
    root_cause: Mapped[str | None] = mapped_column(Text)
    remediation: Mapped[str | None] = mapped_column(Text)
    timeline: Mapped[dict | None] = mapped_column(JSONB)


class AIInvestigation(Base):
    __tablename__ = "ai_investigations"
    __table_args__ = (
        Index("ix_ai_org", "organization_id"),
        Index("ix_ai_finding", "finding_id"),
        Index("ix_ai_hash", "input_hash"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    finding_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("findings.id", ondelete="CASCADE")
    )
    input_hash: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str | None] = mapped_column(String(120))
    mode: Mapped[str] = mapped_column(String(40), default="deterministic")
    status: Mapped[str] = mapped_column(String(40), default="PENDING")
    summary: Mapped[str | None] = mapped_column(Text)
    root_causes: Mapped[dict | None] = mapped_column(JSONB)
    recommendations: Mapped[dict | None] = mapped_column(JSONB)
    missing_evidence: Mapped[dict | None] = mapped_column(JSONB)
    legal_review_required: Mapped[bool] = mapped_column(Boolean, default=True)
    uncertainty: Mapped[str | None] = mapped_column(Text)
    evidence_considered: Mapped[dict | None] = mapped_column(JSONB)
    raw_response_redacted: Mapped[str | None] = mapped_column(Text)
    input_sanitized: Mapped[bool] = mapped_column(Boolean, default=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
