"""Assessment service.

Builds a ControlContext from the organization's current state, runs each
applicable control evaluator (respecting effective dates), and persists
ControlAssessment rows. Upcoming controls are reported as UPCOMING, never as
active failures.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.controls.effective_date import is_control_active
from app.controls.engine import ControlContext, ControlEvaluation, evaluate
from app.core.database import utcnow
from app.core.enums import (
    Classification,
    ControlStatus,
    EvidenceStatus,
)
from app.models.evidence import ControlEvidence, Evidence
from app.models.identity import Organization
from app.models.inventory import (
    AssetField,
    DataAsset,
    DataFlow,
    ProcessingActivity,
    Vendor,
)
from app.models.regulatory import Control, ControlAssessment
from app.services.evidence_service import compute_freshness

_PERSONAL = {Classification.PERSONAL_DATA.value, Classification.SENSITIVE_PERSONAL_DATA.value}


def get_assessment_date(org: Organization) -> datetime:
    if org.assessment_date is not None:
        dt = org.assessment_date
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def build_context(db: Session, org: Organization) -> ControlContext:
    org_id = org.id
    assessment_date = get_assessment_date(org)

    assets = list(db.scalars(select(DataAsset).where(DataAsset.organization_id == org_id)))
    fields_by_asset: dict[uuid.UUID, list[AssetField]] = {}
    for f in db.scalars(
        select(AssetField).join(DataAsset).where(DataAsset.organization_id == org_id)
    ):
        fields_by_asset.setdefault(f.asset_id, []).append(f)

    def asset_dict(a: DataAsset) -> dict:
        return {
            "id": a.id,
            "name": a.name,
            "display_name": a.display_name,
            "classification": a.classification,
            "sensitivity_level": a.sensitivity_level,
            "row_count": a.row_count,
            "asset_type": a.asset_type,
        }

    def asset_is_personal(a: DataAsset) -> bool:
        if a.classification in _PERSONAL:
            return True
        return any(f.classification in _PERSONAL for f in fields_by_asset.get(a.id, []))

    all_assets = [asset_dict(a) for a in assets]
    personal_assets = [asset_dict(a) for a in assets if asset_is_personal(a)]

    flows = [
        {
            "id": f.id,
            "vendor_id": f.vendor_id,
            "flow_type": f.flow_type,
            "contains_personal_data": f.contains_personal_data,
            "cross_border": f.cross_border,
        }
        for f in db.scalars(select(DataFlow).where(DataFlow.organization_id == org_id))
    ]
    vendors = [
        {
            "id": v.id,
            "name": v.name,
            "contract_status": v.contract_status,
            "country": v.country,
        }
        for v in db.scalars(select(Vendor).where(Vendor.organization_id == org_id))
    ]
    activities = [
        {
            "id": p.id,
            "purpose": p.purpose,
            "has_notice": p.has_notice,
            "has_consent": p.has_consent,
            "retention_period_days": p.retention_period_days,
        }
        for p in db.scalars(
            select(ProcessingActivity).where(ProcessingActivity.organization_id == org_id)
        )
    ]

    # Evidence indexed by control code (via control_evidence linkage).
    evidence_by_control: dict[str, list[dict]] = {}
    rows = db.execute(
        select(Control.code, Evidence)
        .join(ControlEvidence, ControlEvidence.control_id == Control.id)
        .join(Evidence, Evidence.id == ControlEvidence.evidence_id)
        .where(Evidence.organization_id == org_id)
    ).all()
    for code, ev in rows:
        status = compute_freshness(ev.collected_at, ev.expires_at, assessment_date)
        evidence_by_control.setdefault(code, []).append(
            {"id": ev.id, "name": ev.name, "status": status, "type": ev.type}
        )

    # Operational flags from seeded configuration flags stored on org.plan? Use simple heuristics.
    from app.models.operations import BreachIncident, DataSubjectRequest

    dsr_configured = db.scalar(
        select(DataSubjectRequest.id).where(DataSubjectRequest.organization_id == org_id).limit(1)
    ) is not None
    breach_configured = db.scalar(
        select(BreachIncident.id).where(BreachIncident.organization_id == org_id).limit(1)
    ) is not None

    return ControlContext(
        organization_id=org_id,
        assessment_date=assessment_date,
        personal_data_assets=personal_assets,
        all_assets=all_assets,
        flows=flows,
        vendors=vendors,
        processing_activities=activities,
        evidence_by_control=evidence_by_control,
        dsr_configured=dsr_configured,
        breach_workflow_configured=breach_configured,
        flags={
            "deletion_last_status": "FAILED",  # seeded failure scenario; overridable
        },
    )


def assess_control(db: Session, org: Organization, control: Control) -> ControlAssessment:
    ctx = build_context(db, org)
    return _assess_one(db, org, control, ctx)


def _assess_one(
    db: Session, org: Organization, control: Control, ctx: ControlContext
) -> ControlAssessment:
    if not is_control_active(control.effective_from, ctx.assessment_date):
        evaluation = ControlEvaluation(
            status=ControlStatus.UPCOMING.value,
            score=0.0,
            reason=(
                "This control is not yet in force at the current assessment date. "
                "It is displayed for preparation, not as a current failure."
            ),
        )
    else:
        evaluation = evaluate(control.evaluator_key, ctx, control.code)

    assessment = ControlAssessment(
        organization_id=org.id,
        control_id=control.id,
        status=evaluation.status,
        score=evaluation.score,
        assessment_date=ctx.assessment_date,
        reason=evaluation.reason,
        evidence_count=len(evaluation.evidence_ids),
        automated=True,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(assessment)
    return assessment


def assess_all(db: Session, org: Organization) -> list[tuple[Control, ControlAssessment, ControlEvaluation]]:
    """Assess every control and return (control, assessment, evaluation) tuples."""
    ctx = build_context(db, org)
    controls = list(db.scalars(select(Control)))
    results = []
    for control in controls:
        if not is_control_active(control.effective_from, ctx.assessment_date):
            evaluation = ControlEvaluation(
                status=ControlStatus.UPCOMING.value,
                score=0.0,
                reason=(
                    "This control is not yet in force at the current assessment date. "
                    "Displayed for preparation, not as a current failure."
                ),
            )
        else:
            evaluation = evaluate(control.evaluator_key, ctx, control.code)
        assessment = ControlAssessment(
            organization_id=org.id,
            control_id=control.id,
            status=evaluation.status,
            score=evaluation.score,
            assessment_date=ctx.assessment_date,
            reason=evaluation.reason,
            evidence_count=len(evaluation.evidence_ids),
            automated=True,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(assessment)
        results.append((control, assessment, evaluation))
    return results


def latest_assessment(db: Session, org_id: uuid.UUID, control_id: uuid.UUID) -> ControlAssessment | None:
    return db.scalar(
        select(ControlAssessment)
        .where(
            ControlAssessment.organization_id == org_id,
            ControlAssessment.control_id == control_id,
        )
        .order_by(ControlAssessment.created_at.desc())
        .limit(1)
    )
