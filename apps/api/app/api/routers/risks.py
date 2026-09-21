"""Risk register endpoints (feature #3)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.rbac import MANAGE_RISK
from app.models.risk import Risk
from app.services import risk_service

router = APIRouter(prefix="/risks", tags=["risks"])


class RiskIn(BaseModel):
    title: str
    description: str | None = None
    category: str | None = None
    owner: str | None = None
    inherent_likelihood: int | None = None
    inherent_impact: int | None = None
    residual_likelihood: int | None = None
    residual_impact: int | None = None
    treatment_strategy: str | None = None
    treatment_plan: str | None = None
    single_loss_expectancy: float | None = None
    annual_rate_of_occurrence: float | None = None
    rto_hours: int | None = None
    rpo_hours: int | None = None
    max_tolerable_downtime_hours: int | None = None
    business_impact: str | None = None
    review_due_at: datetime | None = None
    control_id: uuid.UUID | None = None
    finding_id: uuid.UUID | None = None
    vendor_id: uuid.UUID | None = None
    ai_system_id: uuid.UUID | None = None
    processing_activity_id: uuid.UUID | None = None


class RiskPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    status: str | None = None
    owner: str | None = None
    inherent_likelihood: int | None = None
    inherent_impact: int | None = None
    residual_likelihood: int | None = None
    residual_impact: int | None = None
    treatment_strategy: str | None = None
    treatment_plan: str | None = None
    single_loss_expectancy: float | None = None
    annual_rate_of_occurrence: float | None = None
    rto_hours: int | None = None
    rpo_hours: int | None = None
    max_tolerable_downtime_hours: int | None = None
    business_impact: str | None = None
    review_due_at: datetime | None = None
    control_id: uuid.UUID | None = None
    finding_id: uuid.UUID | None = None
    vendor_id: uuid.UUID | None = None
    ai_system_id: uuid.UUID | None = None
    processing_activity_id: uuid.UUID | None = None


class AcceptIn(BaseModel):
    rationale: str
    expires_at: datetime | None = None


class RiskOut(BaseModel):
    id: str
    title: str
    description: str | None
    category: str
    status: str
    owner: str | None
    inherent_likelihood: int
    inherent_impact: int
    residual_likelihood: int
    residual_impact: int
    inherent_score: int
    inherent_severity: str
    residual_score: int
    residual_severity: str
    treatment_strategy: str
    treatment_plan: str | None
    single_loss_expectancy: float | None
    annual_rate_of_occurrence: float | None
    ale: float | None
    rto_hours: int | None
    rpo_hours: int | None
    max_tolerable_downtime_hours: int | None
    business_impact: str | None
    accepted_by: str | None
    accepted_at: datetime | None
    acceptance_rationale: str | None
    acceptance_expires_at: datetime | None
    review_due_at: datetime | None
    control_id: str | None
    finding_id: str | None
    vendor_id: str | None
    ai_system_id: str | None
    processing_activity_id: str | None
    created_at: datetime | None


class RiskSummaryOut(BaseModel):
    total: int
    open: int
    by_status: dict[str, int]
    by_severity: dict[str, int]
    heatmap: list[list[int]]
    total_ale: float


def _out(risk: Risk) -> RiskOut:
    scores = risk_service.score_view(risk)
    return RiskOut(
        id=str(risk.id),
        title=risk.title,
        description=risk.description,
        category=risk.category,
        status=risk.status,
        owner=risk.owner,
        inherent_likelihood=risk.inherent_likelihood,
        inherent_impact=risk.inherent_impact,
        residual_likelihood=risk.residual_likelihood,
        residual_impact=risk.residual_impact,
        inherent_score=scores["inherent_score"],
        inherent_severity=scores["inherent_severity"],
        residual_score=scores["residual_score"],
        residual_severity=scores["residual_severity"],
        treatment_strategy=risk.treatment_strategy,
        treatment_plan=risk.treatment_plan,
        single_loss_expectancy=risk.single_loss_expectancy,
        annual_rate_of_occurrence=risk.annual_rate_of_occurrence,
        ale=scores["ale"],
        rto_hours=risk.rto_hours,
        rpo_hours=risk.rpo_hours,
        max_tolerable_downtime_hours=risk.max_tolerable_downtime_hours,
        business_impact=risk.business_impact,
        accepted_by=str(risk.accepted_by) if risk.accepted_by else None,
        accepted_at=risk.accepted_at,
        acceptance_rationale=risk.acceptance_rationale,
        acceptance_expires_at=risk.acceptance_expires_at,
        review_due_at=risk.review_due_at,
        control_id=str(risk.control_id) if risk.control_id else None,
        finding_id=str(risk.finding_id) if risk.finding_id else None,
        vendor_id=str(risk.vendor_id) if risk.vendor_id else None,
        ai_system_id=str(risk.ai_system_id) if risk.ai_system_id else None,
        processing_activity_id=str(risk.processing_activity_id) if risk.processing_activity_id else None,
        created_at=risk.created_at,
    )


@router.get("", response_model=list[RiskOut])
def list_risks(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    status: str | None = Query(None),
    category: str | None = Query(None),
) -> list[RiskOut]:
    return [
        _out(r)
        for r in risk_service.list_risks(db, ctx.organization_id, status=status, category=category)
    ]


@router.get("/summary", response_model=RiskSummaryOut)
def risk_summary(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> RiskSummaryOut:
    return RiskSummaryOut(**risk_service.register_summary(db, ctx.organization_id))


@router.post("", response_model=RiskOut, status_code=201)
def create_risk(
    payload: RiskIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_RISK)),
    db: Session = Depends(get_db),
) -> RiskOut:
    risk = risk_service.create_risk(db, ctx.organization_id, ctx.user.id, payload.model_dump(exclude_unset=True))
    record_audit(
        db,
        action="risk.created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="risk",
        entity_id=risk.id,
        metadata={"category": risk.category},
    )
    db.commit()
    db.refresh(risk)
    return _out(risk)


@router.get("/{risk_id}", response_model=RiskOut)
def get_risk(
    risk_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> RiskOut:
    return _out(risk_service.get_risk(db, ctx.organization_id, risk_id))


@router.patch("/{risk_id}", response_model=RiskOut)
def update_risk(
    risk_id: uuid.UUID,
    payload: RiskPatch,
    ctx: AuthContext = Depends(require_capability(MANAGE_RISK)),
    db: Session = Depends(get_db),
) -> RiskOut:
    risk = risk_service.update_risk(
        db, ctx.organization_id, risk_id, payload.model_dump(exclude_unset=True)
    )
    record_audit(
        db,
        action="risk.updated",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="risk",
        entity_id=risk.id,
    )
    db.commit()
    db.refresh(risk)
    return _out(risk)


@router.post("/{risk_id}/accept", response_model=RiskOut)
def accept_risk(
    risk_id: uuid.UUID,
    payload: AcceptIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_RISK)),
    db: Session = Depends(get_db),
) -> RiskOut:
    risk = risk_service.accept_risk(
        db,
        ctx.organization_id,
        risk_id,
        ctx.user.id,
        rationale=payload.rationale,
        expires_at=payload.expires_at,
    )
    record_audit(
        db,
        action="risk.accepted",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="risk",
        entity_id=risk.id,
    )
    db.commit()
    db.refresh(risk)
    return _out(risk)


@router.post("/{risk_id}/close", response_model=RiskOut)
def close_risk(
    risk_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_RISK)),
    db: Session = Depends(get_db),
) -> RiskOut:
    risk = risk_service.close_risk(db, ctx.organization_id, risk_id)
    record_audit(
        db,
        action="risk.closed",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="risk",
        entity_id=risk.id,
    )
    db.commit()
    db.refresh(risk)
    return _out(risk)


@router.delete("/{risk_id}", status_code=204)
def delete_risk(
    risk_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_RISK)),
    db: Session = Depends(get_db),
) -> None:
    risk_service.delete_risk(db, ctx.organization_id, risk_id)
    record_audit(
        db,
        action="risk.deleted",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="risk",
        entity_id=risk_id,
    )
    db.commit()
