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


def upgrade() -> None:
    with op.batch_alter_table("regulations") as batch:
        batch.add_column(sa.Column("source_url", sa.String(length=1024), nullable=True))
        batch.add_column(sa.Column("pack", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("pack_version", sa.String(length=40), nullable=True))
        batch.add_column(
            sa.Column(
                "legal_status",
                sa.String(length=40),
                nullable=False,
                server_default="BINDING_LAW",
            )
        )

    with op.batch_alter_table("obligations") as batch:
        batch.add_column(sa.Column("source_url", sa.String(length=1024), nullable=True))
        batch.add_column(
            sa.Column(
                "legal_status",
                sa.String(length=40),
                nullable=False,
                server_default="BINDING_LAW",
            )
        )
        batch.add_column(
            sa.Column(
                "citation_status",
                sa.String(length=40),
                nullable=False,
                server_default="UNVERIFIED",
            )
        )

    with op.batch_alter_table("controls") as batch:
        batch.add_column(sa.Column("applies_to", JSONB(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("controls") as batch:
        batch.drop_column("applies_to")

    with op.batch_alter_table("obligations") as batch:
        batch.drop_column("citation_status")
        batch.drop_column("legal_status")
        batch.drop_column("source_url")

    with op.batch_alter_table("regulations") as batch:
        batch.drop_column("legal_status")
        batch.drop_column("pack_version")
        batch.drop_column("pack")
        batch.drop_column("source_url")
