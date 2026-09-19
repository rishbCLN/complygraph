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
