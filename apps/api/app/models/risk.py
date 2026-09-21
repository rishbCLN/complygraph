"""Risk management models: the risk register.

A Risk is a register entry with inherent and residual scoring (likelihood x
impact), an optional quantitative view (single-loss expectancy x annual rate of
occurrence => annualised loss expectancy) and business-impact-analysis fields
(RTO/RPO/MTD). It can link to the finding, control, vendor, AI system or
processing activity it concerns. Risk acceptance is captured with an explicit
rationale, approver and review-expiry so an accepted risk cannot silently
persist forever.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._common import TimestampMixin, uuid_pk
from app.models.types import GUID


class Risk(Base, TimestampMixin):
    __tablename__ = "risks"
    __table_args__ = (
        Index("ix_risks_org", "organization_id"),
        Index("ix_risks_status", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40), default="COMPLIANCE")
    status: Mapped[str] = mapped_column(String(40), default="IDENTIFIED")
    owner: Mapped[str | None] = mapped_column(String(255))

    # Qualitative scoring (1..5 each). Inherent = before controls, residual = after.
    inherent_likelihood: Mapped[int] = mapped_column(Integer, default=3)
    inherent_impact: Mapped[int] = mapped_column(Integer, default=3)
    residual_likelihood: Mapped[int] = mapped_column(Integer, default=3)
    residual_impact: Mapped[int] = mapped_column(Integer, default=3)

    # Treatment.
    treatment_strategy: Mapped[str] = mapped_column(String(40), default="MITIGATE")
    treatment_plan: Mapped[str | None] = mapped_column(Text)

    # Quantitative view (optional, monetary). ALE is derived (sle * aro).
    single_loss_expectancy: Mapped[float | None] = mapped_column(Float)
    annual_rate_of_occurrence: Mapped[float | None] = mapped_column(Float)

    # Business Impact Analysis (optional).
    rto_hours: Mapped[int | None] = mapped_column(Integer)  # recovery time objective
    rpo_hours: Mapped[int | None] = mapped_column(Integer)  # recovery point objective
    max_tolerable_downtime_hours: Mapped[int | None] = mapped_column(Integer)
    business_impact: Mapped[str | None] = mapped_column(Text)

    # Acceptance workflow.
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acceptance_rationale: Mapped[str | None] = mapped_column(Text)
    acceptance_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Optional links to what the risk concerns.
    control_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("controls.id", ondelete="SET NULL"))
    finding_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("findings.id", ondelete="SET NULL"))
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("vendors.id", ondelete="SET NULL"))
    ai_system_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("ai_systems.id", ondelete="SET NULL"))
    processing_activity_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("processing_activities.id", ondelete="SET NULL")
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"))
