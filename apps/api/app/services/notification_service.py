"""Notification store service (feature #6).

CRUD for in-app notifications plus an ``upsert`` that dedupes recurring reminders
by a stable key. When a notification is created (or a dormant email integration
is live) a best-effort email is dispatched for WARNING/CRITICAL items.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.enums import NotificationSeverity, NotificationState
from app.core.errors import NotFoundError
from app.models.notification import Notification
from app.services import email_service

_ACTIVE = (NotificationState.UNREAD.value, NotificationState.READ.value)


def upsert(
    db: Session,
    org_id: uuid.UUID,
    *,
    kind: str,
    title: str,
    body: str | None = None,
    severity: str = NotificationSeverity.INFO.value,
    entity_type: str | None = None,
    entity_id: str | None = None,
    dedupe_key: str | None = None,
    due_at=None,
    user_id: uuid.UUID | None = None,
    email_to: str | None = None,
) -> tuple[Notification, bool]:
    """Create a notification, or refresh an existing active one with the same key.

    Returns (notification, created) where ``created`` is True only for a brand-new
    row. Dismissed notifications with the same key are treated as gone (a new one
    is created), so a re-raised reminder reappears after a user dismisses a stale one
    only if it is still relevant on a later run.
    """
    existing: Notification | None = None
    if dedupe_key:
        existing = db.scalar(
            select(Notification).where(
                Notification.organization_id == org_id,
                Notification.dedupe_key == dedupe_key,
                Notification.state.in_(_ACTIVE),
            )
        )

    if existing is not None:
        # Refresh content in place; do not resurrect read->unread aggressively,
        # but re-raise to UNREAD if severity increased.
        existing.title = title
        existing.body = body
        existing.entity_type = entity_type
        existing.entity_id = entity_id
        existing.due_at = due_at
        if _rank(severity) > _rank(existing.severity):
            existing.severity = severity
            existing.state = NotificationState.UNREAD.value
            existing.read_at = None
        db.flush()
        return existing, False

    notif = Notification(
        organization_id=org_id,
        user_id=user_id,
        kind=kind,
        severity=severity,
        state=NotificationState.UNREAD.value,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        dedupe_key=dedupe_key,
        due_at=due_at,
    )
    db.add(notif)
    db.flush()

    # Best-effort email for higher-severity items (no-op when SMTP is dormant).
    if email_to and severity in (NotificationSeverity.WARNING.value, NotificationSeverity.CRITICAL.value):
        email_service.send_email(
            to=email_to,
            subject=f"[ComplyGraph] {title}",
            body=(body or title),
        )
    return notif, True


def _rank(severity: str) -> int:
    return {"INFO": 0, "WARNING": 1, "CRITICAL": 2}.get(severity, 0)


def list_notifications(
    db: Session,
    org_id: uuid.UUID,
    *,
    state: str | None = None,
    limit: int = 100,
) -> list[Notification]:
    stmt = select(Notification).where(Notification.organization_id == org_id)
    if state:
        stmt = stmt.where(Notification.state == state)
    else:
        # Default view hides dismissed.
        stmt = stmt.where(Notification.state.in_(_ACTIVE))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))


def unread_count(db: Session, org_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.organization_id == org_id,
                Notification.state == NotificationState.UNREAD.value,
            )
        )
        or 0
    )


def _get(db: Session, org_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    n = db.get(Notification, notification_id)
    if n is None or n.organization_id != org_id:
        raise NotFoundError("Notification not found.")
    return n


def mark_read(db: Session, org_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    n = _get(db, org_id, notification_id)
    if n.state == NotificationState.UNREAD.value:
        n.state = NotificationState.READ.value
        n.read_at = utcnow()
        db.flush()
    return n


def dismiss(db: Session, org_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    n = _get(db, org_id, notification_id)
    n.state = NotificationState.DISMISSED.value
    db.flush()
    return n


def mark_all_read(db: Session, org_id: uuid.UUID) -> int:
    rows = db.scalars(
        select(Notification).where(
            Notification.organization_id == org_id,
            Notification.state == NotificationState.UNREAD.value,
        )
    )
    count = 0
    now = utcnow()
    for n in rows:
        n.state = NotificationState.READ.value
        n.read_at = now
        count += 1
    db.flush()
    return count
