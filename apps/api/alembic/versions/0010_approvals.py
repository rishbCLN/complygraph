"""Approval requests (maker-checker workflow, feature #4)

Adds approval_requests: a proposed change to an entity (finding resolution,
risk acceptance, control assessment sign-off) that a *different* user must
approve before it is applied.

Revision ID: 0010_approvals
Revises: 0009_risks
Create Date: 2026-09-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID, JSONB

revision = "0010_approvals"
down_revision = "0009_risks"
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
    insp = sa.inspect(op.get_bind())
    if "control_assessments" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("control_assessments")}
        if "approved_by" not in cols:
            op.add_column("control_assessments", sa.Column("approved_by", GUID(), nullable=True))
        if "approved_at" not in cols:
            op.add_column(
                "control_assessments", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True)
            )

    if not _has_table("approval_requests"):
        op.create_table(
            "approval_requests",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column("organization_id", GUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("entity_type", sa.String(length=40), nullable=False),
            sa.Column("entity_id", GUID(), nullable=False),
            sa.Column("action", sa.String(length=60), nullable=False),
            sa.Column("payload", JSONB(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
            sa.Column("submitted_by", GUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("reviewed_by", GUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("review_note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    for name, cols in (
        ("ix_approvals_org", ["organization_id"]),
        ("ix_approvals_status", ["status"]),
        ("ix_approvals_entity", ["entity_type", "entity_id"]),
    ):
        if not _has_index("approval_requests", name):
            op.create_index(name, "approval_requests", cols)


def downgrade() -> None:
    for name in ("ix_approvals_entity", "ix_approvals_status", "ix_approvals_org"):
        if _has_index("approval_requests", name):
            op.drop_index(name, table_name="approval_requests")
    if _has_table("approval_requests"):
        op.drop_table("approval_requests")
    insp = sa.inspect(op.get_bind())
    if "control_assessments" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("control_assessments")}
        if "approved_at" in cols:
            op.drop_column("control_assessments", "approved_at")
        if "approved_by" in cols:
            op.drop_column("control_assessments", "approved_by")
