"""Regulatory framework models: regulations, obligations, controls, scopes, assessments."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._common import TimestampMixin, uuid_pk
from app.models.types import GUID


class Regulation(Base, TimestampMixin):
    __tablename__ = "regulations"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(120), default="India")
    version: Mapped[str | None] = mapped_column(String(80))
    source_document: Mapped[str | None] = mapped_column(String(512))
    source_date: Mapped[str | None] = mapped_column(String(40))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), default="IN_FORCE")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    obligations: Mapped[list["Obligation"]] = relationship(back_populates="regulation")


class Obligation(Base, TimestampMixin):
    __tablename__ = "obligations"
    __table_args__ = (Index("ix_obligations_reg", "regulation_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    regulation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    legal_reference: Mapped[str | None] = mapped_column(String(512))
    source_section: Mapped[str | None] = mapped_column(String(255))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applicability_logic: Mapped[str | None] = mapped_column(Text)

    regulation: Mapped[Regulation] = relationship(back_populates="obligations")
    controls: Mapped[list["Control"]] = relationship(back_populates="obligation")


class Control(Base, TimestampMixin):
    __tablename__ = "controls"
    __table_args__ = (Index("ix_controls_obligation", "obligation_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    obligation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), default="GENERAL")
    assessment_method: Mapped[str] = mapped_column(String(120), default="deterministic")
    evaluator_key: Mapped[str | None] = mapped_column(String(120))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    severity_default: Mapped[str] = mapped_column(String(20), default="MEDIUM")

    obligation: Mapped[Obligation] = relationship(back_populates="controls")


class ControlAssetScope(Base):
    __tablename__ = "control_asset_scopes"
    __table_args__ = (
        Index("ix_scope_control", "control_id"),
        Index("ix_scope_asset", "asset_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    control_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("data_assets.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text)
    applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ControlAssessment(Base, TimestampMixin):
    __tablename__ = "control_assessments"
    __table_args__ = (
        Index("ix_assess_org", "organization_id"),
        Index("ix_assess_control", "control_id"),
        Index("ix_assess_status", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), default="NO_EVIDENCE")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    assessment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    automated: Mapped[bool] = mapped_column(Boolean, default=True)
