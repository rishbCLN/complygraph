"""Audit event helper. Every security-relevant mutation should call record_audit."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.models.identity import AuditEvent


def record_audit(
    db: Session,
    *,
    action: str,
    organization_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | uuid.UUID | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> AuditEvent:
    """Create an audit event. Metadata must never contain personal data or secrets."""
    event = AuditEvent(
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        audit_metadata=metadata,
        ip_address=ip_address,
        created_at=utcnow(),
    )
    db.add(event)
    return event
