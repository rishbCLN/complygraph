"""Tests for the scheduled-rescan beat task."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.database import SessionLocal, utcnow
from app.core.enums import ConnectorType, ScanStatus
from app.models.findings import Scan
from app.models.identity import Organization
from app.models.inventory import Connector
from app.workers import tasks as worker_tasks


def _fresh_org_connector(db, *, last_scan_at=None, status="CONFIGURED") -> Connector:
    org = Organization(name="Sched", slug=f"sched-{uuid.uuid4().hex[:8]}")
    db.add(org)
    db.flush()
    connector = Connector(
        organization_id=org.id,
        name="demo",
        type=ConnectorType.DEMO.value,
        status=status,
        last_scan_at=last_scan_at,
    )
    db.add(connector)
    db.flush()
    db.commit()
    return connector


def test_scheduled_rescans_disabled(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "scheduled_rescan_enabled", False)
    result = worker_tasks.scheduled_rescans_task()
    assert result["enqueued"] == 0
    assert result["reason"] == "disabled"


def test_scheduled_rescans_enqueues_stale_connector(monkeypatch):
    # Isolate the enqueue logic from actual scan execution.
    dispatched: list[str] = []
    monkeypatch.setattr(
        worker_tasks.run_scan_task, "delay", lambda scan_id: dispatched.append(scan_id)
    )

    db = SessionLocal()
    try:
        connector = _fresh_org_connector(db, last_scan_at=None)
        worker_tasks.scheduled_rescans_task()
        scan = db.scalar(
            select(Scan).where(
                Scan.connector_id == connector.id, Scan.status == ScanStatus.QUEUED.value
            )
        )
        assert scan is not None
        assert str(scan.id) in dispatched
    finally:
        db.close()


def test_scheduled_rescans_skips_connector_with_running_scan(monkeypatch):
    dispatched: list[str] = []
    monkeypatch.setattr(
        worker_tasks.run_scan_task, "delay", lambda scan_id: dispatched.append(scan_id)
    )

    db = SessionLocal()
    try:
        connector = _fresh_org_connector(db, last_scan_at=None)
        running = Scan(
            organization_id=connector.organization_id,
            connector_id=connector.id,
            status=ScanStatus.RUNNING.value,
            stage="Inspecting",
            progress=40,
            created_at=utcnow(),
        )
        db.add(running)
        db.commit()

        worker_tasks.scheduled_rescans_task()
        # No new QUEUED scan should be created for a connector already scanning.
        queued = db.scalars(
            select(Scan).where(
                Scan.connector_id == connector.id, Scan.status == ScanStatus.QUEUED.value
            )
        ).all()
        assert queued == []
    finally:
        db.close()
