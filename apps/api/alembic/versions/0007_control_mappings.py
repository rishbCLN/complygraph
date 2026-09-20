"""Cross-framework control mappings

Adds control_mappings, the control-equivalence graph across regulatory packs.
A NULL organization_id denotes a system/knowledge-base mapping; a set
organization_id denotes a tenant-authored mapping. Evidence attached to a
source control can be surfaced for reuse against a mapped target control when
the relation asserts coverage (EQUIVALENT / SUPERSET).

Revision ID: 0007_control_mappings
Revises: 0006_ai_system_snapshots
Create Date: 2026-09-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID

revision = "0007_control_mappings"
down_revision = "0006_ai_system_snapshots"
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
    if not _has_table("control_mappings"):
        op.create_table(
            "control_mappings",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column(
                "source_control_id",
                GUID(),
                sa.ForeignKey("controls.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "target_control_id",
                GUID(),
                sa.ForeignKey("controls.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("relation_type", sa.String(length=40), nullable=False, server_default="RELATED"),
            sa.Column("rationale", sa.Text(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column(
                "organization_id",
                GUID(),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column(
                "created_by",
                GUID(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    for name, cols in (
        ("ix_mapping_source", ["source_control_id"]),
        ("ix_mapping_target", ["target_control_id"]),
        ("ix_mapping_org", ["organization_id"]),
    ):
        if not _has_index("control_mappings", name):
            op.create_index(name, "control_mappings", cols)


def downgrade() -> None:
    for name in ("ix_mapping_org", "ix_mapping_target", "ix_mapping_source"):
        if _has_index("control_mappings", name):
            op.drop_index(name, table_name="control_mappings")
    if _has_table("control_mappings"):
        op.drop_table("control_mappings")
