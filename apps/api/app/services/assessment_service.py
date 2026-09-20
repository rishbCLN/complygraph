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

    # AI-system inventory: one derived-fact dict per system. Feeds the
    # applicability engine and the AI-specific evaluators.
    from app.models.ai_systems import AISystem
    from app.services import ai_system_service

    ai_systems_facts = [
        ai_system_service.derive_facts(db, system)
        for system in db.scalars(
            select(AISystem).where(AISystem.organization_id == org_id)
        )
    ]

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
        ai_systems=ai_systems_facts,
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
        evaluation = evaluate(control.evaluator_key, ctx, control.code, control.applies_to)

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
            evaluation = evaluate(control.evaluator_key, ctx, control.code, control.applies_to)
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


def analyze_system(
    db: Session, org: Organization, system, persist: bool = False
) -> dict:
    """Analyze a single AI system on demand and return a per-system report.

    Runs the deterministic engine with the control context scoped to just this
    system's derived facts, so applicability and every AI evaluator answer
    "how does *this* system do?".

    Controls are split into ``system``-scoped (their applies_to narrows to a
    sector/type/condition) and ``org_wide`` (e.g. CERT-In) so the UI can show why
    each control is in play. Only AI-scoped controls are returned; org-level DPDP
    controls are covered by the org-wide assessment.

    When ``persist`` is True, the run is recorded as an ``AISystemSnapshot`` and
    the report includes a ``changes`` block diffing this run against the previous
    snapshot (newly failing / resolved / regressed / improved controls). When
    False the analysis is read-only and ``changes`` is diffed against the latest
    stored snapshot without writing a new one.
    """
    from app.controls.applicability import is_ai_scoped, is_specific_scope
    from app.services import ai_system_service

    facts, provenance = ai_system_service.derive_facts_with_provenance(db, system)
    ctx = build_context(db, org)
    ctx.ai_systems = [facts]  # scope evaluation to this system only

    controls = list(db.scalars(select(Control)))
    entries: list[dict] = []
    by_status: dict[str, int] = {}
    applicable = 0

    for control in controls:
        if not is_ai_scoped(control.applies_to):
            continue
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
            evaluation = evaluate(control.evaluator_key, ctx, control.code, control.applies_to)

        is_applicable = evaluation.status != ControlStatus.NOT_APPLICABLE.value
        if is_applicable:
            applicable += 1
        by_status[evaluation.status] = by_status.get(evaluation.status, 0) + 1
        entries.append(
            {
                "code": control.code,
                "title": control.title,
                "category": control.category,
                "severity": control.severity_default,
                "evaluator_key": control.evaluator_key,
                "scope": "system" if is_specific_scope(control.applies_to) else "org_wide",
                "applicable": is_applicable,
                "status": evaluation.status,
                "reason": evaluation.reason,
                "recommended_actions": evaluation.recommended_actions,
            }
        )

    # Stable ordering: failing/attention items first, then by code.
    entries.sort(key=lambda e: (_STATUS_ORDER.get(e["status"], 9), e["code"]))

    control_statuses = {e["code"]: e["status"] for e in entries}
    summary = {
        "total": len(entries),
        "applicable": applicable,
        "by_status": by_status,
    }

    changes = _diff_against_last_snapshot(db, system, control_statuses)
    if persist:
        _record_snapshot(db, org, system, ctx.assessment_date, control_statuses, facts, summary)

    return {
        "system_id": str(system.id),
        "system_name": system.name,
        "assessment_date": ctx.assessment_date.isoformat(),
        "facts": facts,
        "fact_provenance": provenance,
        "summary": summary,
        "controls": entries,
        "changes": changes,
    }


# Lower rank = more attention-worthy. Used for ordering AND to classify a status
# transition as a regression (rank decreased) vs an improvement (rank increased).
_STATUS_ORDER = {
    ControlStatus.FAIL.value: 0,
    ControlStatus.NO_EVIDENCE.value: 1,
    ControlStatus.NEEDS_REVIEW.value: 2,
    ControlStatus.PARTIAL.value: 3,
    ControlStatus.UPCOMING.value: 4,
    ControlStatus.PASS.value: 5,
    ControlStatus.NOT_APPLICABLE.value: 6,
}


