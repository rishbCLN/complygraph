"""Maker-checker approval workflow endpoints (feature #4).

Submitting a request requires the capability to make the underlying change
(e.g. manage_findings, manage_risk, assess_controls). Approving or rejecting
requires the distinct approve_requests capability, and the reviewer must differ
from the submitter (segregation of duties).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.errors import ForbiddenError
from app.core.rbac import (
    APPROVE_REQUESTS,
    ASSESS_CONTROLS,
    MANAGE_FINDINGS,
    MANAGE_RISK,
    has_capability,
)
from app.models.approval import ApprovalRequest
from app.services import approval_service

router = APIRouter(prefix="/approvals", tags=["approvals"])

# Which capability a submitter needs, per entity_type.
_SUBMIT_CAP = {
    "finding": MANAGE_FINDINGS,
    "risk": MANAGE_RISK,
    "assessment": ASSESS_CONTROLS,
}


class SubmitIn(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    action: str
    payload: dict | None = None
    summary: str | None = None


class ReviewIn(BaseModel):
    note: str | None = None


class ApprovalOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    action: str
    payload: dict | None
    summary: str | None
    status: str
    submitted_by: str | None
    submitted_at: datetime
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_note: str | None


def _out(req: ApprovalRequest) -> ApprovalOut:
    return ApprovalOut(
        id=str(req.id),
        entity_type=req.entity_type,
        entity_id=str(req.entity_id),
        action=req.action,
        payload=req.payload,
        summary=req.summary,
        status=req.status,
        submitted_by=str(req.submitted_by) if req.submitted_by else None,
        submitted_at=req.submitted_at,
        reviewed_by=str(req.reviewed_by) if req.reviewed_by else None,
        reviewed_at=req.reviewed_at,
        review_note=req.review_note,
    )


@router.get("", response_model=list[ApprovalOut])
def list_approvals(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    status: str | None = Query(None),
    entity_type: str | None = Query(None),
) -> list[ApprovalOut]:
    return [
        _out(r)
        for r in approval_service.list_requests(
            db, ctx.organization_id, status=status, entity_type=entity_type
        )
    ]


@router.post("", response_model=ApprovalOut, status_code=201)
def submit_approval(
    payload: SubmitIn,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> ApprovalOut:
    # The submitter must be allowed to make the underlying change.
    required = _SUBMIT_CAP.get(payload.entity_type)
    if required is None or not has_capability(ctx.membership.role, required):
        raise ForbiddenError("You do not have permission to propose this change.")
    req = approval_service.submit(
        db,
        ctx.organization_id,
        ctx.user.id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        action=payload.action,
        payload=payload.payload,
        summary=payload.summary,
    )
    record_audit(
        db,
        action="approval.submitted",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="approval_request",
        entity_id=req.id,
        metadata={"target": payload.entity_type, "action": payload.action},
    )
    db.commit()
    db.refresh(req)
    return _out(req)


@router.get("/{request_id}", response_model=ApprovalOut)
def get_approval(
    request_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> ApprovalOut:
    return _out(approval_service.get(db, ctx.organization_id, request_id))


@router.post("/{request_id}/approve", response_model=ApprovalOut)
def approve_request(
    request_id: uuid.UUID,
    payload: ReviewIn,
    ctx: AuthContext = Depends(require_capability(APPROVE_REQUESTS)),
    db: Session = Depends(get_db),
) -> ApprovalOut:
    req = approval_service.approve(
        db, ctx.organization_id, request_id, ctx.user.id, note=payload.note
    )
    record_audit(
        db,
        action="approval.approved",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="approval_request",
        entity_id=req.id,
        metadata={"target": req.entity_type, "action": req.action},
    )
    db.commit()
    db.refresh(req)
    return _out(req)


@router.post("/{request_id}/reject", response_model=ApprovalOut)
def reject_request(
    request_id: uuid.UUID,
    payload: ReviewIn,
    ctx: AuthContext = Depends(require_capability(APPROVE_REQUESTS)),
    db: Session = Depends(get_db),
) -> ApprovalOut:
    req = approval_service.reject(
        db, ctx.organization_id, request_id, ctx.user.id, note=payload.note
    )
    record_audit(
        db,
        action="approval.rejected",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="approval_request",
        entity_id=req.id,
    )
    db.commit()
    db.refresh(req)
    return _out(req)


@router.post("/{request_id}/cancel", response_model=ApprovalOut)
def cancel_request(
    request_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> ApprovalOut:
    req = approval_service.cancel(db, ctx.organization_id, request_id, ctx.user.id)
    record_audit(
        db,
        action="approval.cancelled",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="approval_request",
        entity_id=req.id,
    )
    db.commit()
    db.refresh(req)
    return _out(req)
