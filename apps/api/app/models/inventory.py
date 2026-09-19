"""Data inventory models: connectors, assets, fields, flows, vendors, processing activities."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._common import TimestampMixin, uuid_pk
from app.models.types import GUID


class Connector(Base, TimestampMixin):
    __tablename__ = "connectors"
    __table_args__ = (Index("ix_connectors_org", "organization_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="CONFIGURED")
    configuration_encrypted: Mapped[str | None] = mapped_column(Text)
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assets: Mapped[list["DataAsset"]] = relationship(back_populates="connector")


class DataAsset(Base, TimestampMixin):
    __tablename__ = "data_assets"
    __table_args__ = (
        Index("ix_assets_org", "organization_id"),
        Index("ix_assets_type", "asset_type"),
        Index("ix_assets_fingerprint", "fingerprint"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    connector_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("connectors.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    asset_type: Mapped[str] = mapped_column(String(40), nullable=False)
    system_name: Mapped[str | None] = mapped_column(String(255))
    environment: Mapped[str | None] = mapped_column(String(80))
    classification: Mapped[str] = mapped_column(String(60), default="UNKNOWN")
    sensitivity_level: Mapped[int] = mapped_column(Integer, default=1)
    owner: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    row_count: Mapped[int | None] = mapped_column(Integer)
    fingerprint: Mapped[str | None] = mapped_column(String(80))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    connector: Mapped[Connector | None] = relationship(back_populates="assets")
    fields: Mapped[list["AssetField"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )


class AssetField(Base, TimestampMixin):
    __tablename__ = "asset_fields"
    __table_args__ = (
        Index("ix_fields_asset", "asset_id"),
        Index("ix_fields_fingerprint", "fingerprint"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    asset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("data_assets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str | None] = mapped_column(String(80))
    classification: Mapped[str] = mapped_column(String(60), default="UNKNOWN")
    category: Mapped[str] = mapped_column(String(60), default="UNKNOWN")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_band: Mapped[str] = mapped_column(String(20), default="LOW")
    detection_method: Mapped[str | None] = mapped_column(String(120))
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    sensitive_count: Mapped[int] = mapped_column(Integer, default=0)
    masked_examples: Mapped[str | None] = mapped_column(Text)  # comma-joined masked samples
    fingerprint: Mapped[str | None] = mapped_column(String(80))

    asset: Mapped[DataAsset] = relationship(back_populates="fields")


class Vendor(Base, TimestampMixin):
    __tablename__ = "vendors"
    __table_args__ = (Index("ix_vendors_org", "organization_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    service_type: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str | None] = mapped_column(String(80))
    data_processing: Mapped[str | None] = mapped_column(Text)
    contract_status: Mapped[str] = mapped_column(String(60), default="UNKNOWN")
    risk_level: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    owner: Mapped[str | None] = mapped_column(String(255))


class ProcessingActivity(Base, TimestampMixin):
    __tablename__ = "processing_activities"
    __table_args__ = (Index("ix_activities_org", "organization_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    lawful_basis: Mapped[str | None] = mapped_column(String(120))
    owner: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(60), default="ACTIVE")
    retention_period_days: Mapped[int | None] = mapped_column(Integer)
    has_notice: Mapped[bool] = mapped_column(Boolean, default=False)
    has_consent: Mapped[bool] = mapped_column(Boolean, default=False)


class ClassificationOverride(Base, TimestampMixin):
    """Analyst feedback that overrides the automatic classifier for a field.

    Matching is by normalized field name, optionally scoped to a specific asset
    (by logical name). Applied during scans so confirmed/corrected classifications
    persist across re-scans, forming the classifier feedback loop.
    """

    __tablename__ = "classification_overrides"
    __table_args__ = (
        Index("ix_overrides_org", "organization_id"),
        Index("ix_overrides_field", "field_name"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_name: Mapped[str | None] = mapped_column(String(255))  # None = applies org-wide
    classification: Mapped[str] = mapped_column(String(60), nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="UNKNOWN")
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID())


class DataFlow(Base, TimestampMixin):
    __tablename__ = "data_flows"
    __table_args__ = (
        Index("ix_flows_org", "organization_id"),
        Index("ix_flows_source", "source_asset_id"),
        Index("ix_flows_dest", "destination_asset_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    source_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("data_assets.id", ondelete="CASCADE")
    )
    destination_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("data_assets.id", ondelete="CASCADE")
    )
    flow_type: Mapped[str] = mapped_column(String(40), default="INTERNAL")
    purpose: Mapped[str | None] = mapped_column(Text)
    contains_personal_data: Mapped[bool] = mapped_column(Boolean, default=False)
    contains_sensitive_category: Mapped[bool] = mapped_column(Boolean, default=False)
    cross_border: Mapped[bool] = mapped_column(Boolean, default=False)
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("vendors.id", ondelete="SET NULL")
    )
    discovered: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE")
    categories: Mapped[str | None] = mapped_column(Text)  # comma-joined data categories
