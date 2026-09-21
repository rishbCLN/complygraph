"""Risk register table (feature #3)

Adds risks: the risk register with inherent/residual qualitative scoring, an
optional quantitative view (SLE x ARO), business-impact-analysis fields, a
treatment strategy, an acceptance workflow and optional links to the finding /
control / vendor / AI system / processing activity the risk concerns.

Revision ID: 0009_risks
Revises: 0008_custom_packs
Create Date: 2026-09-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID

revision = "0009_risks"
down_revision = "0008_custom_packs"
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
    if not _has_table("risks"):
        op.create_table(
            "risks",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column("organization_id", GUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("category", sa.String(length=40), nullable=False, server_default="COMPLIANCE"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="IDENTIFIED"),
            sa.Column("owner", sa.String(length=255), nullable=True),
            sa.Column("inherent_likelihood", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("inherent_impact", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("residual_likelihood", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("residual_impact", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("treatment_strategy", sa.String(length=40), nullable=False, server_default="MITIGATE"),
            sa.Column("treatment_plan", sa.Text(), nullable=True),
            sa.Column("single_loss_expectancy", sa.Float(), nullable=True),
            sa.Column("annual_rate_of_occurrence", sa.Float(), nullable=True),
            sa.Column("rto_hours", sa.Integer(), nullable=True),
            sa.Column("rpo_hours", sa.Integer(), nullable=True),
            sa.Column("max_tolerable_downtime_hours", sa.Integer(), nullable=True),
            sa.Column("business_impact", sa.Text(), nullable=True),
            sa.Column("accepted_by", GUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("acceptance_rationale", sa.Text(), nullable=True),
            sa.Column("acceptance_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("review_due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("control_id", GUID(), sa.ForeignKey("controls.id", ondelete="SET NULL"), nullable=True),
            sa.Column("finding_id", GUID(), sa.ForeignKey("findings.id", ondelete="SET NULL"), nullable=True),
            sa.Column("vendor_id", GUID(), sa.ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True),
            sa.Column("ai_system_id", GUID(), sa.ForeignKey("ai_systems.id", ondelete="SET NULL"), nullable=True),
            sa.Column(
                "processing_activity_id",
                GUID(),
                sa.ForeignKey("processing_activities.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_by", GUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    for name, cols in (
        ("ix_risks_org", ["organization_id"]),
        ("ix_risks_status", ["status"]),
    ):
        if not _has_index("risks", name):
            op.create_index(name, "risks", cols)


def downgrade() -> None:
    for name in ("ix_risks_status", "ix_risks_org"):
        if _has_index("risks", name):
            op.drop_index(name, table_name="risks")
    if _has_table("risks"):
        op.drop_table("risks")
