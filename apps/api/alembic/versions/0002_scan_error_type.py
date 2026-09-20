"""add scan.error_type

Adds a structured error category to scans so failures can be surfaced with
actionable guidance (connection vs configuration vs data vs internal) rather
than only a raw exception string.

Revision ID: 0002_scan_error_type
Revises: 0001_initial
Create Date: 2026-09-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_scan_error_type"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    """True if the column already exists.

    The 0001 baseline builds the schema from live metadata (create_all), so on a
    fresh database this column already exists. Guarding makes the migration safe
    on both a fresh baseline and a genuine historical upgrade.
    """
    inspector = sa.inspect(op.get_bind())
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    if not _has_column("scans", "error_type"):
        with op.batch_alter_table("scans") as batch:
            batch.add_column(sa.Column("error_type", sa.String(length=40), nullable=True))


def downgrade() -> None:
    if _has_column("scans", "error_type"):
        with op.batch_alter_table("scans") as batch:
            batch.drop_column("error_type")
