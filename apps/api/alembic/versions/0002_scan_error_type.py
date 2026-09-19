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


def upgrade() -> None:
    with op.batch_alter_table("scans") as batch:
        batch.add_column(sa.Column("error_type", sa.String(length=40), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("scans") as batch:
        batch.drop_column("error_type")