def _diff_against_last_snapshot(
    db: Session, system, current: dict[str, str]
) -> dict:
    """Compare current per-control statuses to the most recent stored snapshot.

    Returns a change-impact report classifying each control transition as
    regressed (posture got worse), improved (got better), added, or removed. The
    first-ever analysis has no baseline, so ``is_baseline`` is True and no
    transitions are reported.
    """
    from app.models.ai_systems import AISystemSnapshot

    last = db.scalar(
        select(AISystemSnapshot)
        .where(AISystemSnapshot.ai_system_id == system.id)
        .order_by(AISystemSnapshot.created_at.desc())
        .limit(1)
    )
    if last is None or not last.control_statuses:
        return {
            "is_baseline": True,
            "previous_at": None,
            "regressed": [],
            "improved": [],
            "added": [],
            "removed": [],
            "unchanged": len(current),
        }

    previous: dict[str, str] = dict(last.control_statuses)
    regressed: list[dict] = []
    improved: list[dict] = []
    added: list[dict] = []
    unchanged = 0

    for code, status in current.items():
        if code not in previous:
            added.append({"code": code, "status": status})
            continue
        prev_status = previous[code]
        if status == prev_status:
            unchanged += 1
            continue
        transition = {"code": code, "from": prev_status, "to": status}
        # Lower rank == worse. A drop in rank is a regression.
        if _STATUS_ORDER.get(status, 9) < _STATUS_ORDER.get(prev_status, 9):
            regressed.append(transition)
        else:
            improved.append(transition)

    removed = [
        {"code": code, "status": previous[code]}
        for code in previous
        if code not in current
    ]

    return {
        "is_baseline": False,
        "previous_at": last.created_at.isoformat() if last.created_at else None,
        "regressed": regressed,
        "improved": improved,
        "added": added,
        "removed": removed,
        "unchanged": unchanged,
    }


def _record_snapshot(
    db: Session, org, system, assessment_date, control_statuses, facts, summary
) -> None:
    """Persist a point-in-time snapshot of this system's analysis result."""
    from app.models.ai_systems import AISystemSnapshot

    db.add(
        AISystemSnapshot(
            ai_system_id=system.id,
            organization_id=org.id,
            assessment_date=assessment_date,
            control_statuses=control_statuses,
            facts=facts,
            summary=summary,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
    )
    db.flush()


def analyze_all_systems(db: Session, org: Organization, persist: bool = True) -> dict:
    """Analyze every AI system in the org in one pass and return a rollup.

    Builds the control context once and reuses it per system (scoping
    ``ctx.ai_systems`` to each system in turn) so bulk analysis of a large
    inventory does not rebuild the org context N times. Each system's snapshot is
    persisted (when ``persist``) so the change-impact trail advances uniformly.

    Returns a portfolio-level rollup: per-system summaries plus aggregate counts
    of systems with any regression / any failing control, which is what a CISO
    needs to triage an inventory rather than click through systems one by one.
    """
    from app.controls.applicability import is_ai_scoped, is_specific_scope
    from app.services import ai_system_service
    from app.models.ai_systems import AISystem

    systems = list(
        db.scalars(select(AISystem).where(AISystem.organization_id == org.id))
    )
    ctx = build_context(db, org)
    controls = [c for c in db.scalars(select(Control)) if is_ai_scoped(c.applies_to)]

    per_system: list[dict] = []
    total_regressions = 0
    systems_with_failures = 0

    for system in systems:
        facts, _ = ai_system_service.derive_facts_with_provenance(db, system)
        ctx.ai_systems = [facts]

        by_status: dict[str, int] = {}
        control_statuses: dict[str, str] = {}
        applicable = 0
        for control in controls:
            if not is_control_active(control.effective_from, ctx.assessment_date):
                status = ControlStatus.UPCOMING.value
            else:
                status = evaluate(
                    control.evaluator_key, ctx, control.code, control.applies_to
                ).status
            control_statuses[control.code] = status
            if status != ControlStatus.NOT_APPLICABLE.value:
                applicable += 1
            by_status[status] = by_status.get(status, 0) + 1

        summary = {
            "total": len(control_statuses),
            "applicable": applicable,
            "by_status": by_status,
        }
        changes = _diff_against_last_snapshot(db, system, control_statuses)
        if persist:
            _record_snapshot(
                db, org, system, ctx.assessment_date, control_statuses, facts, summary
            )

        failing = by_status.get(ControlStatus.FAIL.value, 0) + by_status.get(
            ControlStatus.NO_EVIDENCE.value, 0
        )
        if failing:
            systems_with_failures += 1
        total_regressions += len(changes["regressed"])

        per_system.append(
            {
                "system_id": str(system.id),
                "system_name": system.name,
                "sector": system.sector,
                "summary": summary,
                "regressed": changes["regressed"],
                "improved": changes["improved"],
                "is_baseline": changes["is_baseline"],
            }
        )

    return {
        "organization": org.name,
        "assessment_date": ctx.assessment_date.isoformat(),
        "generated_at": utcnow().isoformat(),
        "system_count": len(systems),
        "systems_with_failures": systems_with_failures,
        "total_regressions": total_regressions,
        "systems": per_system,
    }


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
