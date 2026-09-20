"""Findings endpoints: list, detail, workflow transitions, investigation trigger."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.api.query import get_org_scoped, paginate
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.enums import FindingStatus
from app.core.rbac import MANAGE_FINDINGS, RUN_AI
from app.models.ai_systems import AISystem
from app.models.findings import Finding
from app.models.inventory import DataAsset
from app.models.regulatory import Control
from app.schemas.common import Page
from app.services import findings_service

router = APIRouter(prefix="/findings", tags=["findings"])


class FindingOut(BaseModel):
    id: str
    title: str
    description: str | None
    severity: str
    risk_score: int
    risk_breakdown: dict | None
    status: str
    source: str | None
    data_categories: str | None
    recommended_actions: list | None
    evidence_refs: list | None
    control_id: str | None
    control_code: str | None
    asset_id: str | None
    asset_name: str | None
    vendor_id: str | None
    ai_system_id: str | None
    ai_system_name: str | None
    owner: str | None
    resolution_note: str | None
    detected_at: datetime | None
    due_at: datetime | None
    resolved_at: datetime | None


class StatusChange(BaseModel):
    note: str | None = None


class AssignRequest(BaseModel):
    assignee_id: uuid.UUID | None = None
    owner: str | None = None


def _out(db: Session, f: Finding) -> FindingOut:
    control = db.get(Control, f.control_id) if f.control_id else None
    asset = db.get(DataAsset, f.asset_id) if f.asset_id else None
    ai_system = db.get(AISystem, f.ai_system_id) if f.ai_system_id else None
    return FindingOut(
        id=str(f.id),
        title=f.title,
        description=f.description,
        severity=f.severity,
        risk_score=f.risk_score,
        risk_breakdown=f.risk_breakdown,
        status=f.status,
        source=f.source,
        data_categories=f.data_categories,
        recommended_actions=f.recommended_actions,
        evidence_refs=f.evidence_refs,
        control_id=str(f.control_id) if f.control_id else None,
        control_code=control.code if control else None,
        asset_id=str(f.asset_id) if f.asset_id else None,
        asset_name=asset.display_name or asset.name if asset else None,
        vendor_id=str(f.vendor_id) if f.vendor_id else None,
        ai_system_id=str(f.ai_system_id) if f.ai_system_id else None,
        ai_system_name=ai_system.name if ai_system else None,
        owner=f.owner,
        resolution_note=f.resolution_note,
        detected_at=f.detected_at,
        due_at=f.due_at,
        resolved_at=f.resolved_at,
    )


@router.get("", response_model=Page[FindingOut])
def list_findings(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    severity: str | None = None,
    status: str | None = None,
    control_id: uuid.UUID | None = None,
    ai_system_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 50,
) -> Page[FindingOut]:
    stmt = select(Finding).where(Finding.organization_id == ctx.organization_id)
    if severity:
        stmt = stmt.where(Finding.severity == severity)
    if status:
        stmt = stmt.where(Finding.status == status)
    if control_id:
        stmt = stmt.where(Finding.control_id == control_id)
    if ai_system_id:
        stmt = stmt.where(Finding.ai_system_id == ai_system_id)
    stmt = stmt.order_by(Finding.risk_score.desc(), Finding.detected_at.desc())
    rows, total = paginate(db, stmt, page, page_size)
    return Page(items=[_out(db, f) for f in rows], total=total, page=page, page_size=page_size)


@router.get("/{finding_id}", response_model=FindingOut)
def get_finding(
    finding_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> FindingOut:
    return _out(db, get_org_scoped(db, Finding, finding_id, ctx.organization_id))


@router.patch("/{finding_id}", response_model=FindingOut)
def update_finding(
    finding_id: uuid.UUID,
    payload: StatusChange,
    ctx: AuthContext = Depends(require_capability(MANAGE_FINDINGS)),
    db: Session = Depends(get_db),
) -> FindingOut:
    finding = get_org_scoped(db, Finding, finding_id, ctx.organization_id)
    if payload.note:
        finding.resolution_note = payload.note
    db.commit()
    return _out(db, finding)


@router.post("/{finding_id}/assign", response_model=FindingOut)
def assign_finding(
    finding_id: uuid.UUID,
    payload: AssignRequest,
    ctx: AuthContext = Depends(require_capability(MANAGE_FINDINGS)),
    db: Session = Depends(get_db),
) -> FindingOut:
    finding = get_org_scoped(db, Finding, finding_id, ctx.organization_id)
    finding.assignee_id = payload.assignee_id
    if payload.owner:
        finding.owner = payload.owner
    if finding.status == FindingStatus.OPEN.value:
        finding.status = FindingStatus.ACKNOWLEDGED.value
    record_audit(
        db,
        action="finding.assigned",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="finding",
        entity_id=finding.id,
        metadata={"assignee_id": str(payload.assignee_id) if payload.assignee_id else None},
    )
    db.commit()
    return _out(db, finding)


def _transition(db, ctx, finding_id, new_status, note):
    finding = get_org_scoped(db, Finding, finding_id, ctx.organization_id)
    findings_service.transition_finding(
        db,
        finding,
        new_status=new_status,
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        note=note,
    )
    db.commit()
    return _out(db, finding)


@router.post("/{finding_id}/resolve", response_model=FindingOut)
def resolve_finding(
    finding_id: uuid.UUID,
    payload: StatusChange,
    ctx: AuthContext = Depends(require_capability(MANAGE_FINDINGS)),
    db: Session = Depends(get_db),
) -> FindingOut:
    return _transition(db, ctx, finding_id, FindingStatus.RESOLVED.value, payload.note)


@router.post("/{finding_id}/accept-risk", response_model=FindingOut)
def accept_risk(
    finding_id: uuid.UUID,
    payload: StatusChange,
    ctx: AuthContext = Depends(require_capability(MANAGE_FINDINGS)),
    db: Session = Depends(get_db),
) -> FindingOut:
    return _transition(db, ctx, finding_id, FindingStatus.ACCEPTED_RISK.value, payload.note)


@router.post("/{finding_id}/investigate")
def investigate_finding(
    finding_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(RUN_AI)),
    db: Session = Depends(get_db),
) -> dict:
    """Run an AI investigation grounded in the platform's evidence (never raw PII)."""
    from app.services.ai_service import investigate

    finding = get_org_scoped(db, Finding, finding_id, ctx.organization_id)
    investigation = investigate(db, ctx.organization, finding, user_id=ctx.user.id)
    record_audit(
        db,
        action="ai.investigation_run",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="finding",
        entity_id=finding.id,
        metadata={"mode": investigation.mode, "status": investigation.status},
    )
    db.commit()
    return {"investigation_id": str(investigation.id), "status": investigation.status}
