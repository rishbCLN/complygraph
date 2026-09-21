"""DSR fulfillment engine (feature #7)

Adds dsr_tasks (per-datastore execution steps) and fulfillment columns on
data_subject_requests (the assembled access/erasure package + timestamp).

Revision ID: 0012_dsr_fulfillment
Revises: 0011_campaigns
Create Date: 2026-09-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.types import GUID, JSONB

revision = "0012_dsr_fulfillment"
down_revision = "0011_campaigns"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return table in insp.get_table_names()


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
    if _has_table("data_subject_requests"):
        if not _has_column("data_subject_requests", "fulfillment"):
            op.add_column("data_subject_requests", sa.Column("fulfillment", JSONB(), nullable=True))
        if not _has_column("data_subject_requests", "fulfilled_at"):
            op.add_column(
                "data_subject_requests", sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True)
            )

    if not _has_table("dsr_tasks"):
        op.create_table(
            "dsr_tasks",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column(
                "request_id", GUID(), sa.ForeignKey("data_subject_requests.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("asset_id", GUID(), sa.ForeignKey("data_assets.id", ondelete="SET NULL"), nullable=True),
            sa.Column("asset_name", sa.String(length=255), nullable=False),
            sa.Column("connector_type", sa.String(length=80), nullable=True),
            sa.Column("action", sa.String(length=40), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="PENDING"),
            sa.Column("matched_fields", JSONB(), nullable=True),
            sa.Column("records_affected", sa.Integer(), nullable=True),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    for name, cols in (
        ("ix_dsr_tasks_request", ["request_id"]),
        ("ix_dsr_tasks_status", ["status"]),
    ):
        if not _has_index("dsr_tasks", name):
            op.create_index(name, "dsr_tasks", cols)


def downgrade() -> None:
    for name in ("ix_dsr_tasks_status", "ix_dsr_tasks_request"):
        if _has_index("dsr_tasks", name):
            op.drop_index(name, table_name="dsr_tasks")
    if _has_table("dsr_tasks"):
        op.drop_table("dsr_tasks")
    if _has_column("data_subject_requests", "fulfilled_at"):
        op.drop_column("data_subject_requests", "fulfilled_at")
    if _has_column("data_subject_requests", "fulfillment"):
        op.drop_column("data_subject_requests", "fulfillment")
