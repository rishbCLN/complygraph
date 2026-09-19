"""Tests for scan operational hardening: error classification, drift, concurrency."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal, utcnow
from app.core.enums import ConnectorType, ScanStatus
from app.core.errors import ValidationError
from app.models.findings import Finding, Scan
from app.models.identity import Organization
from app.models.inventory import Connector
from app.services import scan_service
from app.services.scan_service import (
    ScanConfigError,
    ScanConnectionError,
    _classify_scan_error,
    _persist_drift_findings,
    run_scan,
)


def test_classify_scan_error_categories():
    assert _classify_scan_error(ScanConfigError("bad dsn"))[0] == "CONFIG"
    assert _classify_scan_error(ValidationError("blocked host"))[0] == "CONFIG"
    assert _classify_scan_error(ScanConnectionError("refused"))[0] == "CONNECTION"
    assert _classify_scan_error(RuntimeError("connection timeout"))[0] == "CONNECTION"
    assert _classify_scan_error(RuntimeError("could not resolve host"))[0] == "CONNECTION"
    assert _classify_scan_error(KeyError("boom"))[0] == "INTERNAL"


def _make_org(db) -> Organization:
    org = Organization(name="OpsCorp", slug=f"ops-{uuid.uuid4().hex[:8]}")
    db.add(org)
    db.flush()
    return org


def test_persist_drift_findings_creates_finding():
    db = SessionLocal()
    try:
        org = _make_org(db)
        changes = {
            "classification_changed": ["users.ssn: NON_PERSONAL -> SENSITIVE_PERSONAL_DATA"],
            "sensitivity_changed": ["users.ssn: 2 -> 5"],
        }
        created = _persist_drift_findings(db, org, changes)
        db.commit()
        assert created == 1
        f = db.scalar(
            select(Finding).where(
                Finding.organization_id == org.id, Finding.source == "drift"
            )
        )
        assert f is not None
        assert "drift" in f.title.lower()
    finally:
        db.close()


def test_persist_drift_findings_noop_without_changes():
    db = SessionLocal()
    try:
        org = _make_org(db)
        created = _persist_drift_findings(db, org, {"classification_changed": [], "sensitivity_changed": []})
        db.commit()
        assert created == 0
    finally:
        db.close()


def test_concurrency_guard_blocks_second_scan():
    db = SessionLocal()
    try:
        org = _make_org(db)
        connector = Connector(
            organization_id=org.id,
            name="demo",
            type=ConnectorType.DEMO.value,
            status="CONFIGURED",
        )
        db.add(connector)
        db.flush()

        running = Scan(
            organization_id=org.id,
            connector_id=connector.id,
            status=ScanStatus.RUNNING.value,
            stage="Inspecting",
            progress=30,
            created_at=utcnow(),
        )
        second = Scan(
            organization_id=org.id,
            connector_id=connector.id,
            status=ScanStatus.QUEUED.value,
            stage="Queued",
            progress=0,
            created_at=utcnow(),
        )
        db.add_all([running, second])
        db.flush()
        second_id = second.id
        db.commit()

        result = run_scan(db, second_id)
        assert result.status == ScanStatus.FAILED.value
        assert result.error_type == "CONCURRENCY"
    finally:
        db.close()
