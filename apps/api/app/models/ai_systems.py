"""AI system inventory and architecture-graph models.

An AI system is a first-class governed entity (AI Compliance Compiler spec s.8.2).
Its architecture is represented as a small relational graph:

    AISystem 1---* AISystemComponent   (nodes: models, agents, data stores, ...)
    AISystem 1---* AISystemFlow        (edges: component -> component)

Components may reference an existing Vendor row (`vendor_id`) or DataAsset row
(`data_asset_id`) so the established vendor / cross-border evaluators keep
working against the same underlying inventory.

Only facts the organization explicitly declares are stored as columns. Derived
facts (has_vendors, has_external_inference, ...) are computed by the service so
unknown facts are never silently turned into assumptions.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._common import TimestampMixin, uuid_pk
from app.models.types import GUID, JSONB


class AISystem(Base, TimestampMixin):
    __tablename__ = "ai_systems"
    __table_args__ = (
        Index("ix_ai_systems_org", "organization_id"),
        Index("ix_ai_systems_stage", "lifecycle_stage"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    business_purpose: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(255))  # None -> "owner not assigned" gap
    # Coarse archetype consumed by the applicability engine (see AISystemType).
    system_type: Mapped[str] = mapped_column(String(40), default="OTHER")
    risk_domain: Mapped[str | None] = mapped_column(String(120))  # e.g. "customer_support", "credit"
    lifecycle_stage: Mapped[str] = mapped_column(String(40), default="DEVELOPMENT")
    review_status: Mapped[str] = mapped_column(String(40), default="NOT_REVIEWED")
    # Sector this system operates in. Drives sector-scoped packs (e.g. "bfsi" -> RBI).
    sector: Mapped[str] = mapped_column(String(60), default="general")
    # Operating regions (ISO-ish tags, e.g. ["India", "us"]). JSON list.
    regions: Mapped[list | None] = mapped_column(JSONB)
    deployment_environment: Mapped[str | None] = mapped_column(String(80))  # production / staging / ...
    # Explicitly declared facts (never inferred). Used by the applicability engine.
    processes_personal_data: Mapped[bool] = mapped_column(Boolean, default=False)
    makes_automated_decisions: Mapped[bool] = mapped_column(Boolean, default=False)
    high_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    components: Mapped[list["AISystemComponent"]] = relationship(
        back_populates="system", cascade="all, delete-orphan"
    )
    flows: Mapped[list["AISystemFlow"]] = relationship(
        back_populates="system", cascade="all, delete-orphan"
    )


class AISystemComponent(Base, TimestampMixin):
    """A node in an AI system's architecture graph (model, data store, vendor, ...)."""

    __tablename__ = "ai_system_components"
    __table_args__ = (
        Index("ix_ai_components_system", "ai_system_id"),
        Index("ix_ai_components_type", "component_type"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    ai_system_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("ai_systems.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    component_type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(255))  # e.g. "external_llm", "self_hosted"
    region: Mapped[str | None] = mapped_column(String(80))  # e.g. "India", "us"
    # True when the component is operated outside the organization's boundary
    # (external LLM API, third-party analytics, ...). Drives residency review.
    external: Mapped[bool] = mapped_column(Boolean, default=False)
    # Optional links into the existing inventory so vendor/asset evaluators reuse data.
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("vendors.id", ondelete="SET NULL")
    )
    data_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("data_assets.id", ondelete="SET NULL")
    )
    # Personal-data categories this component handles (JSON list of strings).
    data_categories: Mapped[list | None] = mapped_column(JSONB)
    # Freeform structured config (model version, parameters, agent tools, ...).
    config: Mapped[dict | None] = mapped_column(JSONB)

    system: Mapped[AISystem] = relationship(back_populates="components")


class AISystemFlow(Base, TimestampMixin):
    """A directed edge between two components of an AI system's architecture."""

    __tablename__ = "ai_system_flows"
    __table_args__ = (
        Index("ix_ai_flows_system", "ai_system_id"),
        Index("ix_ai_flows_source", "source_component_id"),
        Index("ix_ai_flows_target", "target_component_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    ai_system_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("ai_systems.id", ondelete="CASCADE"), nullable=False
    )
    source_component_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("ai_system_components.id", ondelete="CASCADE")
    )
    target_component_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("ai_system_components.id", ondelete="CASCADE")
    )
    relation: Mapped[str] = mapped_column(String(40), default="SENDS_TO")
    purpose: Mapped[str | None] = mapped_column(Text)
    data_categories: Mapped[list | None] = mapped_column(JSONB)
    contains_personal_data: Mapped[bool] = mapped_column(Boolean, default=False)
    cross_border: Mapped[bool] = mapped_column(Boolean, default=False)

    system: Mapped[AISystem] = relationship(back_populates="flows")
