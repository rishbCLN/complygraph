"""Control library + assessment endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.controls.effective_date import control_temporal_status
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.core.rbac import ASSESS_CONTROLS
from app.models.evidence import ControlEvidence, Evidence
from app.models.findings import Finding
from app.models.regulatory import Control, ControlAssessment, Obligation, Regulation
from app.services import assessment_service, mapping_service
from app.services.assessment_service import get_assessment_date
from app.services.evidence_service import compute_freshness

router = APIRouter(prefix="/controls", tags=["controls"])


class ControlOut(BaseModel):
    id: str
    code: str
    title: str
    description: str | None
    category: str
    legal_reference: str | None
    source_section: str | None
    regulation_name: str | None
    effective_from: datetime | None
    temporal_status: str
    severity_default: str
    latest_status: str | None
    latest_score: float | None


class AssessmentOut(BaseModel):
    id: str
    control_id: str
    status: str
    score: float
    assessment_date: datetime
    reason: str | None
    evidence_count: int
    automated: bool


@router.get("", response_model=list[ControlOut])
def list_controls(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    category: str | None = None,
    search: str | None = Query(None),
) -> list[ControlOut]:
    assessment_date = get_assessment_date(ctx.organization)
    stmt = select(Control)
    if category:
        stmt = stmt.where(Control.category == category)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Control.code.ilike(like), Control.title.ilike(like), Control.description.ilike(like)))
    stmt = stmt.order_by(Control.code)
    out = []
    for c in db.scalars(stmt):
        obligation = db.get(Obligation, c.obligation_id)
        regulation = db.get(Regulation, obligation.regulation_id) if obligation else None
        latest = assessment_service.latest_assessment(db, ctx.organization_id, c.id)
        out.append(
            ControlOut(
                id=str(c.id),
                code=c.code,
                title=c.title,
                description=c.description,
                category=c.category,
                legal_reference=obligation.legal_reference if obligation else None,
                source_section=obligation.source_section if obligation else None,
                regulation_name=regulation.name if regulation else None,
                effective_from=c.effective_from,
                temporal_status=control_temporal_status(c.effective_from, assessment_date),
                severity_default=c.severity_default,
                latest_status=latest.status if latest else None,
                latest_score=latest.score if latest else None,
            )
        )
    return out


@router.get("/{control_id}", response_model=ControlOut)
def get_control(
    control_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> ControlOut:
    c = db.get(Control, control_id)
    if not c:
        raise NotFoundError("Control not found.")
    assessment_date = get_assessment_date(ctx.organization)
    obligation = db.get(Obligation, c.obligation_id)
    regulation = db.get(Regulation, obligation.regulation_id) if obligation else None
    latest = assessment_service.latest_assessment(db, ctx.organization_id, c.id)
    return ControlOut(
        id=str(c.id),
        code=c.code,
        title=c.title,
        description=c.description,
        category=c.category,
        legal_reference=obligation.legal_reference if obligation else None,
        source_section=obligation.source_section if obligation else None,
        regulation_name=regulation.name if regulation else None,
        effective_from=c.effective_from,
        temporal_status=control_temporal_status(c.effective_from, assessment_date),
        severity_default=c.severity_default,
        latest_status=latest.status if latest else None,
        latest_score=latest.score if latest else None,
    )


class ControlEvidenceOut(BaseModel):
    id: str
    name: str
    type: str
    status: str
    relation_type: str
    collected_at: datetime | None
    expires_at: datetime | None
    hash: str | None


@router.get("/{control_id}/evidence", response_model=list[ControlEvidenceOut])
def get_control_evidence(
    control_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[ControlEvidenceOut]:
    assessment_date = get_assessment_date(ctx.organization)
    rows = db.execute(
        select(Evidence, ControlEvidence)
        .join(ControlEvidence, ControlEvidence.evidence_id == Evidence.id)
        .where(ControlEvidence.control_id == control_id, Evidence.organization_id == ctx.organization_id)
    ).all()
    out = []
    for ev, ce in rows:
        status = compute_freshness(ev.collected_at, ev.expires_at, assessment_date)
        out.append(
            ControlEvidenceOut(
                id=str(ev.id),
                name=ev.name,
                type=ev.type,
                status=status,
                relation_type=ce.relation_type,
                collected_at=ev.collected_at,
                expires_at=ev.expires_at,
                hash=ev.hash,
            )
        )
    return out


class MappedControlOut(BaseModel):
    id: str
    code: str
    title: str
    category: str
    regulation_id: str | None
    regulation_name: str | None


class ControlMappingOut(BaseModel):
    id: str
    relation_type: str
    rationale: str | None
    confidence: float
    system: bool
    direction: str
    other: MappedControlOut


class ReusableEvidenceOut(BaseModel):
    evidence_id: str
    evidence_name: str
    evidence_type: str
    status: str
    relation_type_on_source: str
    via_mapping_id: str
    mapping_relation: str
    mapping_confidence: float
    source_control: MappedControlOut
    requires_review: bool


@router.get("/{control_id}/mappings", response_model=list[ControlMappingOut])
def get_control_mappings(
    control_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[ControlMappingOut]:
    """Cross-framework controls mapped to/from this control."""
    return [
        ControlMappingOut(**m) for m in mapping_service.mappings_for_control(db, ctx.organization_id, control_id)
    ]


@router.get("/{control_id}/reusable-evidence", response_model=list[ReusableEvidenceOut])
def get_reusable_evidence(
    control_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[ReusableEvidenceOut]:
    """Evidence collected for mapped controls that could satisfy this control.

    Advisory only: every candidate is flagged requires_review and must be
    explicitly linked before it counts toward this control's assessment.
    """
    return [
        ReusableEvidenceOut(**e)
        for e in mapping_service.reusable_evidence(db, ctx.organization_id, control_id)
    ]


@router.get("/{control_id}/assessment", response_model=AssessmentOut | None)
def get_control_assessment(
    control_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> AssessmentOut | None:
    latest = assessment_service.latest_assessment(db, ctx.organization_id, control_id)
    if not latest:
        return None
    return AssessmentOut(
        id=str(latest.id),
        control_id=str(latest.control_id),
        status=latest.status,
        score=latest.score,
        assessment_date=latest.assessment_date,
        reason=latest.reason,
        evidence_count=latest.evidence_count,
        automated=latest.automated,
    )


@router.post("/{control_id}/assess", response_model=AssessmentOut)
def assess_control(
    control_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(ASSESS_CONTROLS)),
    db: Session = Depends(get_db),
) -> AssessmentOut:
    """Re-run the deterministic evaluator for this control against current state."""
    control = db.get(Control, control_id)
    if not control:
        raise NotFoundError("Control not found.")
    assessment = assessment_service.assess_control(db, ctx.organization, control)
    record_audit(
        db,
        action="control.assessed",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="control",
        entity_id=control.id,
        metadata={"status": assessment.status, "score": assessment.score},
    )
    db.commit()
    db.refresh(assessment)
    return AssessmentOut(
        id=str(assessment.id),
        control_id=str(assessment.control_id),
        status=assessment.status,
        score=assessment.score,
        assessment_date=assessment.assessment_date,
        reason=assessment.reason,
        evidence_count=assessment.evidence_count,
        automated=assessment.automated,
    )
