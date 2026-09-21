"""Background tasks."""

from __future__ import annotations

import uuid

from app.core.database import SessionLocal
from app.workers.celery_app import celery_app


@celery_app.task(name="complygraph.run_scan")
def run_scan_task(scan_id: str) -> dict:
    """Execute a scan by id. Safe to run eagerly (in-process) or on a worker."""
    from app.services.scan_service import run_scan

    db = SessionLocal()
    try:
        scan = run_scan(db, uuid.UUID(scan_id))
        return {
            "scan_id": scan_id,
            "status": scan.status if scan else "UNKNOWN",
            "items_scanned": scan.items_scanned if scan else 0,
            "findings_created": scan.findings_created if scan else 0,
        }
    finally:
        db.close()


@celery_app.task(name="complygraph.analyze_ai_systems")
def analyze_ai_systems_task(organization_id: str) -> dict:
    """Analyze every AI system in an organization on a worker.

    Safe to run eagerly (in-process) or dispatched to a worker; used by the bulk
    analyze endpoint so a large inventory does not block the request thread.
    """
    from app.models.identity import Organization
    from app.services.assessment_service import analyze_all_systems

    db = SessionLocal()
    try:
        org = db.get(Organization, uuid.UUID(organization_id))
        if org is None:
            return {"organization_id": organization_id, "error": "not_found"}
        rollup = analyze_all_systems(db, org, persist=True)
        db.commit()
        return {
            "organization_id": organization_id,
            "system_count": rollup["system_count"],
            "systems_with_failures": rollup["systems_with_failures"],
            "total_regressions": rollup["total_regressions"],
        }
    finally:
        db.close()


@celery_app.task(name="complygraph.scheduled_reassessment")
def scheduled_reassessment_task() -> dict:
    """Re-run the control engine for every org on the beat cadence.

    Records fresh ControlAssessment history and raises regression notifications.
    Safe eager (in-process) or on a worker.
    """
    from sqlalchemy import select

    from app.core.config import settings
    from app.models.identity import Organization
    from app.services.reassessment_service import run_reassessment

    if not settings.scheduled_reassessment_enabled:
        return {"orgs": 0, "reason": "disabled"}

    processed = 0
    total_regressions = 0
    db = SessionLocal()
    try:
        for org in db.scalars(select(Organization)):
            summary = run_reassessment(db, org)
            db.commit()
            processed += 1
            total_regressions += summary["regressions"]
    finally:
        db.close()
    return {"orgs": processed, "regressions": total_regressions}


@celery_app.task(name="complygraph.generate_reminders")
def generate_reminders_task() -> dict:
    """Generate reminder notifications for every org on the beat cadence."""
    from sqlalchemy import select

    from app.core.config import settings
    from app.models.identity import Organization
    from app.services.reminder_service import generate_for_org

    if not settings.reminders_enabled:
        return {"orgs": 0, "reason": "disabled"}

    processed = 0
    total = 0
    db = SessionLocal()
    try:
        for org in db.scalars(select(Organization)):
            counts = generate_for_org(db, org)
            db.commit()
            processed += 1
            total += counts.get("total", 0)
    finally:
        db.close()
    return {"orgs": processed, "reminders": total}


@celery_app.task(name="complygraph.scheduled_rescans")
def scheduled_rescans_task() -> dict:
    """Enqueue rescans for connectors that have gone stale.

    Runs on the celery-beat cadence. A connector is eligible when it has never
    been scanned or its last scan is older than ``scheduled_rescan_min_age_hours``
    and it has no scan currently running. Continuous monitoring is what turns a
    one-off audit into ongoing DPDP compliance evidence.
    """
    from datetime import timedelta

    from sqlalchemy import or_, select

    from app.core.config import settings
    from app.core.database import utcnow
    from app.core.enums import ScanStatus
    from app.models.findings import Scan
    from app.models.inventory import Connector

    if not settings.scheduled_rescan_enabled:
        return {"enqueued": 0, "reason": "disabled"}

    cutoff = utcnow() - timedelta(hours=settings.scheduled_rescan_min_age_hours)
    enqueued: list[str] = []

    db = SessionLocal()
    try:
        connectors = db.scalars(
            select(Connector).where(
                Connector.status == "CONFIGURED",
                or_(Connector.last_scan_at.is_(None), Connector.last_scan_at < cutoff),
            )
        )
        for connector in connectors:
            running = db.scalar(
                select(Scan).where(
                    Scan.connector_id == connector.id,
                    Scan.status.in_([ScanStatus.RUNNING.value, ScanStatus.QUEUED.value]),
                )
            )
            if running is not None:
                continue
            scan = Scan(
                organization_id=connector.organization_id,
                connector_id=connector.id,
                status=ScanStatus.QUEUED.value,
                stage="Queued",
                progress=0,
                created_at=utcnow(),
            )
            db.add(scan)
            db.flush()
            scan_id = str(scan.id)
            db.commit()
            run_scan_task.delay(scan_id)
            enqueued.append(scan_id)
    finally:
        db.close()

    return {"enqueued": len(enqueued), "scan_ids": enqueued}
