"""Audit campaigns (feature #5)

Adds audit_campaigns (a scoped, tracked assessment run) and campaign_results
(the persisted per-control outcome for that run).

Revision ID: 0011_campaigns
Revises: 0010_approvals
Create Date: 2026-09-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID, JSONB

revision = "0011_campaigns"
down_revision = "0010_approvals"
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
    if not _has_table("audit_campaigns"):
        op.create_table(
            "audit_campaigns",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column("organization_id", GUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("scope_regulation_ids", JSONB(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
            sa.Column("assessment_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("summary", JSONB(), nullable=True),
            sa.Column("created_by", GUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    for name, cols in (
        ("ix_campaigns_org", ["organization_id"]),
        ("ix_campaigns_status", ["status"]),
    ):
        if not _has_index("audit_campaigns", name):
            op.create_index(name, "audit_campaigns", cols)

    if not _has_table("campaign_results"):
        op.create_table(
            "campaign_results",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column("campaign_id", GUID(), sa.ForeignKey("audit_campaigns.id", ondelete="CASCADE"), nullable=False),
            sa.Column("control_id", GUID(), sa.ForeignKey("controls.id", ondelete="SET NULL"), nullable=True),
            sa.Column("control_code", sa.String(length=80), nullable=False),
            sa.Column("control_title", sa.String(length=255), nullable=True),
            sa.Column("regulation_name", sa.String(length=255), nullable=True),
            sa.Column("category", sa.String(length=80), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    for name, cols in (
        ("ix_campaign_results_campaign", ["campaign_id"]),
        ("ix_campaign_results_status", ["status"]),
    ):
        if not _has_index("campaign_results", name):
            op.create_index(name, "campaign_results", cols)


def downgrade() -> None:
    for name in ("ix_campaign_results_status", "ix_campaign_results_campaign"):
        if _has_index("campaign_results", name):
            op.drop_index(name, table_name="campaign_results")
    if _has_table("campaign_results"):
        op.drop_table("campaign_results")
    for name in ("ix_campaigns_status", "ix_campaigns_org"):
        if _has_index("audit_campaigns", name):
            op.drop_index(name, table_name="audit_campaigns")
    if _has_table("audit_campaigns"):
        op.drop_table("audit_campaigns")
