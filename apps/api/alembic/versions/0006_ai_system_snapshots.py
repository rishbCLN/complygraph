"""AI system analysis snapshots (change-impact history)

Adds ai_system_snapshots so each on-demand analysis of an AI system records the
per-control status map + derived facts at that point in time. Diffing the two
most recent snapshots produces the change-impact view (newly failing, resolved,
regressed controls) on re-analysis.

Revision ID: 0006_ai_system_snapshots
Revises: 0005_finding_ai_system
Create Date: 2026-09-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID, JSONB

revision = "0006_ai_system_snapshots"
down_revision = "0005_finding_ai_system"
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
    if not _has_table("ai_system_snapshots"):
        op.create_table(
            "ai_system_snapshots",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column(
                "ai_system_id",
                GUID(),
                sa.ForeignKey("ai_systems.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "organization_id",
                GUID(),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("assessment_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("control_statuses", JSONB(), nullable=True),
            sa.Column("facts", JSONB(), nullable=True),
            sa.Column("summary", JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_index("ai_system_snapshots", "ix_ai_snapshots_system"):
        op.create_index(
            "ix_ai_snapshots_system", "ai_system_snapshots", ["ai_system_id"]
        )
    if not _has_index("ai_system_snapshots", "ix_ai_snapshots_system_created"):
        op.create_index(
            "ix_ai_snapshots_system_created",
            "ai_system_snapshots",
            ["ai_system_id", "created_at"],
        )


def downgrade() -> None:
    if _has_index("ai_system_snapshots", "ix_ai_snapshots_system_created"):
        op.drop_index("ix_ai_snapshots_system_created", table_name="ai_system_snapshots")
    if _has_index("ai_system_snapshots", "ix_ai_snapshots_system"):
        op.drop_index("ix_ai_snapshots_system", table_name="ai_system_snapshots")
    if _has_table("ai_system_snapshots"):
        op.drop_table("ai_system_snapshots")
