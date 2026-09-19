"""Identity, tenancy, and audit models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._common import TimestampMixin, uuid_pk
from app.models.types import GUID, JSONB


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    industry: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80), default="India")
    plan: Mapped[str] = mapped_column(String(40), default="GROWTH")
    assessment_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        Index("ix_memberships_org", "organization_id"),
        Index("ix_memberships_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    organization: Mapped[Organization] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user", "user_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_org_created", "organization_id", "created_at"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    audit_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
