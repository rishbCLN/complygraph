"""Breach incident endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.api.query import get_org_scoped
from app.core.audit import record_audit
from app.core.database import get_db, utcnow
from app.core.enums import BreachStatus
from app.core.rbac import MANAGE_BREACH
from app.models.operations import BreachIncident

router = APIRouter(prefix="/incidents", tags=["incidents"])


class IncidentIn(BaseModel):
    title: str
    description: str | None = None
    severity: str | None = "MEDIUM"
    affected_records_estimate: int | None = None
    root_cause: str | None = None


class IncidentUpdate(BaseModel):
    status: str | None = None
    severity: str | None = None
    root_cause: str | None = None
    remediation: str | None = None
    contained_at: datetime | None = None
    affected_records_estimate: int | None = None


class IncidentOut(BaseModel):
    id: str
    title: str
    description: str | None
    severity: str
    status: str
    detected_at: datetime | None
    contained_at: datetime | None
    affected_records_estimate: int | None
    board_notification_status: str
    principal_notification_status: str
    root_cause: str | None
    remediation: str | None
    timeline: dict | None


def _out(i: BreachIncident) -> IncidentOut:
    return IncidentOut(
        id=str(i.id),
        title=i.title,
        description=i.description,
        severity=i.severity,
        status=i.status,
        detected_at=i.detected_at,
        contained_at=i.contained_at,
        affected_records_estimate=i.affected_records_estimate,
        board_notification_status=i.board_notification_status,
        principal_notification_status=i.principal_notification_status,
        root_cause=i.root_cause,
        remediation=i.remediation,
        timeline=i.timeline,
    )


def _append_timeline(incident: BreachIncident, event: str) -> None:
    timeline = incident.timeline or {"events": []}
    events = timeline.get("events", [])
    events.append({"at": utcnow().isoformat(), "event": event})
    incident.timeline = {"events": events}


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)
) -> list[IncidentOut]:
    rows = db.scalars(
        select(BreachIncident)
        .where(BreachIncident.organization_id == ctx.organization_id)
        .order_by(BreachIncident.detected_at.desc())
    )
    return [_out(i) for i in rows]


@router.post("", response_model=IncidentOut, status_code=201)
def create_incident(
    payload: IncidentIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_BREACH)),
    db: Session = Depends(get_db),
) -> IncidentOut:
    incident = BreachIncident(
        organization_id=ctx.organization_id,
        status=BreachStatus.DETECTED.value,
        detected_at=utcnow(),
        **payload.model_dump(exclude_none=True),
    )
    _append_timeline(incident, "Incident detected")
    db.add(incident)
    db.flush()
    record_audit(
        db,
        action="incident.created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="incident",
        entity_id=incident.id,
    )
    db.commit()
    return _out(incident)


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(
    incident_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> IncidentOut:
    return _out(get_org_scoped(db, BreachIncident, incident_id, ctx.organization_id))


@router.patch("/{incident_id}", response_model=IncidentOut)
def update_incident(
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    ctx: AuthContext = Depends(require_capability(MANAGE_BREACH)),
    db: Session = Depends(get_db),
) -> IncidentOut:
    incident = get_org_scoped(db, BreachIncident, incident_id, ctx.organization_id)
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] != incident.status:
        _append_timeline(incident, f"Status changed to {data['status']}")
    for key, value in data.items():
        setattr(incident, key, value)
    record_audit(
        db,
        action="incident.updated",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="incident",
        entity_id=incident.id,
        metadata={"status": incident.status},
    )
    db.commit()
    return _out(incident)


@router.post("/{incident_id}/notify", response_model=IncidentOut)
def notify_incident(
    incident_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_BREACH)),
    db: Session = Depends(get_db),
) -> IncidentOut:
    incident = get_org_scoped(db, BreachIncident, incident_id, ctx.organization_id)
    incident.board_notification_status = "COMPLETED"
    incident.principal_notification_status = "COMPLETED"
    incident.status = BreachStatus.NOTIFIED.value
    _append_timeline(incident, "Notifications recorded (board + data principals)")
    record_audit(
        db,
        action="incident.notified",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="incident",
        entity_id=incident.id,
    )
    db.commit()
    return _out(incident)


@router.post("/{incident_id}/close", response_model=IncidentOut)
def close_incident(
    incident_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_BREACH)),
    db: Session = Depends(get_db),
) -> IncidentOut:
    incident = get_org_scoped(db, BreachIncident, incident_id, ctx.organization_id)
    incident.status = BreachStatus.CLOSED.value
    _append_timeline(incident, "Incident closed")
    record_audit(
        db,
        action="incident.closed",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="incident",
        entity_id=incident.id,
    )
    db.commit()
    return _out(incident)
