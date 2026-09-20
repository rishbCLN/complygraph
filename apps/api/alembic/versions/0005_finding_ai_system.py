"""Attribute findings to AI systems

Adds findings.ai_system_id so AI-scoped findings (RBI/CERT-In/MeitY controls
evaluated against an AI system) can be attributed to the specific system, which
powers per-system analysis and the change-impact view.

Revision ID: 0005_finding_ai_system
Revises: 0004_ai_systems
Create Date: 2026-09-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID

revision = "0005_finding_ai_system"
down_revision = "0004_ai_systems"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return column in {c["name"] for c in insp.get_columns(table)}


def _has_index(table: str, index: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return index in {ix["name"] for ix in insp.get_indexes(table)}


def upgrade() -> None:
    if not _has_column("findings", "ai_system_id"):
        op.add_column(
            "findings",
            sa.Column(
                "ai_system_id",
                GUID(),
                sa.ForeignKey("ai_systems.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if not _has_index("findings", "ix_findings_ai_system"):
        op.create_index("ix_findings_ai_system", "findings", ["ai_system_id"])


def downgrade() -> None:
    if _has_index("findings", "ix_findings_ai_system"):
        op.drop_index("ix_findings_ai_system", table_name="findings")
    if _has_column("findings", "ai_system_id"):
        if op.get_bind().dialect.name == "sqlite":
            # SQLite cannot DROP a column referenced by a FK via plain ALTER;
            # recreate="always" forces the copy-and-move rebuild so the FK on
            # ai_system_id does not trip the "ALTER of constraints" limitation.
            with op.batch_alter_table("findings", recreate="always") as batch:
                batch.drop_column("ai_system_id")
        else:
            op.drop_column("findings", "ai_system_id")
