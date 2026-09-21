"""Consent management models (feature #8).

DPDP centres on consent: it must be free, specific, informed, and as easy to
withdraw as to give. This module models three things:

  * ConsentPurpose  - the catalogue of purposes an organisation processes personal
                      data for (optionally linked to a ProcessingActivity), each
                      with its lawful basis and whether consent is required.
  * ConsentNotice   - versioned notice text shown in the Privacy Center. Publishing
                      a new version supersedes the previous one; old versions are
                      retained so a consent event can point at the exact notice the
                      principal saw.
  * ConsentRecord   - the *current* consent state for one (principal, purpose) pair.
  * ConsentEvent    - an append-only ledger row for every grant / withdrawal /
                      renewal / expiry, capturing method, source and the notice
                      version in force. The ledger is the audit source of truth;
                      ConsentRecord is a materialised current-state view of it.

The data principal is identified only by a self-provided identifier (usually an
email). No raw personal data beyond that identifier is stored here.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._common import TimestampMixin, uuid_pk
from app.models.types import GUID


class ConsentPurpose(Base, TimestampMixin):
    __tablename__ = "consent_purposes"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_consent_purpose_code"),
        Index("ix_consent_purposes_org", "organization_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    processing_activity_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("processing_activities.id", ondelete="SET NULL")
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)  # stable per-org key
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    lawful_basis: Mapped[str] = mapped_column(String(120), default="Consent")
    # If consent is not required (e.g. legitimate use / legal obligation) the purpose
    # is still shown for transparency but cannot be withdrawn in the portal.
    requires_consent: Mapped[bool] = mapped_column(Boolean, default=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    # Optional consent lifetime; None = no automatic expiry.
    default_expiry_days: Mapped[int | None] = mapped_column(Integer)
    display_order: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")


class ConsentNotice(Base, TimestampMixin):
    __tablename__ = "consent_notices"
    __table_args__ = (
        UniqueConstraint("organization_id", "version", name="uq_consent_notice_version"),
        Index("ix_consent_notices_org", "organization_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[uuid.UUID | None] = mapped_column(GUID())


class ConsentRecord(Base, TimestampMixin):
    """Current consent state for one (principal, purpose) pair (materialised view)."""

    __tablename__ = "consent_records"
    __table_args__ = (
        UniqueConstraint("purpose_id", "principal_identifier", name="uq_consent_record"),
        Index("ix_consent_records_org", "organization_id"),
        Index("ix_consent_records_principal", "principal_identifier"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    purpose_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("consent_purposes.id", ondelete="CASCADE"), nullable=False
    )
    principal_identifier: Mapped[str] = mapped_column(String(320), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="GRANTED")
    method: Mapped[str] = mapped_column(String(30), default="PRIVACY_CENTER")
    notice_version: Mapped[int | None] = mapped_column(Integer)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Provenance flag: portal submissions are self-asserted (identity not strongly
    # verified) until an operator confirms; staff-recorded entries are verified.
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class ConsentEvent(Base):
    """Append-only ledger. Never updated or deleted; the audit source of truth."""

    __tablename__ = "consent_events"
    __table_args__ = (
        Index("ix_consent_events_org", "organization_id"),
        Index("ix_consent_events_principal", "principal_identifier"),
        Index("ix_consent_events_purpose", "purpose_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    purpose_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("consent_purposes.id", ondelete="SET NULL")
    )
    purpose_code: Mapped[str] = mapped_column(String(80), nullable=False)  # denormalised
    purpose_name: Mapped[str] = mapped_column(String(255), nullable=False)  # denormalised
    principal_identifier: Mapped[str] = mapped_column(String(320), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    method: Mapped[str] = mapped_column(String(30), nullable=False)
    source: Mapped[str] = mapped_column(String(60), default="PRIVACY_CENTER")
    notice_version: Mapped[int | None] = mapped_column(Integer)
    actor: Mapped[str | None] = mapped_column(String(320))  # staff user id/email if applicable
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
