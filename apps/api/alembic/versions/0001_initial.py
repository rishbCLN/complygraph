"""initial schema

Creates the full ComplyGraph schema from SQLAlchemy metadata. Subsequent schema
changes must be expressed as new Alembic revisions rather than editing this file.

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01
"""
from __future__ import annotations

from alembic import op

from app.core.database import Base

# Import models so every table is registered on Base.metadata.
import app.models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
