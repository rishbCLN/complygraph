"""Scan orchestration service.

Runs the full discovery loop for a connector:
  connect -> discover -> classify -> persist assets/fields (idempotent) ->
  detect changes -> evaluate applicable controls -> generate findings -> commit.

Progress is recorded on the Scan row so the frontend can poll real stages.
Raw sampled values are never persisted; only masked examples and redacted
detection evidence are stored.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.controls.risk import RiskInputs, volume_band
from app.core.audit import record_audit
from app.core.config import settings
from app.core.database import utcnow
from app.core.enums import (
    Classification,
    ConnectorType,
    ScanStatus,
)
from app.models.findings import Scan, ScanResult
from app.models.identity import Organization
from app.models.inventory import AssetField, Connector, DataAsset
from app.scanners.base import BaseConnector, DiscoveredAsset
from app.scanners.classifier import FieldSample, classify_field
from app.scanners.sensitivity import asset_sensitivity, field_sensitivity
from app.security.encryption import decrypt_json
from app.services import findings_service

STAGES = [
    (5, "Connecting"),
    (15, "Inspecting schemas"),
    (35, "Inspecting fields"),
    (55, "Classifying data"),
    (70, "Building inventory"),
    (80, "Updating flows"),
    (90, "Evaluating controls"),
    (97, "Generating findings"),
    (100, "Complete"),
]

_PERSONAL = {Classification.PERSONAL_DATA.value, Classification.SENSITIVE_PERSONAL_DATA.value}


def _fingerprint(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]


def _set_stage(db: Session, scan: Scan, progress: int, stage: str) -> None:
    scan.progress = progress
    scan.stage = stage
    db.commit()


def build_connector(connector: Connector) -> BaseConnector:
    from app.scanners.file_connectors import CSVConnector, JSONConnector
    from app.scanners.postgres_connector import PostgresConnector

    from app.scanners.demo_connector import DemoConnector

    config = decrypt_json(connector.configuration_encrypted) if connector.configuration_encrypted else {}

    if connector.type == ConnectorType.DEMO.value:
        dsn = config.get("dsn") or settings.demo_database_url
        # Use a real PostgreSQL source if configured, otherwise synthetic in-memory data.
        return PostgresConnector(dsn) if dsn else DemoConnector()
    if connector.type == ConnectorType.POSTGRES.value:
        dsn = config.get("dsn") or settings.demo_database_url
        if not dsn:
            return DemoConnector()
        return PostgresConnector(dsn)
    if connector.type == ConnectorType.CSV.value:
        import base64

        content = base64.b64decode(config.get("content_b64", ""))
        return CSVConnector(content, config.get("filename", "upload.csv"))
    if connector.type == ConnectorType.JSON.value:
        import base64

        content = base64.b64decode(config.get("content_b64", ""))
        return JSONConnector(content, config.get("filename", "upload.json"))
    raise ValueError(f"Unsupported connector type: {connector.type}")


def _persist_asset(
    db: Session,
    org_id: uuid.UUID,
    connector: Connector,
    discovered: DiscoveredAsset,
    scan: Scan,
    changes: dict,
) -> DataAsset:
    asset_fp = _fingerprint(str(connector.id), discovered.name)
    asset = db.scalar(
        select(DataAsset).where(
            DataAsset.organization_id == org_id, DataAsset.fingerprint == asset_fp
        )
    )
    is_new = asset is None
    if is_new:
        asset = DataAsset(
            organization_id=org_id,
            connector_id=connector.id,
            name=discovered.name,
            display_name=discovered.display_name,
            asset_type=discovered.asset_type,
            system_name=discovered.system_name,
            environment=discovered.environment,
            fingerprint=asset_fp,
        )
        db.add(asset)
        db.flush()
        changes["new_assets"].append(discovered.display_name)
    asset.row_count = discovered.row_count
    asset.last_seen_at = utcnow()

    existing_fields = {f.fingerprint: f for f in asset.fields}
    field_levels: list[int] = []
    asset_has_personal = False

    for dfield in discovered.fields:
        sample = FieldSample(
            name=dfield.name,
            data_type=dfield.data_type,
            field_path=dfield.field_path,
            values=dfield.samples,
        )
        result = classify_field(sample)
        field_fp = _fingerprint(str(asset.id), dfield.field_path or dfield.name)
        field_obj = existing_fields.get(field_fp)
        prev_classification = field_obj.classification if field_obj else None
        prev_sensitivity = None

        if field_obj is None:
            field_obj = AssetField(asset_id=asset.id, name=dfield.name, fingerprint=field_fp)
            db.add(field_obj)
            if not is_new:
                changes["new_fields"].append(f"{discovered.display_name}.{dfield.name}")
        else:
            prev_sensitivity = field_sensitivity(field_obj.classification, field_obj.category)

        field_obj.data_type = dfield.data_type
        field_obj.classification = result.classification
        field_obj.category = result.category
        field_obj.confidence = result.confidence
        field_obj.confidence_band = result.confidence_band
        field_obj.detection_method = result.detection_method
        field_obj.needs_review = result.needs_review
        field_obj.sample_count = result.sample_count
        field_obj.sensitive_count = result.sensitive_count
        field_obj.masked_examples = ", ".join(result.masked_examples) or None

        level = field_sensitivity(result.classification, result.category)
        field_levels.append(level)
        if result.classification in _PERSONAL:
            asset_has_personal = True

        if prev_classification and prev_classification != result.classification:
            changes["classification_changed"].append(
                f"{discovered.display_name}.{dfield.name}: {prev_classification} -> {result.classification}"
            )
        new_sensitivity = level
        if prev_sensitivity is not None and prev_sensitivity != new_sensitivity:
            changes["sensitivity_changed"].append(
                f"{discovered.display_name}.{dfield.name}: {prev_sensitivity} -> {new_sensitivity}"
            )

        # Store only redacted detection evidence (never raw values).
        db.add(
            ScanResult(
                scan_id=scan.id,
                asset_id=asset.id,
                field_name=dfield.name,
                result_type="classification",
                classification=result.classification,
                confidence=result.confidence,
                evidence=(
                    f"method={result.detection_method}; band={result.confidence_band}; "
                    f"examples={'; '.join(result.masked_examples)}"
                ),
                created_at=utcnow(),
            )
        )

    asset.sensitivity_level = asset_sensitivity(field_levels)
    asset.classification = (
        Classification.PERSONAL_DATA.value if asset_has_personal else Classification.NON_PERSONAL.value
    )
    return asset


def _generate_findings(db: Session, org: Organization, scan: Scan) -> int:
    """Regenerate control-driven findings after a scan and return the count created/updated."""
    from app.services.assessment_service import assess_all

    count = 0
    results = assess_all(db, org)
    for control, assessment, evaluation in results:
        if assessment.status not in {"FAIL", "NO_EVIDENCE", "NEEDS_REVIEW"}:
            continue
        affected_asset_id = None
        sensitivity = 3
        volume = 1
        if evaluation.affected_asset_ids:
            affected_asset_id = uuid.UUID(evaluation.affected_asset_ids[0])
            asset = db.get(DataAsset, affected_asset_id)
            if asset:
                sensitivity = asset.sensitivity_level
                volume = volume_band(asset.row_count)
        control_gap = 5 if assessment.status in {"FAIL", "NO_EVIDENCE"} else 3
        exposure = 3
        findings_service.upsert_finding(
            db,
            organization_id=org.id,
            finding_type=f"control:{control.code}",
            title=f"{control.title} — {assessment.status.replace('_', ' ').title()}",
            description=evaluation.reason,
            risk_inputs=RiskInputs(sensitivity, exposure, control_gap, volume),
            control_id=control.id,
            asset_id=affected_asset_id,
            data_categories=None,
            recommended_actions=evaluation.recommended_actions,
            evidence_refs=evaluation.evidence_ids,
            source="scan",
        )
        count += 1
    return count


def run_scan(db: Session, scan_id: uuid.UUID) -> Scan:
    scan = db.get(Scan, scan_id)
    if scan is None:
        raise ValueError("Scan not found")
    org = db.get(Organization, scan.organization_id)
    connector = db.get(Connector, scan.connector_id) if scan.connector_id else None

    changes = {
        "new_assets": [],
        "deleted_assets": [],
        "new_fields": [],
        "classification_changed": [],
        "sensitivity_changed": [],
    }

    scan.status = ScanStatus.RUNNING.value
    scan.started_at = utcnow()
    _set_stage(db, scan, *STAGES[0])

    try:
        if connector is None:
            raise ValueError("Scan has no connector")
        conn_impl = build_connector(connector)

        _set_stage(db, scan, *STAGES[1])
        ok, message = conn_impl.test_connection()
        if not ok:
            raise RuntimeError(message)

        _set_stage(db, scan, *STAGES[2])
        discovered_assets = conn_impl.discover()

        _set_stage(db, scan, *STAGES[3])
        items = 0
        for discovered in discovered_assets:
            _persist_asset(db, org.id, connector, discovered, scan, changes)
            items += 1 + len(discovered.fields)

        _set_stage(db, scan, *STAGES[4])
        db.flush()

        _set_stage(db, scan, *STAGES[5])
        # Flow discovery is handled by the flow service / seed; scan updates inventory.

        _set_stage(db, scan, *STAGES[6])
        _set_stage(db, scan, *STAGES[7])
        findings_created = _generate_findings(db, org, scan)

        connector.last_scan_at = utcnow()
        scan.items_scanned = items
        scan.findings_created = findings_created
        scan.changes = changes
        scan.status = ScanStatus.COMPLETED.value
        scan.completed_at = utcnow()
        _set_stage(db, scan, *STAGES[8])

        record_audit(
            db,
            action="connector.scanned",
            organization_id=org.id,
            entity_type="scan",
            entity_id=scan.id,
            metadata={
                "connector_id": str(connector.id),
                "items_scanned": items,
                "findings_created": findings_created,
                "new_assets": len(changes["new_assets"]),
            },
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        scan = db.get(Scan, scan_id)
        if scan:
            scan.status = ScanStatus.FAILED.value
            scan.error_message = f"{type(exc).__name__}: {exc}"
            scan.completed_at = utcnow()
            db.commit()
    return db.get(Scan, scan_id)
