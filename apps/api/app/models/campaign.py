"""Audit campaign models (feature #5).

An AuditCampaign is a scoped, tracked, point-in-time assessment run: pick a set
of frameworks (regulations) to assess, run every in-scope active control through
the deterministic engine, and persist each control's result as a CampaignResult.
Unlike the live control view (which always reflects "now"), a completed campaign
is an immutable record of posture at its assessment date, suitable for an audit
trail and period-over-period comparison.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._common import TimestampMixin, uuid_pk
from app.models.types import GUID, JSONB


class AuditCampaign(Base, TimestampMixin):
    __tablename__ = "audit_campaigns"
    __table_args__ = (
        Index("ix_campaigns_org", "organization_id"),
        Index("ix_campaigns_status", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # Scope: list of regulation ids (as strings). Empty/absent => all frameworks.
    scope_regulation_ids: Mapped[list | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")  # DRAFT|RUNNING|COMPLETED|ARCHIVED
    assessment_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Aggregate result: {total, applicable, by_status:{...}, coverage: float}
    summary: Mapped[dict | None] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"))


class CampaignResult(Base):
    __tablename__ = "campaign_results"
    __table_args__ = (
        Index("ix_campaign_results_campaign", "campaign_id"),
        Index("ix_campaign_results_status", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("audit_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("controls.id", ondelete="SET NULL")
    )
    control_code: Mapped[str] = mapped_column(String(80), nullable=False)
    control_title: Mapped[str | None] = mapped_column(String(255))
    regulation_name: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
