"""Custom regulatory pack authoring (org-scoped frameworks)

Adds regulations.organization_id + regulations.created_by so a tenant can author
its own regulatory framework/pack without it leaking to other tenants. A NULL
organization_id continues to denote a system/shipped regulation visible to all.

Revision ID: 0008_custom_packs
Revises: 0007_control_mappings
Create Date: 2026-09-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID

revision = "0008_custom_packs"
down_revision = "0007_control_mappings"
branch_labels = None
depends_on = None


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
    if not _has_column("regulations", "organization_id"):
        op.add_column("regulations", sa.Column("organization_id", GUID(), nullable=True))
    if not _has_column("regulations", "created_by"):
        op.add_column("regulations", sa.Column("created_by", GUID(), nullable=True))
    if not _has_index("regulations", "ix_regulations_organization_id"):
        op.create_index(
            "ix_regulations_organization_id", "regulations", ["organization_id"]
        )


def downgrade() -> None:
    if _has_index("regulations", "ix_regulations_organization_id"):
        op.drop_index("ix_regulations_organization_id", table_name="regulations")
    if _has_column("regulations", "created_by"):
        op.drop_column("regulations", "created_by")
    if _has_column("regulations", "organization_id"):
        op.drop_column("regulations", "organization_id")
