"""Risk register service.

Qualitative scoring is likelihood x impact on a 1..5 scale (score 1..25), mapped
to a severity band. The quantitative view derives annualised loss expectancy
(ALE = SLE x ARO) when both inputs are present. Acceptance is an explicit,
attributable action with a rationale and a review-expiry date.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.enums import RiskCategory, RiskStatus, TreatmentStrategy, risk_severity
from app.core.errors import NotFoundError, ValidationError
from app.models.risk import Risk

_CATEGORIES = {c.value for c in RiskCategory}
_STATUSES = {s.value for s in RiskStatus}
_STRATEGIES = {s.value for s in TreatmentStrategy}

# Fields a client may set on create/update (excludes workflow-managed fields).
_EDITABLE = {
    "title",
    "description",
    "category",
    "owner",
    "inherent_likelihood",
    "inherent_impact",
    "residual_likelihood",
    "residual_impact",
    "treatment_strategy",
    "treatment_plan",
    "single_loss_expectancy",
    "annual_rate_of_occurrence",
    "rto_hours",
    "rpo_hours",
    "max_tolerable_downtime_hours",
    "business_impact",
    "review_due_at",
    "control_id",
    "finding_id",
    "vendor_id",
    "ai_system_id",
    "processing_activity_id",
    "status",
}


def _clamp_1_5(value: int | None, default: int) -> int:
    if value is None:
        return default
    return max(1, min(5, int(value)))


def annualised_loss_expectancy(risk: Risk) -> float | None:
    if risk.single_loss_expectancy is None or risk.annual_rate_of_occurrence is None:
        return None
    return round(risk.single_loss_expectancy * risk.annual_rate_of_occurrence, 2)


def score_view(risk: Risk) -> dict:
    inherent = risk.inherent_likelihood * risk.inherent_impact
    residual = risk.residual_likelihood * risk.residual_impact
    return {
        "inherent_score": inherent,
        "inherent_severity": risk_severity(inherent),
        "residual_score": residual,
        "residual_severity": risk_severity(residual),
        "ale": annualised_loss_expectancy(risk),
    }


def _validate_enums(data: dict) -> None:
    if "category" in data and data["category"] is not None and data["category"] not in _CATEGORIES:
        raise ValidationError(f"category must be one of {sorted(_CATEGORIES)}")
    if "status" in data and data["status"] is not None and data["status"] not in _STATUSES:
        raise ValidationError(f"status must be one of {sorted(_STATUSES)}")
    if (
        "treatment_strategy" in data
        and data["treatment_strategy"] is not None
        and data["treatment_strategy"] not in _STRATEGIES
    ):
        raise ValidationError(f"treatment_strategy must be one of {sorted(_STRATEGIES)}")


def create_risk(db: Session, org_id: uuid.UUID, user_id: uuid.UUID | None, data: dict) -> Risk:
    if not (data.get("title") or "").strip():
        raise ValidationError("A risk requires a title.")
    _validate_enums(data)
    risk = Risk(
        organization_id=org_id,
        title=data["title"].strip(),
        description=data.get("description"),
        category=data.get("category") or RiskCategory.COMPLIANCE.value,
        status=data.get("status") or RiskStatus.IDENTIFIED.value,
        owner=data.get("owner"),
        inherent_likelihood=_clamp_1_5(data.get("inherent_likelihood"), 3),
        inherent_impact=_clamp_1_5(data.get("inherent_impact"), 3),
        residual_likelihood=_clamp_1_5(data.get("residual_likelihood"), 3),
        residual_impact=_clamp_1_5(data.get("residual_impact"), 3),
        treatment_strategy=data.get("treatment_strategy") or TreatmentStrategy.MITIGATE.value,
        treatment_plan=data.get("treatment_plan"),
        single_loss_expectancy=data.get("single_loss_expectancy"),
        annual_rate_of_occurrence=data.get("annual_rate_of_occurrence"),
        rto_hours=data.get("rto_hours"),
        rpo_hours=data.get("rpo_hours"),
        max_tolerable_downtime_hours=data.get("max_tolerable_downtime_hours"),
        business_impact=data.get("business_impact"),
        review_due_at=data.get("review_due_at"),
        control_id=data.get("control_id"),
        finding_id=data.get("finding_id"),
        vendor_id=data.get("vendor_id"),
        ai_system_id=data.get("ai_system_id"),
        processing_activity_id=data.get("processing_activity_id"),
        created_by=user_id,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(risk)
    db.flush()
    _dispatch_risk_event(db, org_id, "risk.created", risk)
    return risk


def _dispatch_risk_event(db, org_id, event, risk, *, previous_status=None) -> None:
    from app.services import webhook_service

    payload = {
        "id": str(risk.id),
        "title": risk.title,
        "status": risk.status,
        "category": risk.category,
        "owner": risk.owner,
    }
    if previous_status is not None:
        payload["previous_status"] = previous_status
    webhook_service.dispatch_event(db, org_id, event, payload)


def get_risk(db: Session, org_id: uuid.UUID, risk_id: uuid.UUID) -> Risk:
    risk = db.get(Risk, risk_id)
    if risk is None or risk.organization_id != org_id:
        raise NotFoundError("Risk not found.")
    return risk


def list_risks(
    db: Session,
    org_id: uuid.UUID,
    *,
    status: str | None = None,
    category: str | None = None,
) -> list[Risk]:
    stmt = select(Risk).where(Risk.organization_id == org_id)
    if status:
        stmt = stmt.where(Risk.status == status)
    if category:
        stmt = stmt.where(Risk.category == category)
    return list(db.scalars(stmt.order_by(Risk.created_at.desc())))


def update_risk(db: Session, org_id: uuid.UUID, risk_id: uuid.UUID, data: dict) -> Risk:
    risk = get_risk(db, org_id, risk_id)
    _validate_enums(data)
    previous_status = risk.status
    for key, value in data.items():
        if key not in _EDITABLE:
            continue
        if key in {"inherent_likelihood", "inherent_impact", "residual_likelihood", "residual_impact"}:
            value = _clamp_1_5(value, getattr(risk, key))
        setattr(risk, key, value)
    risk.updated_at = utcnow()
    db.flush()
    if risk.status != previous_status:
        _dispatch_risk_event(
            db, org_id, "risk.status_changed", risk, previous_status=previous_status
        )
    return risk


def accept_risk(
    db: Session,
    org_id: uuid.UUID,
    risk_id: uuid.UUID,
    user_id: uuid.UUID | None,
    *,
    rationale: str,
    expires_at: datetime | None,
) -> Risk:
    if not (rationale or "").strip():
        raise ValidationError("Risk acceptance requires a rationale.")
    risk = get_risk(db, org_id, risk_id)
    previous_status = risk.status
    risk.status = RiskStatus.ACCEPTED.value
    risk.treatment_strategy = TreatmentStrategy.ACCEPT.value
    risk.accepted_by = user_id
    risk.accepted_at = utcnow()
    risk.acceptance_rationale = rationale.strip()
    risk.acceptance_expires_at = expires_at
    if expires_at is not None:
        risk.review_due_at = expires_at
    risk.updated_at = utcnow()
    db.flush()
    if risk.status != previous_status:
        _dispatch_risk_event(
            db, org_id, "risk.status_changed", risk, previous_status=previous_status
        )
    return risk


def close_risk(db: Session, org_id: uuid.UUID, risk_id: uuid.UUID) -> Risk:
    risk = get_risk(db, org_id, risk_id)
    previous_status = risk.status
    risk.status = RiskStatus.CLOSED.value
    risk.updated_at = utcnow()
    db.flush()
    if risk.status != previous_status:
        _dispatch_risk_event(
            db, org_id, "risk.status_changed", risk, previous_status=previous_status
        )
    return risk


def delete_risk(db: Session, org_id: uuid.UUID, risk_id: uuid.UUID) -> Risk:
    risk = get_risk(db, org_id, risk_id)
    db.delete(risk)
    db.flush()
    return risk


def register_summary(db: Session, org_id: uuid.UUID) -> dict:
    risks = list(db.scalars(select(Risk).where(Risk.organization_id == org_id)))
    by_status: dict[str, int] = {}
    by_severity: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    # 5x5 residual heatmap indexed as heatmap[impact][likelihood].
    heatmap = [[0 for _ in range(5)] for _ in range(5)]
    total_ale = 0.0
    open_statuses = {
        RiskStatus.IDENTIFIED.value,
        RiskStatus.ASSESSED.value,
        RiskStatus.TREATING.value,
    }
    open_count = 0
    for r in risks:
        by_status[r.status] = by_status.get(r.status, 0) + 1
        residual = r.residual_likelihood * r.residual_impact
        by_severity[risk_severity(residual)] = by_severity.get(risk_severity(residual), 0) + 1
        heatmap[r.residual_impact - 1][r.residual_likelihood - 1] += 1
        ale = annualised_loss_expectancy(r)
        if ale is not None:
            total_ale += ale
        if r.status in open_statuses:
            open_count += 1

    return {
        "total": len(risks),
        "open": open_count,
        "by_status": by_status,
        "by_severity": by_severity,
        "heatmap": heatmap,
        "total_ale": round(total_ale, 2),
    }
