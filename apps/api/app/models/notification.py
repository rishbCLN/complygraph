"""Notification / reminder model (feature #6).

An append-then-update in-app notification store. Reminders (expiring evidence,
overdue findings/tasks/DSRs, risk reviews due, controls due for re-assessment)
and re-assessment outcomes are written here by the reminder/re-assessment
services. Each notification carries a stable ``dedupe_key`` so a recurring
scheduled run refreshes rather than duplicates an existing open reminder.

Notifications are org-scoped and may optionally target a specific user. No PII
or secret values are stored in the title/body - only entity references and
compliance metadata.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._common import TimestampMixin, uuid_pk
from app.models.types import GUID


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_org", "organization_id"),
        Index("ix_notifications_state", "state"),
        Index("ix_notifications_dedupe", "organization_id", "dedupe_key"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    # Optional per-user targeting (bare GUID - user table has no strict FK use here).
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="INFO")
    state: Mapped[str] = mapped_column(String(20), default="UNREAD")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    # Deep-link target (e.g. entity_type="finding", entity_id=<uuid>).
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    # Stable identity for a recurring reminder so runs refresh, not duplicate.
    dedupe_key: Mapped[str | None] = mapped_column(String(200))
    # When the underlying thing is due/expires (for sorting and display).
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
