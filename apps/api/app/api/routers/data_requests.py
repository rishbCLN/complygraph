"""Data Subject Request (DSR) workflow endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.api.query import get_org_scoped
from app.core.audit import record_audit
from app.core.database import get_db, utcnow
from app.core.enums import DSRStatus, DSRType
from app.core.errors import ValidationError
from app.core.rbac import MANAGE_DSR
from app.models.dsr import DSRTask
from app.models.operations import DataSubjectRequest
from app.services import dsr_service

router = APIRouter(prefix="/data-requests", tags=["data-requests"])


class DSRIn(BaseModel):
    requester_identifier: str
    request_type: str
    notes: str | None = None


class DSROut(BaseModel):
    id: str
    requester_identifier: str
    request_type: str
    status: str
    verification_status: str
    received_at: datetime | None
    due_at: datetime | None
    completed_at: datetime | None
    notes: str | None
    fulfillment: dict | None = None
    fulfilled_at: datetime | None = None


class DSRTaskOut(BaseModel):
    id: str
    asset_id: str | None
    asset_name: str
    connector_type: str | None
    action: str
    status: str
    matched_fields: dict | None
    records_affected: int | None
    detail: str | None
    executed_at: datetime | None


class DiscoveryItem(BaseModel):
    asset_id: str
    asset_name: str
    connector_type: str | None
    pii_fields: list[dict]
    row_count: int | None


class DSRUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    assigned_to: uuid.UUID | None = None


def _out(r: DataSubjectRequest) -> DSROut:
    return DSROut(
        id=str(r.id),
        requester_identifier=r.requester_identifier,
        request_type=r.request_type,
        status=r.status,
        verification_status=r.verification_status,
        received_at=r.received_at,
        due_at=r.due_at,
        completed_at=r.completed_at,
        notes=r.notes,
        fulfillment=r.fulfillment,
        fulfilled_at=r.fulfilled_at,
    )


def _task_out(t: DSRTask) -> DSRTaskOut:
    return DSRTaskOut(
        id=str(t.id),
        asset_id=str(t.asset_id) if t.asset_id else None,
        asset_name=t.asset_name,
        connector_type=t.connector_type,
        action=t.action,
        status=t.status,
        matched_fields=t.matched_fields,
        records_affected=t.records_affected,
        detail=t.detail,
        executed_at=t.executed_at,
    )


@router.get("", response_model=list[DSROut])
def list_requests(
    ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)
) -> list[DSROut]:
    rows = db.scalars(
        select(DataSubjectRequest)
        .where(DataSubjectRequest.organization_id == ctx.organization_id)
        .order_by(DataSubjectRequest.created_at.desc())
    )
    return [_out(r) for r in rows]


@router.post("", response_model=DSROut, status_code=201)
def create_request(
    payload: DSRIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_DSR)),
    db: Session = Depends(get_db),
) -> DSROut:
    if payload.request_type not in {t.value for t in DSRType}:
        raise ValidationError(f"Unsupported request type: {payload.request_type}")
    req = DataSubjectRequest(
        organization_id=ctx.organization_id,
        requester_identifier=payload.requester_identifier,
        request_type=payload.request_type,
        status=DSRStatus.REQUESTED.value,
        received_at=utcnow(),
        due_at=utcnow() + timedelta(days=30),
        notes=payload.notes,
    )
    db.add(req)
    db.flush()
    record_audit(
        db,
        action="data_request.created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="data_request",
        entity_id=req.id,
        metadata={"request_type": payload.request_type},
    )
    dsr_service.dispatch_dsr_event(db, req, "dsr.created")
    db.commit()
    return _out(req)


@router.get("/{request_id}", response_model=DSROut)
def get_request(
    request_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> DSROut:
    return _out(get_org_scoped(db, DataSubjectRequest, request_id, ctx.organization_id))


@router.patch("/{request_id}", response_model=DSROut)
def update_request(
    request_id: uuid.UUID,
    payload: DSRUpdate,
    ctx: AuthContext = Depends(require_capability(MANAGE_DSR)),
    db: Session = Depends(get_db),
) -> DSROut:
    req = get_org_scoped(db, DataSubjectRequest, request_id, ctx.organization_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(req, key, value)
    db.commit()
    return _out(req)


@router.post("/{request_id}/verify", response_model=DSROut)
def verify_request(
    request_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_DSR)),
    db: Session = Depends(get_db),
) -> DSROut:
    """Mark identity verification complete and advance the workflow.

    This manages operational workflow state only; it does not perform real legal
    identity verification.
    """
    req = get_org_scoped(db, DataSubjectRequest, request_id, ctx.organization_id)
    req.verification_status = "VERIFIED"
    req.status = DSRStatus.IN_PROGRESS.value
    record_audit(
        db,
        action="data_request.verified",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="data_request",
        entity_id=req.id,
    )
    db.commit()
    return _out(req)


@router.post("/{request_id}/complete", response_model=DSROut)
def complete_request(
    request_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_DSR)),
    db: Session = Depends(get_db),
) -> DSROut:
    req = get_org_scoped(db, DataSubjectRequest, request_id, ctx.organization_id)
    req.status = DSRStatus.FULFILLED.value
    req.completed_at = utcnow()
    dsr_service.dispatch_dsr_event(db, req, "dsr.fulfilled")
    record_audit(
        db,
        action="data_request.completed",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="data_request",
        entity_id=req.id,
    )
    db.commit()
    return _out(req)


@router.get("/{request_id}/discover", response_model=list[DiscoveryItem])
def discover_data(
    request_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_DSR)),
    db: Session = Depends(get_db),
) -> list[DiscoveryItem]:
    """Preview which datastores hold the principal's personal data (read-only)."""
    get_org_scoped(db, DataSubjectRequest, request_id, ctx.organization_id)  # scope check
    discovered = dsr_service.discover(db, ctx.organization_id)
    return [
        DiscoveryItem(
            asset_id=str(entry["asset"].id),
            asset_name=entry["asset"].display_name or entry["asset"].name,
            connector_type=entry["connector"].type if entry["connector"] else None,
            pii_fields=entry["pii_fields"],
            row_count=entry["row_count"],
        )
        for entry in discovered
    ]


@router.post("/{request_id}/fulfill", response_model=DSROut)
def fulfill_request(
    request_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_DSR)),
    db: Session = Depends(get_db),
) -> DSROut:
    """Run the fulfillment engine: discover, execute per-store, and package.

    Requires a verified identity. Collects (ACCESS) or erases (ERASURE) the
    principal's data across managed datastores; non-automatable stores are
    recorded for manual completion.
    """
    req = get_org_scoped(db, DataSubjectRequest, request_id, ctx.organization_id)
    dsr_service.execute(db, req)
    record_audit(
        db,
        action="data_request.fulfilled",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="data_request",
        entity_id=req.id,
        metadata={
            "action": (req.fulfillment or {}).get("action"),
            "stores_completed": (req.fulfillment or {}).get("stores_completed"),
        },
    )
    db.commit()
    db.refresh(req)
    return _out(req)


@router.get("/{request_id}/tasks", response_model=list[DSRTaskOut])
def get_tasks(
    request_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[DSRTaskOut]:
    get_org_scoped(db, DataSubjectRequest, request_id, ctx.organization_id)  # scope check
    return [_task_out(t) for t in dsr_service.list_tasks(db, request_id)]
