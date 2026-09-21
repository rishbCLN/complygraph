"""Notification / reminder endpoints (feature #6)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.rbac import ASSESS_CONTROLS
from app.models.notification import Notification
from app.services import reminder_service, notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: str
    kind: str
    severity: str
    state: str
    title: str
    body: str | None
    entity_type: str | None
    entity_id: str | None
    due_at: datetime | None
    read_at: datetime | None
    created_at: datetime | None


class UnreadCountOut(BaseModel):
    unread: int


class GenerateResult(BaseModel):
    total: int
    by_kind: dict[str, int]


def _out(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=str(n.id),
        kind=n.kind,
        severity=n.severity,
        state=n.state,
        title=n.title,
        body=n.body,
        entity_type=n.entity_type,
        entity_id=n.entity_id,
        due_at=n.due_at,
        read_at=n.read_at,
        created_at=n.created_at,
    )


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    state: str | None = Query(None),
) -> list[NotificationOut]:
    return [
        _out(n)
        for n in notification_service.list_notifications(db, ctx.organization_id, state=state)
    ]


@router.get("/unread-count", response_model=UnreadCountOut)
def unread_count(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> UnreadCountOut:
    return UnreadCountOut(unread=notification_service.unread_count(db, ctx.organization_id))


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> NotificationOut:
    n = notification_service.mark_read(db, ctx.organization_id, notification_id)
    db.commit()
    db.refresh(n)
    return _out(n)


@router.post("/{notification_id}/dismiss", response_model=NotificationOut)
def dismiss(
    notification_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> NotificationOut:
    n = notification_service.dismiss(db, ctx.organization_id, notification_id)
    db.commit()
    db.refresh(n)
    return _out(n)


@router.post("/read-all", response_model=UnreadCountOut)
def mark_all_read(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> UnreadCountOut:
    notification_service.mark_all_read(db, ctx.organization_id)
    db.commit()
    return UnreadCountOut(unread=notification_service.unread_count(db, ctx.organization_id))


@router.post("/generate", response_model=GenerateResult)
def generate_reminders(
    ctx: AuthContext = Depends(require_capability(ASSESS_CONTROLS)),
    db: Session = Depends(get_db),
) -> GenerateResult:
    """Run the reminder engine now for this org (also runs on the beat cadence)."""
    counts = reminder_service.generate_for_org(db, ctx.organization)
    record_audit(
        db,
        action="reminders.generated",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="notification",
        metadata={"total": counts.get("total", 0)},
    )
    db.commit()
    total = counts.pop("total", 0)
    return GenerateResult(total=total, by_kind=counts)
