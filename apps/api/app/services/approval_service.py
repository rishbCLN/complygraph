"""Maker-checker approval service (feature #4).

Submitting a request records a *proposed* change with no side effects. Approving
it applies the change through a dispatch handler and stamps the reviewer.
Segregation of duties is enforced: the reviewer must be a different user than the
submitter.

Supported (entity_type, action) pairs:
  - ("finding", "resolve" | "accept_risk" | "false_positive") -> finding transition
  - ("risk", "accept")                                        -> risk acceptance
  - ("assessment", "sign_off")                                -> control assessment sign-off
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.enums import FindingStatus
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.approval import ApprovalRequest
from app.models.findings import Finding
from app.models.regulatory import ControlAssessment
from app.models.risk import Risk

PENDING = "PENDING"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
CANCELLED = "CANCELLED"

_FINDING_ACTIONS = {
    "resolve": FindingStatus.RESOLVED.value,
    "accept_risk": FindingStatus.ACCEPTED_RISK.value,
    "false_positive": FindingStatus.FALSE_POSITIVE.value,
}

# Allowed (entity_type -> {actions}) surface, validated on submit.
_ACTIONS: dict[str, set[str]] = {
    "finding": set(_FINDING_ACTIONS),
    "risk": {"accept"},
    "assessment": {"sign_off"},
}


def _entity_exists(db: Session, org_id: uuid.UUID, entity_type: str, entity_id: uuid.UUID) -> object:
    model = {"finding": Finding, "risk": Risk, "assessment": ControlAssessment}.get(entity_type)
    if model is None:
        raise ValidationError(f"Unknown entity_type '{entity_type}'.")
    row = db.get(model, entity_id)
    if row is None or getattr(row, "organization_id", None) != org_id:
        raise NotFoundError(f"{entity_type} not found.")
    return row


def submit(
    db: Session,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    payload: dict | None,
    summary: str | None = None,
) -> ApprovalRequest:
    if entity_type not in _ACTIONS:
        raise ValidationError(f"entity_type must be one of {sorted(_ACTIONS)}")
    if action not in _ACTIONS[entity_type]:
        raise ValidationError(f"action '{action}' not valid for {entity_type}.")

    _entity_exists(db, org_id, entity_type, entity_id)

    # Per-entity guardrails so a request carries the data its handler needs.
    payload = payload or {}
    if entity_type == "finding" and action in {"accept_risk", "false_positive"} and not (
        payload.get("note") or ""
    ).strip():
        raise ValidationError(f"A justification note is required to {action} a finding.")
    if entity_type == "risk" and action == "accept" and not (payload.get("rationale") or "").strip():
        raise ValidationError("Risk acceptance requires a rationale.")

    # One open request per (entity, action) at a time.
    existing = db.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.organization_id == org_id,
            ApprovalRequest.entity_type == entity_type,
            ApprovalRequest.entity_id == entity_id,
            ApprovalRequest.action == action,
            ApprovalRequest.status == PENDING,
        )
    )
    if existing is not None:
        raise ConflictError("A pending approval already exists for this change.")

    req = ApprovalRequest(
        organization_id=org_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        payload=payload,
        summary=summary,
        status=PENDING,
        submitted_by=user_id,
        submitted_at=utcnow(),
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(req)
    db.flush()
    return req


def get(db: Session, org_id: uuid.UUID, request_id: uuid.UUID) -> ApprovalRequest:
    req = db.get(ApprovalRequest, request_id)
    if req is None or req.organization_id != org_id:
        raise NotFoundError("Approval request not found.")
    return req


def list_requests(
    db: Session,
    org_id: uuid.UUID,
    *,
    status: str | None = None,
    entity_type: str | None = None,
) -> list[ApprovalRequest]:
    stmt = select(ApprovalRequest).where(ApprovalRequest.organization_id == org_id)
    if status:
        stmt = stmt.where(ApprovalRequest.status == status)
    if entity_type:
        stmt = stmt.where(ApprovalRequest.entity_type == entity_type)
    return list(db.scalars(stmt.order_by(ApprovalRequest.submitted_at.desc())))


def _apply(db: Session, org_id: uuid.UUID, req: ApprovalRequest) -> None:
    """Apply the approved change. The maker (submitter) is recorded as the actor
    who owns the change; the checker's identity is stored on the request."""
    payload = req.payload or {}
    actor = req.submitted_by
    if req.entity_type == "finding":
        from app.services.findings_service import transition_finding

        finding = _entity_exists(db, org_id, "finding", req.entity_id)
        transition_finding(
            db,
            finding,  # type: ignore[arg-type]
            new_status=_FINDING_ACTIONS[req.action],
            user_id=actor,
            organization_id=org_id,
            note=payload.get("note"),
        )
    elif req.entity_type == "risk":
        from app.services import risk_service

        expires = payload.get("expires_at")
        if isinstance(expires, str):
            expires = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        risk_service.accept_risk(
            db,
            org_id,
            req.entity_id,
            actor,
            rationale=payload.get("rationale", ""),
            expires_at=expires,
        )
    elif req.entity_type == "assessment":
        assessment = _entity_exists(db, org_id, "assessment", req.entity_id)
        assessment.approved_by = actor  # type: ignore[attr-defined]
        assessment.approved_at = utcnow()  # type: ignore[attr-defined]
    else:  # pragma: no cover - guarded on submit
        raise ValidationError(f"Cannot apply action for {req.entity_type}.")


def approve(
    db: Session,
    org_id: uuid.UUID,
    request_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    *,
    note: str | None = None,
) -> ApprovalRequest:
    req = get(db, org_id, request_id)
    if req.status != PENDING:
        raise ConflictError(f"Request is already {req.status}.")
    if req.submitted_by == reviewer_id:
        raise ValidationError("Segregation of duties: the submitter cannot approve their own request.")
    _apply(db, org_id, req)
    req.status = APPROVED
    req.reviewed_by = reviewer_id
    req.reviewed_at = utcnow()
    req.review_note = note
    req.updated_at = utcnow()
    db.flush()
    return req


def reject(
    db: Session,
    org_id: uuid.UUID,
    request_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    *,
    note: str | None = None,
) -> ApprovalRequest:
    req = get(db, org_id, request_id)
    if req.status != PENDING:
        raise ConflictError(f"Request is already {req.status}.")
    if req.submitted_by == reviewer_id:
        raise ValidationError("Segregation of duties: the submitter cannot review their own request.")
    req.status = REJECTED
    req.reviewed_by = reviewer_id
    req.reviewed_at = utcnow()
    req.review_note = note
    req.updated_at = utcnow()
    db.flush()
    return req


def cancel(db: Session, org_id: uuid.UUID, request_id: uuid.UUID, user_id: uuid.UUID) -> ApprovalRequest:
    req = get(db, org_id, request_id)
    if req.status != PENDING:
        raise ConflictError(f"Request is already {req.status}.")
    if req.submitted_by != user_id:
        raise ValidationError("Only the submitter can cancel a pending request.")
    req.status = CANCELLED
    req.updated_at = utcnow()
    db.flush()
    return req
