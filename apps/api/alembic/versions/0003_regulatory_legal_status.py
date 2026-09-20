"""regulatory legal-status + AI-compliance pack columns

Adds legal-weight and provenance columns so the regulatory library can honestly
distinguish binding law from rules, directions, frameworks and guidance, and so
requirements can carry verified/unverified citation status and applicability
scoping for the AI-system applicability engine.

  regulations: + source_url, pack, pack_version, legal_status
  obligations: + source_url, legal_status, citation_status
  controls:    + applies_to (JSON)

Revision ID: 0003_regulatory_legal_status
Revises: 0002_scan_error_type
Create Date: 2026-09-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.types import JSONB

revision = "0003_regulatory_legal_status"
down_revision = "0002_scan_error_type"
branch_labels = None
depends_on = None


def _existing_columns(table: str) -> set[str]:
    """Column names already present on the table.

    The 0001 baseline builds the schema from live metadata (create_all), so on a
    fresh database these columns already exist. Guarding each add/drop keeps the
    migration safe on both a fresh baseline and a genuine historical upgrade.
    """
    inspector = sa.inspect(op.get_bind())
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    reg_cols = _existing_columns("regulations")
    with op.batch_alter_table("regulations") as batch:
        if "source_url" not in reg_cols:
            batch.add_column(sa.Column("source_url", sa.String(length=1024), nullable=True))
        if "pack" not in reg_cols:
            batch.add_column(sa.Column("pack", sa.String(length=80), nullable=True))
        if "pack_version" not in reg_cols:
            batch.add_column(sa.Column("pack_version", sa.String(length=40), nullable=True))
        if "legal_status" not in reg_cols:
            batch.add_column(
                sa.Column(
                    "legal_status",
                    sa.String(length=40),
                    nullable=False,
                    server_default="BINDING_LAW",
                )
            )

    obl_cols = _existing_columns("obligations")
    with op.batch_alter_table("obligations") as batch:
        if "source_url" not in obl_cols:
            batch.add_column(sa.Column("source_url", sa.String(length=1024), nullable=True))
        if "legal_status" not in obl_cols:
            batch.add_column(
                sa.Column(
                    "legal_status",
                    sa.String(length=40),
                    nullable=False,
                    server_default="BINDING_LAW",
                )
            )
        if "citation_status" not in obl_cols:
            batch.add_column(
                sa.Column(
                    "citation_status",
                    sa.String(length=40),
                    nullable=False,
                    server_default="UNVERIFIED",
                )
            )

    if "applies_to" not in _existing_columns("controls"):
        with op.batch_alter_table("controls") as batch:
            batch.add_column(sa.Column("applies_to", JSONB(), nullable=True))


def downgrade() -> None:
    if "applies_to" in _existing_columns("controls"):
        with op.batch_alter_table("controls") as batch:
            batch.drop_column("applies_to")

    obl_cols = _existing_columns("obligations")
    with op.batch_alter_table("obligations") as batch:
        if "citation_status" in obl_cols:
            batch.drop_column("citation_status")
        if "legal_status" in obl_cols:
            batch.drop_column("legal_status")
        if "source_url" in obl_cols:
            batch.drop_column("source_url")

    reg_cols = _existing_columns("regulations")
    with op.batch_alter_table("regulations") as batch:
        if "legal_status" in reg_cols:
            batch.drop_column("legal_status")
        if "pack_version" in reg_cols:
            batch.drop_column("pack_version")
        if "pack" in reg_cols:
            batch.drop_column("pack")
        if "source_url" in reg_cols:
            batch.drop_column("source_url")
