"""Scheduled / on-demand org-wide re-assessment (feature #6).

Re-running the control engine produces a fresh ``ControlAssessment`` row per
control (the model is append-only history). This service wraps ``assess_all``
to also:

  * capture each control's *prior* latest status before the run;
  * detect regressions (a control that got worse, e.g. PASS -> FAIL) by comparing
    against the deterministic ``_STATUS_ORDER``;
  * raise a summary notification and one notification per regression.

Deterministic and idempotent in effect: the engine decides status purely from
context + evidence + effective dates, never from AI.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import NotificationKind, NotificationSeverity
from app.models.identity import Organization
from app.services import assessment_service, notification_service
from app.services.assessment_service import _STATUS_ORDER


def _rank(status: str) -> int:
    # Lower rank == worse posture. Unknown statuses sort mid.
    return _STATUS_ORDER.get(status, 2)


def run_reassessment(db: Session, org: Organization) -> dict:
    """Re-assess every control for one org, recording history and regressions.

    Returns a summary dict. Does not commit; the caller owns the transaction.
    """
    # Snapshot prior latest status per control BEFORE inserting new rows.
    prior: dict[str, str] = {}
    from app.models.regulatory import Control
    from sqlalchemy import select

    for control in db.scalars(select(Control)):
        latest = assessment_service.latest_assessment(db, org.id, control.id)
        if latest is not None:
            prior[str(control.id)] = latest.status

    results = assessment_service.assess_all(db, org)

    regressions: list[dict] = []
    improvements = 0
    status_counts: dict[str, int] = {}
    for control, assessment, _evaluation in results:
        new_status = assessment.status
        status_counts[new_status] = status_counts.get(new_status, 0) + 1
        old_status = prior.get(str(control.id))
        if old_status is None or old_status == new_status:
            continue
        if _rank(new_status) < _rank(old_status):
            regressions.append(
                {
                    "control_id": str(control.id),
                    "control_code": control.code,
                    "from": old_status,
                    "to": new_status,
                }
            )
        elif _rank(new_status) > _rank(old_status):
            improvements += 1

    from app.services import webhook_service

    # One notification per regression (deduped by control), plus a run summary.
    for reg in regressions:
        notification_service.upsert(
            db,
            org.id,
            kind=NotificationKind.ASSESSMENT_REGRESSED.value,
            severity=NotificationSeverity.CRITICAL.value,
            title=f"Control regressed: {reg['control_code']}",
            body=(
                f"{reg['control_code']} moved from {reg['from']} to {reg['to']} on re-assessment. "
                "Review recent changes to evidence, data flows, or scope."
            ),
            entity_type="control",
            entity_id=reg["control_id"],
            dedupe_key=f"assessment_regressed:{reg['control_id']}:{reg['to']}",
        )
        webhook_service.dispatch_event(
            db,
            org.id,
            "assessment.regressed",
            {
                "control_id": reg["control_id"],
                "control_code": reg["control_code"],
                "from": reg["from"],
                "to": reg["to"],
            },
        )

    total = len(results)
    summary = {
        "controls_assessed": total,
        "regressions": len(regressions),
        "improvements": improvements,
        "status_counts": status_counts,
        "regressed_controls": regressions,
    }

    webhook_service.dispatch_event(
        db,
        org.id,
        "control.reassessed",
        {
            "controls_assessed": total,
            "regressions": len(regressions),
            "improvements": improvements,
            "status_counts": status_counts,
        },
    )

    notification_service.upsert(
        db,
        org.id,
        kind=NotificationKind.REASSESSMENT_COMPLETE.value,
        severity=(
            NotificationSeverity.WARNING.value if regressions else NotificationSeverity.INFO.value
        ),
        title="Re-assessment complete",
        body=(
            f"Re-assessed {total} controls: {len(regressions)} regressed, {improvements} improved."
        ),
        entity_type="reassessment",
        entity_id=None,
        # No dedupe: each completed run is its own record.
    )
    return summary
