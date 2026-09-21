"""Consent management (feature #8)

Adds the consent purpose catalogue, versioned notices, current-state consent
records, and the append-only consent event ledger.

Revision ID: 0013_consent
Revises: 0012_dsr_fulfillment
Create Date: 2026-09-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID, JSONB  # noqa: F401  (JSONB kept for parity/imports)

revision = "0013_consent"
down_revision = "0012_dsr_fulfillment"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return table in insp.get_table_names()


def _has_index(table: str, index: str) -> bool:
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return False
    return index in {ix["name"] for ix in insp.get_indexes(table)}


def upgrade() -> None:
    if not _has_table("consent_purposes"):
        op.create_table(
            "consent_purposes",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column(
                "organization_id", GUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "processing_activity_id",
                GUID(),
                sa.ForeignKey("processing_activities.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("lawful_basis", sa.String(length=120), nullable=False, server_default="Consent"),
            sa.Column("requires_consent", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("default_expiry_days", sa.Integer(), nullable=True),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("organization_id", "code", name="uq_consent_purpose_code"),
        )
    if not _has_index("consent_purposes", "ix_consent_purposes_org"):
        op.create_index("ix_consent_purposes_org", "consent_purposes", ["organization_id"])

    if not _has_table("consent_notices"):
        op.create_table(
            "consent_notices",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column(
                "organization_id", GUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("published_by", GUID(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("organization_id", "version", name="uq_consent_notice_version"),
        )
    if not _has_index("consent_notices", "ix_consent_notices_org"):
        op.create_index("ix_consent_notices_org", "consent_notices", ["organization_id"])

    if not _has_table("consent_records"):
        op.create_table(
            "consent_records",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column(
                "organization_id", GUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "purpose_id", GUID(), sa.ForeignKey("consent_purposes.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("principal_identifier", sa.String(length=320), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="GRANTED"),
            sa.Column("method", sa.String(length=30), nullable=False, server_default="PRIVACY_CENTER"),
            sa.Column("notice_version", sa.Integer(), nullable=True),
            sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("purpose_id", "principal_identifier", name="uq_consent_record"),
        )
    for name, cols in (
        ("ix_consent_records_org", ["organization_id"]),
        ("ix_consent_records_principal", ["principal_identifier"]),
    ):
        if not _has_index("consent_records", name):
            op.create_index(name, "consent_records", cols)

    if not _has_table("consent_events"):
        op.create_table(
            "consent_events",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column(
                "organization_id", GUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "purpose_id", GUID(), sa.ForeignKey("consent_purposes.id", ondelete="SET NULL"), nullable=True
            ),
            sa.Column("purpose_code", sa.String(length=80), nullable=False),
            sa.Column("purpose_name", sa.String(length=255), nullable=False),
            sa.Column("principal_identifier", sa.String(length=320), nullable=False),
            sa.Column("event_type", sa.String(length=20), nullable=False),
            sa.Column("method", sa.String(length=30), nullable=False),
            sa.Column("source", sa.String(length=60), nullable=False, server_default="PRIVACY_CENTER"),
            sa.Column("notice_version", sa.Integer(), nullable=True),
            sa.Column("actor", sa.String(length=320), nullable=True),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    for name, cols in (
        ("ix_consent_events_org", ["organization_id"]),
        ("ix_consent_events_principal", ["principal_identifier"]),
        ("ix_consent_events_purpose", ["purpose_id"]),
    ):
        if not _has_index("consent_events", name):
            op.create_index(name, "consent_events", cols)


def downgrade() -> None:
    for name in ("ix_consent_events_purpose", "ix_consent_events_principal", "ix_consent_events_org"):
        if _has_index("consent_events", name):
            op.drop_index(name, table_name="consent_events")
    if _has_table("consent_events"):
        op.drop_table("consent_events")

    for name in ("ix_consent_records_principal", "ix_consent_records_org"):
        if _has_index("consent_records", name):
            op.drop_index(name, table_name="consent_records")
    if _has_table("consent_records"):
        op.drop_table("consent_records")

    if _has_index("consent_notices", "ix_consent_notices_org"):
        op.drop_index("ix_consent_notices_org", table_name="consent_notices")
    if _has_table("consent_notices"):
        op.drop_table("consent_notices")

    if _has_index("consent_purposes", "ix_consent_purposes_org"):
        op.drop_index("ix_consent_purposes_org", table_name="consent_purposes")
    if _has_table("consent_purposes"):
        op.drop_table("consent_purposes")
