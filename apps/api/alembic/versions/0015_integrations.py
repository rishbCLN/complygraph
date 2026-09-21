"""Integrations: webhooks, external tickets, MFA columns (feature #10)

Adds:
* webhook_endpoints / webhook_deliveries - outbound signed webhook delivery.
* external_tickets - local mirror of Jira/ServiceNow issues.
* users.mfa_* columns - TOTP multi-factor enrolment state.

Every table/column is guarded so the migration is idempotent and safe to run
against a partially-migrated database.

Revision ID: 0015_integrations
Revises: 0014_notifications
Create Date: 2026-09-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID

revision = "0015_integrations"
down_revision = "0014_notifications"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return table in insp.get_table_names()


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def _has_index(table: str, index: str) -> bool:
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return False
    return index in {ix["name"] for ix in insp.get_indexes(table)}


def upgrade() -> None:
    # --- webhook_endpoints -------------------------------------------------
    if not _has_table("webhook_endpoints"):
        op.create_table(
            "webhook_endpoints",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column(
                "organization_id", GUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column("url", sa.String(length=1024), nullable=False),
            sa.Column("secret_encrypted", sa.Text(), nullable=True),
            sa.Column("events", sa.JSON(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("last_status", sa.String(length=20), nullable=True),
            sa.Column("last_delivery_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not _has_index("webhook_endpoints", "ix_webhook_endpoints_org"):
        op.create_index("ix_webhook_endpoints_org", "webhook_endpoints", ["organization_id"])

    # --- webhook_deliveries ------------------------------------------------
    if not _has_table("webhook_deliveries"):
        op.create_table(
            "webhook_deliveries",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column("organization_id", GUID(), nullable=False),
            sa.Column(
                "endpoint_id", GUID(), sa.ForeignKey("webhook_endpoints.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("event", sa.String(length=60), nullable=False),
            sa.Column("event_id", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("response_code", sa.Integer(), nullable=True),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
    for name, cols in (
        ("ix_webhook_deliveries_endpoint", ["endpoint_id", "created_at"]),
        ("ix_webhook_deliveries_org", ["organization_id"]),
    ):
        if not _has_index("webhook_deliveries", name):
            op.create_index(name, "webhook_deliveries", cols)

    # --- external_tickets --------------------------------------------------
    if not _has_table("external_tickets"):
        op.create_table(
            "external_tickets",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column(
                "organization_id", GUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("entity_type", sa.String(length=40), nullable=False),
            sa.Column("entity_id", sa.String(length=64), nullable=False),
            sa.Column("external_key", sa.String(length=120), nullable=True),
            sa.Column("external_id", sa.String(length=120), nullable=True),
            sa.Column("external_url", sa.String(length=1024), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="CREATED"),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("created_by", GUID(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    for name, cols in (
        ("ix_external_tickets_org", ["organization_id"]),
        ("ix_external_tickets_entity", ["entity_type", "entity_id"]),
    ):
        if not _has_index("external_tickets", name):
            op.create_index(name, "external_tickets", cols)

    # --- users MFA columns -------------------------------------------------
    if not _has_column("users", "mfa_enabled"):
        op.add_column(
            "users", sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false())
        )
    if not _has_column("users", "mfa_secret_encrypted"):
        op.add_column("users", sa.Column("mfa_secret_encrypted", sa.String(length=512), nullable=True))
    if not _has_column("users", "mfa_backup_codes_encrypted"):
        op.add_column("users", sa.Column("mfa_backup_codes_encrypted", sa.Text(), nullable=True))
    if not _has_column("users", "mfa_enrolled_at"):
        op.add_column("users", sa.Column("mfa_enrolled_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for col in ("mfa_enrolled_at", "mfa_backup_codes_encrypted", "mfa_secret_encrypted", "mfa_enabled"):
        if _has_column("users", col):
            op.drop_column("users", col)

    for name in ("ix_external_tickets_entity", "ix_external_tickets_org"):
        if _has_index("external_tickets", name):
            op.drop_index(name, table_name="external_tickets")
    if _has_table("external_tickets"):
        op.drop_table("external_tickets")

    for name in ("ix_webhook_deliveries_org", "ix_webhook_deliveries_endpoint"):
        if _has_index("webhook_deliveries", name):
            op.drop_index(name, table_name="webhook_deliveries")
    if _has_table("webhook_deliveries"):
        op.drop_table("webhook_deliveries")

    if _has_index("webhook_endpoints", "ix_webhook_endpoints_org"):
        op.drop_index("ix_webhook_endpoints_org", table_name="webhook_endpoints")
    if _has_table("webhook_endpoints"):
        op.drop_table("webhook_endpoints")
