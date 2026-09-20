"""AI system inventory + architecture graph tables

Adds the AI-system-centric inventory so an AI system's architecture (models,
data stores, vendors, flows) can be mapped against the regulatory graph:

  ai_systems             first-class governed AI system entity
  ai_system_components   architecture-graph nodes (model/agent/data store/...)
  ai_system_flows        directed edges between components

Revision ID: 0004_ai_systems
Revises: 0003_regulatory_legal_status
Create Date: 2026-09-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID, JSONB

revision = "0004_ai_systems"
down_revision = "0003_regulatory_legal_status"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    """True if the table already exists.

    The 0001 baseline builds the schema from live metadata (create_all), so on a
    fresh database these tables already exist. Guarding keeps the migration safe
    on both a fresh baseline and a genuine historical upgrade.
    """
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if _has_table("ai_systems"):
        return
    op.create_table(
        "ai_systems",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "organization_id",
            GUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("business_purpose", sa.Text(), nullable=True),
        sa.Column("owner", sa.String(length=255), nullable=True),
        sa.Column("system_type", sa.String(length=40), nullable=False, server_default="OTHER"),
        sa.Column("risk_domain", sa.String(length=120), nullable=True),
        sa.Column(
            "lifecycle_stage", sa.String(length=40), nullable=False, server_default="DEVELOPMENT"
        ),
        sa.Column(
            "review_status", sa.String(length=40), nullable=False, server_default="NOT_REVIEWED"
        ),
        sa.Column("sector", sa.String(length=60), nullable=False, server_default="general"),
        sa.Column("regions", JSONB(), nullable=True),
        sa.Column("deployment_environment", sa.String(length=80), nullable=True),
        sa.Column(
            "processes_personal_data", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "makes_automated_decisions", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("high_risk", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ai_systems_org", "ai_systems", ["organization_id"])
    op.create_index("ix_ai_systems_stage", "ai_systems", ["lifecycle_stage"])

    op.create_table(
        "ai_system_components",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "ai_system_id",
            GUID(),
            sa.ForeignKey("ai_systems.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("component_type", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=255), nullable=True),
        sa.Column("region", sa.String(length=80), nullable=True),
        sa.Column("external", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "vendor_id", GUID(), sa.ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "data_asset_id",
            GUID(),
            sa.ForeignKey("data_assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("data_categories", JSONB(), nullable=True),
        sa.Column("config", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ai_components_system", "ai_system_components", ["ai_system_id"])
    op.create_index("ix_ai_components_type", "ai_system_components", ["component_type"])

    op.create_table(
        "ai_system_flows",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "ai_system_id",
            GUID(),
            sa.ForeignKey("ai_systems.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_component_id",
            GUID(),
            sa.ForeignKey("ai_system_components.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "target_component_id",
            GUID(),
            sa.ForeignKey("ai_system_components.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("relation", sa.String(length=40), nullable=False, server_default="SENDS_TO"),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("data_categories", JSONB(), nullable=True),
        sa.Column(
            "contains_personal_data", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("cross_border", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ai_flows_system", "ai_system_flows", ["ai_system_id"])
    op.create_index("ix_ai_flows_source", "ai_system_flows", ["source_component_id"])
    op.create_index("ix_ai_flows_target", "ai_system_flows", ["target_component_id"])


def downgrade() -> None:
    if _has_table("ai_system_flows"):
        op.drop_table("ai_system_flows")
    if _has_table("ai_system_components"):
        op.drop_table("ai_system_components")
    if _has_table("ai_systems"):
        op.drop_table("ai_systems")
