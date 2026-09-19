"""Findings, remediation tasks, scans, and scan results."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._common import TimestampMixin, uuid_pk
from app.models.types import GUID, JSONB


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"
    __table_args__ = (
        Index("ix_findings_org", "organization_id"),
        Index("ix_findings_status", "status"),
        Index("ix_findings_severity", "severity"),
        Index("ix_findings_control", "control_id"),
        Index("ix_findings_fingerprint", "fingerprint"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("controls.id", ondelete="SET NULL")
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("data_assets.id", ondelete="SET NULL")
    )
    data_flow_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("data_flows.id", ondelete="SET NULL")
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("vendors.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_breakdown: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(40), default="OPEN")
    source: Mapped[str | None] = mapped_column(String(120))
    fingerprint: Mapped[str | None] = mapped_column(String(80))
    data_categories: Mapped[str | None] = mapped_column(Text)
    recommended_actions: Mapped[dict | None] = mapped_column(JSONB)
    evidence_refs: Mapped[dict | None] = mapped_column(JSONB)
    owner: Mapped[str | None] = mapped_column(String(255))
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    resolution_note: Mapped[str | None] = mapped_column(Text)
    detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(GUID())


class RemediationTask(Base, TimestampMixin):
    __tablename__ = "remediation_tasks"
    __table_args__ = (
        Index("ix_tasks_org", "organization_id"),
        Index("ix_tasks_finding", "finding_id"),
        Index("ix_tasks_status", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    finding_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("findings.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(40), default="TODO")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Scan(Base):
    __tablename__ = "scans"
    __table_args__ = (
        Index("ix_scans_org", "organization_id"),
        Index("ix_scans_connector", "connector_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    connector_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("connectors.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(40), default="QUEUED")
    stage: Mapped[str | None] = mapped_column(String(80))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    items_scanned: Mapped[int] = mapped_column(Integer, default=0)
    findings_created: Mapped[int] = mapped_column(Integer, default=0)
    changes: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScanResult(Base):
    __tablename__ = "scan_results"
    __table_args__ = (Index("ix_scanresults_scan", "scan_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    scan_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    field_name: Mapped[str | None] = mapped_column(String(255))
    result_type: Mapped[str | None] = mapped_column(String(80))
    classification: Mapped[str | None] = mapped_column(String(60))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[str | None] = mapped_column(Text)  # redacted detection evidence only
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
