"""Notifications / reminders (feature #6)

Adds the in-app notification store used by the reminder engine and scheduled
re-assessment.

Revision ID: 0014_notifications
Revises: 0013_consent
Create Date: 2026-09-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID

revision = "0014_notifications"
down_revision = "0013_consent"
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
    if not _has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column(
                "organization_id", GUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("user_id", GUID(), nullable=True),
            sa.Column("kind", sa.String(length=40), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False, server_default="INFO"),
            sa.Column("state", sa.String(length=20), nullable=False, server_default="UNREAD"),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.Text(), nullable=True),
            sa.Column("entity_type", sa.String(length=80), nullable=True),
            sa.Column("entity_id", sa.String(length=80), nullable=True),
            sa.Column("dedupe_key", sa.String(length=200), nullable=True),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    for name, cols in (
        ("ix_notifications_org", ["organization_id"]),
        ("ix_notifications_state", ["state"]),
        ("ix_notifications_dedupe", ["organization_id", "dedupe_key"]),
    ):
        if not _has_index("notifications", name):
            op.create_index(name, "notifications", cols)


def downgrade() -> None:
    for name in ("ix_notifications_dedupe", "ix_notifications_state", "ix_notifications_org"):
        if _has_index("notifications", name):
            op.drop_index(name, table_name="notifications")
    if _has_table("notifications"):
        op.drop_table("notifications")
