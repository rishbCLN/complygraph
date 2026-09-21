"""Reminder detection engine (feature #6).

Deterministically scans an organisation's compliance state as of its assessment
date and raises in-app notifications for things that need attention:

  * evidence expiring soon / already expired
  * findings, remediation tasks, and DSRs past (or nearing) their due date
  * risks whose review date has passed
  * controls that have not been (re-)assessed within the configured cadence

Every reminder uses a stable ``dedupe_key`` so repeated scheduled runs refresh a
single notification per underlying item rather than piling up duplicates. This
engine never changes compliance status - it only surfaces reminders.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import (
    FindingStatus,
    NotificationKind,
    NotificationSeverity,
    RiskStatus,
    TaskStatus,
)
from app.models.evidence import ControlEvidence, Evidence
from app.models.findings import Finding, RemediationTask
from app.models.identity import Organization
from app.models.operations import DataSubjectRequest
from app.models.regulatory import Control
from app.models.risk import Risk
from app.services import assessment_service, notification_service

# DSR statuses that are still "open" (a due-date reminder is meaningful).
_OPEN_DSR = {"REQUESTED", "IDENTITY_VERIFICATION", "IN_PROGRESS"}
_OPEN_FINDING = {
    FindingStatus.OPEN.value,
    FindingStatus.ACKNOWLEDGED.value,
    FindingStatus.IN_PROGRESS.value,
}
_OPEN_TASK = {TaskStatus.TODO.value, TaskStatus.IN_PROGRESS.value, TaskStatus.BLOCKED.value}
_CLOSED_RISK = {RiskStatus.CLOSED.value, RiskStatus.MITIGATED.value}


def generate_for_org(db: Session, org: Organization) -> dict:
    """Run all reminder checks for one org. Returns a per-kind count summary.

    Does not commit; the caller (task/endpoint) owns the transaction.
    """
    as_of = assessment_service.get_assessment_date(org)
    counts: dict[str, int] = {}

    def bump(kind: str) -> None:
        counts[kind] = counts.get(kind, 0) + 1

    _evidence_reminders(db, org, as_of, bump)
    _finding_reminders(db, org, as_of, bump)
    _task_reminders(db, org, as_of, bump)
    _dsr_reminders(db, org, as_of, bump)
    _risk_reminders(db, org, as_of, bump)
    _control_reassess_reminders(db, org, as_of, bump)

    counts["total"] = sum(counts.values())
    return counts


# --------------------------------------------------------------------------- #
def _evidence_reminders(db, org, as_of, bump) -> None:
    window = timedelta(days=settings.reminder_evidence_expiry_days)
    rows = db.scalars(
        select(Evidence).where(
            Evidence.organization_id == org.id,
            Evidence.expires_at.is_not(None),
        )
    )
    for ev in rows:
        expires = ev.expires_at
        if expires is None:
            continue
        expires = expires if expires.tzinfo else expires.replace(tzinfo=as_of.tzinfo)
        if expires < as_of:
            notification_service.upsert(
                db,
                org.id,
                kind=NotificationKind.EVIDENCE_EXPIRED.value,
                severity=NotificationSeverity.CRITICAL.value,
                title=f"Evidence expired: {ev.name}",
                body=(
                    f"'{ev.name}' expired on {expires.date().isoformat()}. Controls relying on it "
                    "may no longer be substantiated - collect a fresh artifact."
                ),
                entity_type="evidence",
                entity_id=str(ev.id),
                dedupe_key=f"evidence_expired:{ev.id}",
                due_at=expires,
                email_to=ev.owner,
            )
            bump("evidence_expired")
        elif expires <= as_of + window:
            notification_service.upsert(
                db,
                org.id,
                kind=NotificationKind.EVIDENCE_EXPIRING.value,
                severity=NotificationSeverity.WARNING.value,
                title=f"Evidence expiring soon: {ev.name}",
                body=(
                    f"'{ev.name}' expires on {expires.date().isoformat()}. Refresh it before then to "
                    "keep dependent controls substantiated."
                ),
                entity_type="evidence",
                entity_id=str(ev.id),
                dedupe_key=f"evidence_expiring:{ev.id}",
                due_at=expires,
                email_to=ev.owner,
            )
            bump("evidence_expiring")


def _finding_reminders(db, org, as_of, bump) -> None:
    rows = db.scalars(
        select(Finding).where(
            Finding.organization_id == org.id,
            Finding.status.in_(_OPEN_FINDING),
            Finding.due_at.is_not(None),
        )
    )
    for f in rows:
        due = f.due_at
        due = due if due.tzinfo else due.replace(tzinfo=as_of.tzinfo)
        if due < as_of:
            notification_service.upsert(
                db,
                org.id,
                kind=NotificationKind.FINDING_OVERDUE.value,
                severity=NotificationSeverity.WARNING.value,
                title=f"Overdue finding: {f.title}",
                body=f"This finding was due {due.date().isoformat()} and is still {f.status}.",
                entity_type="finding",
                entity_id=str(f.id),
                dedupe_key=f"finding_overdue:{f.id}",
                due_at=due,
                email_to=f.owner,
            )
            bump("finding_overdue")


def _task_reminders(db, org, as_of, bump) -> None:
    rows = db.scalars(
        select(RemediationTask).where(
            RemediationTask.organization_id == org.id,
            RemediationTask.status.in_(_OPEN_TASK),
            RemediationTask.due_at.is_not(None),
        )
    )
    for t in rows:
        due = t.due_at
        due = due if due.tzinfo else due.replace(tzinfo=as_of.tzinfo)
        if due < as_of:
            notification_service.upsert(
                db,
                org.id,
                kind=NotificationKind.TASK_OVERDUE.value,
                severity=NotificationSeverity.WARNING.value,
                title=f"Overdue task: {t.title}",
                body=f"This remediation task was due {due.date().isoformat()} and is still {t.status}.",
                entity_type="task",
                entity_id=str(t.id),
                dedupe_key=f"task_overdue:{t.id}",
                due_at=due,
            )
            bump("task_overdue")


def _dsr_reminders(db, org, as_of, bump) -> None:
    window = timedelta(days=settings.reminder_dsr_due_days)
    rows = db.scalars(
        select(DataSubjectRequest).where(
            DataSubjectRequest.organization_id == org.id,
            DataSubjectRequest.status.in_(_OPEN_DSR),
            DataSubjectRequest.due_at.is_not(None),
        )
    )
    for r in rows:
        due = r.due_at
        due = due if due.tzinfo else due.replace(tzinfo=as_of.tzinfo)
        if due < as_of:
            notification_service.upsert(
                db,
                org.id,
                kind=NotificationKind.DSR_OVERDUE.value,
                severity=NotificationSeverity.CRITICAL.value,
                title=f"Overdue data request ({r.request_type})",
                body=(
                    f"A {r.request_type} request passed its statutory deadline on "
                    f"{due.date().isoformat()} and is still {r.status}."
                ),
                entity_type="data_request",
                entity_id=str(r.id),
                dedupe_key=f"dsr_overdue:{r.id}",
                due_at=due,
            )
            bump("dsr_overdue")
        elif due <= as_of + window:
            notification_service.upsert(
                db,
                org.id,
                kind=NotificationKind.DSR_DUE.value,
                severity=NotificationSeverity.WARNING.value,
                title=f"Data request due soon ({r.request_type})",
                body=f"A {r.request_type} request is due {due.date().isoformat()}.",
                entity_type="data_request",
                entity_id=str(r.id),
                dedupe_key=f"dsr_due:{r.id}",
                due_at=due,
            )
            bump("dsr_due")


def _risk_reminders(db, org, as_of, bump) -> None:
    rows = db.scalars(
        select(Risk).where(
            Risk.organization_id == org.id,
            Risk.review_due_at.is_not(None),
        )
    )
    for risk in rows:
        if risk.status in _CLOSED_RISK:
            continue
        due = risk.review_due_at
        due = due if due.tzinfo else due.replace(tzinfo=as_of.tzinfo)
        if due < as_of:
            notification_service.upsert(
                db,
                org.id,
                kind=NotificationKind.RISK_REVIEW_DUE.value,
                severity=NotificationSeverity.WARNING.value,
                title=f"Risk review due: {risk.title}",
                body=(
                    f"This risk was due for review on {due.date().isoformat()}. Re-evaluate its "
                    "treatment and residual rating."
                ),
                entity_type="risk",
                entity_id=str(risk.id),
                dedupe_key=f"risk_review:{risk.id}",
                due_at=due,
                email_to=risk.owner,
            )
            bump("risk_review_due")


def _control_reassess_reminders(db, org, as_of, bump) -> None:
    cadence = timedelta(days=settings.control_reassess_interval_days)
    controls = db.scalars(select(Control))
    for control in controls:
        latest = assessment_service.latest_assessment(db, org.id, control.id)
        if latest is None:
            continue  # never assessed: covered by coverage metrics, not a reminder
        assessed = latest.assessment_date
        assessed = assessed if assessed.tzinfo else assessed.replace(tzinfo=as_of.tzinfo)
        if assessed + cadence < as_of:
            notification_service.upsert(
                db,
                org.id,
                kind=NotificationKind.CONTROL_REASSESS_DUE.value,
                severity=NotificationSeverity.INFO.value,
                title=f"Control due for re-assessment: {control.code}",
                body=(
                    f"{control.code} was last assessed as of {assessed.date().isoformat()}, beyond "
                    f"the {settings.control_reassess_interval_days}-day cadence."
                ),
                entity_type="control",
                entity_id=str(control.id),
                dedupe_key=f"control_reassess:{control.id}",
                due_at=assessed + cadence,
            )
            bump("control_reassess_due")
