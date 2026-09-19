"""Audit event endpoints. Read-only, org-scoped audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context
from app.api.query import paginate
from app.core.database import get_db
from app.models.identity import AuditEvent
from app.schemas.common import Page

router = APIRouter(tags=["audit"])


class AuditEventOut(BaseModel):
    id: str
    action: str
    entity_type: str | None
    entity_id: str | None
    user_id: str | None
    metadata: dict | None
    ip_address: str | None
    created_at: datetime | None


def _out(e: AuditEvent) -> AuditEventOut:
    return AuditEventOut(
        id=str(e.id),
        action=e.action,
        entity_type=e.entity_type,
        entity_id=e.entity_id,
        user_id=str(e.user_id) if e.user_id else None,
        metadata=e.audit_metadata,
        ip_address=e.ip_address,
        created_at=e.created_at,
    )


@router.get("/audit-events", response_model=Page[AuditEventOut])
def list_audit_events(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> Page[AuditEventOut]:
    stmt = select(AuditEvent).where(AuditEvent.organization_id == ctx.organization_id)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)
    stmt = stmt.order_by(AuditEvent.created_at.desc())
    rows, total = paginate(db, stmt, page, page_size)
    return Page(items=[_out(e) for e in rows], total=total, page=page, page_size=page_size)
