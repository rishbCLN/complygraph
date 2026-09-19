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
    AssetType,
    Classification,
    ConfidenceBand,
    ConnectorType,
    FlowType,
    ScanStatus,
)
from app.models.findings import Scan, ScanResult
from app.models.identity import Organization
from app.models.inventory import (
    AssetField,
    ClassificationOverride,
    Connector,
    DataAsset,
    DataFlow,
    Vendor,
)
from app.scanners.base import (
    BaseConnector,
    DiscoveredAsset,
    DiscoveredCodeRisk,
    DiscoveredIntegration,
)
from app.core.errors import ValidationError
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


class ScanConfigError(Exception):
    """Connector is misconfigured (bad DSN, missing/undecryptable config, unsupported type)."""


class ScanConnectionError(Exception):
    """The source could not be reached or authentication failed."""


def _classify_scan_error(exc: Exception) -> tuple[str, str]:
    """Map an exception to a (error_type, user_message) for actionable reporting."""
    if isinstance(exc, (ScanConfigError, ValidationError)):
        return "CONFIG", str(exc)
    if isinstance(exc, ScanConnectionError):
        return "CONNECTION", str(exc)
    message = str(exc).lower()
    if any(w in message for w in ("connect", "timeout", "refused", "unreachable", "resolve", "authentication", "password")):
        return "CONNECTION", str(exc)
    if any(w in message for w in ("config", "dsn", "decrypt", "unsupported", "missing")):
        return "CONFIG", str(exc)
    return "INTERNAL", str(exc)


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
    if connector.type == ConnectorType.CODEBASE.value:
        import base64

        from app.scanners.codebase_connector import CodebaseConnector

        content = base64.b64decode(config.get("content_b64", ""))
        return CodebaseConnector(content, config.get("filename", "repository.zip"))
    raise ScanConfigError(f"Unsupported connector type: {connector.type}")


def _load_overrides(db: Session, org_id: uuid.UUID) -> dict[tuple[str | None, str], ClassificationOverride]:
    """Index analyst classification overrides by (asset_name|None, field_name_lower)."""
    overrides: dict[tuple[str | None, str], ClassificationOverride] = {}
    for ov in db.scalars(
        select(ClassificationOverride).where(ClassificationOverride.organization_id == org_id)
    ):
        overrides[(ov.asset_name, ov.field_name.strip().lower())] = ov
    return overrides


def _match_override(
    overrides: dict[tuple[str | None, str], ClassificationOverride],
    asset_name: str,
    field_name: str,
) -> ClassificationOverride | None:
    key = field_name.strip().lower()
    # Asset-scoped override wins over an org-wide one.
    return overrides.get((asset_name, key)) or overrides.get((None, key))


def _persist_asset(
    db: Session,
    org_id: uuid.UUID,
    connector: Connector,
    discovered: DiscoveredAsset,
    scan: Scan,
    changes: dict,
    overrides: dict[tuple[str | None, str], ClassificationOverride] | None = None,
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
        # Analyst feedback loop: a confirmed/corrected classification wins.
        override = (
            _match_override(overrides, discovered.name, dfield.name) if overrides else None
        )
        if override is not None:
            result.classification = override.classification
            result.category = override.category
            result.confidence = 1.0
            result.confidence_band = ConfidenceBand.HIGH.value
            result.needs_review = False
            result.detection_method = (
                f"{result.detection_method}+override"
                if result.detection_method and result.detection_method != "none"
                else "override"
            )
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


def _find_or_create_flow(
    db: Session,
    org_id: uuid.UUID,
    *,
    source_asset_id: uuid.UUID | None,
    destination_asset_id: uuid.UUID | None,
    vendor_id: uuid.UUID | None,
    flow_type: str,
    contains_personal_data: bool,
    contains_sensitive_category: bool,
    cross_border: bool,
    categories: str | None,
) -> None:
    """Idempotently upsert a discovered flow keyed by (source, destination, vendor)."""
    existing = db.scalar(
        select(DataFlow).where(
            DataFlow.organization_id == org_id,
            DataFlow.source_asset_id == source_asset_id,
            DataFlow.destination_asset_id == destination_asset_id,
            DataFlow.vendor_id == vendor_id,
        )
    )
    if existing is None:
        db.add(
            DataFlow(
                organization_id=org_id,
                source_asset_id=source_asset_id,
                destination_asset_id=destination_asset_id,
                vendor_id=vendor_id,
                flow_type=flow_type,
                contains_personal_data=contains_personal_data,
                contains_sensitive_category=contains_sensitive_category,
                cross_border=cross_border,
                discovered=True,
                confidence=0.6,  # static inference from code, not runtime-observed
                status="ACTIVE",
                categories=categories,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
    else:
        existing.flow_type = flow_type
        existing.contains_personal_data = contains_personal_data
        existing.contains_sensitive_category = contains_sensitive_category
        existing.cross_border = cross_border
        existing.categories = categories
        existing.updated_at = utcnow()


def _persist_code_graph(
    db: Session,
    org: Organization,
    connector: Connector,
    integrations: list[DiscoveredIntegration],
) -> None:
    """Wire code-derived assets into the data-flow graph.

    Builds: [personal-data datasets] -> [application] -> [third-party vendors],
    creating Vendor rows for detected SDKs and flows that feed the existing
    cross-border and vendor-governance controls.
    """
    app_asset = db.scalar(
        select(DataAsset).where(
            DataAsset.organization_id == org.id,
            DataAsset.connector_id == connector.id,
            DataAsset.asset_type == AssetType.APPLICATION.value,
        )
    )
    if app_asset is None:
        return

    datasets = list(
        db.scalars(
            select(DataAsset).where(
                DataAsset.organization_id == org.id,
                DataAsset.connector_id == connector.id,
                DataAsset.asset_type != AssetType.APPLICATION.value,
            )
        )
    )
    personal = [d for d in datasets if d.classification in _PERSONAL]
    any_personal = len(personal) > 0
    any_sensitive = any(d.sensitivity_level >= 5 for d in personal)

    # Aggregate distinct personal-data categories for edge labeling.
    categories: list[str] = []
    for d in personal:
        for f in d.fields:
            if f.classification in _PERSONAL and f.category and f.category not in categories:
                categories.append(f.category)
    categories_str = ", ".join(sorted(categories)[:6]) or None

    # Internal flows: each personal dataset -> application.
    for d in personal:
        _find_or_create_flow(
            db,
            org.id,
            source_asset_id=d.id,
            destination_asset_id=app_asset.id,
            vendor_id=None,
            flow_type=FlowType.INTERNAL.value,
            contains_personal_data=True,
            contains_sensitive_category=d.sensitivity_level >= 5,
            cross_border=False,
            categories=None,
        )

    # Outbound flows: application -> each detected third-party vendor.
    for integ in integrations:
        cross_border = bool(integ.country) and integ.country != "India"
        vendor = db.scalar(
            select(Vendor).where(
                Vendor.organization_id == org.id, Vendor.name == integ.vendor_name
            )
        )
        if vendor is None:
            vendor = Vendor(
                organization_id=org.id,
                name=integ.vendor_name,
                description=f"Detected in application source ({integ.evidence}).",
                service_type=integ.service_type,
                country=integ.country,
                data_processing=(
                    "Personal data may be shared based on code integration."
                    if any_personal
                    else "Integration detected in source code."
                ),
                contract_status="UNKNOWN",  # drives vendor-governance review
                risk_level="HIGH" if cross_border else "MEDIUM",
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(vendor)
            db.flush()

        _find_or_create_flow(
            db,
            org.id,
            source_asset_id=app_asset.id,
            destination_asset_id=None,
            vendor_id=vendor.id,
            flow_type=integ.flow_type,
            contains_personal_data=any_personal,
            contains_sensitive_category=any_sensitive,
            cross_border=cross_border,
            categories=categories_str,
        )


_CODE_RISK_TITLES = {
    "pii_in_logs": "Personal data written to application logs",
    "pii_to_third_party": "Personal data may be shared with a third-party SDK",
}


def _persist_code_risks(
    db: Session,
    org: Organization,
    connector: Connector,
    code_risks: list[DiscoveredCodeRisk],
) -> int:
    """Turn static code-analysis risks into findings attached to the application asset."""
    if not code_risks:
        return 0

    app_asset = db.scalar(
        select(DataAsset).where(
            DataAsset.organization_id == org.id,
            DataAsset.connector_id == connector.id,
            DataAsset.asset_type == AssetType.APPLICATION.value,
        )
    )
    app_asset_id = app_asset.id if app_asset else None

    grouped: dict[str, list[DiscoveredCodeRisk]] = {}
    for risk in code_risks:
        grouped.setdefault(risk.kind, []).append(risk)

    count = 0
    for kind, risks in grouped.items():
        locations = "; ".join(f"{r.file_path}:{r.line_no}" for r in risks[:8])
        more = f" (+{len(risks) - 8} more)" if len(risks) > 8 else ""
        title = _CODE_RISK_TITLES.get(kind, "Code privacy risk")
        # pii_to_third_party is the higher-exposure signal.
        control_gap = 4 if kind == "pii_to_third_party" else 3
        exposure = 4 if kind == "pii_to_third_party" else 2
        findings_service.upsert_finding(
            db,
            organization_id=org.id,
            finding_type=f"code:{kind}",
            title=title,
            description=(
                f"Static source analysis flagged {len(risks)} occurrence(s). "
                f"Locations: {locations}{more}. "
                "This is a heuristic signal for human review, not a confirmed transfer."
            ),
            risk_inputs=RiskInputs(sensitivity=4, exposure=exposure, control_gap=control_gap, volume=2),
            asset_id=app_asset_id,
            data_categories=None,
            recommended_actions=[
                "Review the flagged lines and confirm whether personal data is involved",
                "Redact or remove personal data from logs"
                if kind == "pii_in_logs"
                else "Confirm a processor agreement and lawful basis for the third-party transfer",
            ],
            source="code_scan",
        )
        count += 1
    return count


def _persist_drift_findings(db: Session, org: Organization, changes: dict) -> int:
    """Raise a finding when a rescan detects material drift from the prior state.

    Sensitivity escalations and classification changes are the signals a DPO
    cares about between scans (e.g. a field that became sensitive personal data),
    so they are surfaced as reviewable findings rather than buried in scan metadata.
    """
    escalations = changes.get("sensitivity_changed", [])
    reclassifications = changes.get("classification_changed", [])
    if not escalations and not reclassifications:
        return 0

    details: list[str] = []
    if reclassifications:
        details.append(f"{len(reclassifications)} field(s) changed classification")
    if escalations:
        details.append(f"{len(escalations)} field(s) changed sensitivity")
    examples = "; ".join((reclassifications + escalations)[:8])

    # Drift is a moderate, review-oriented signal; keep control_gap modest.
    findings_service.upsert_finding(
        db,
        organization_id=org.id,
        finding_type="scan:drift",
        title="Data classification drift detected since last scan",
        description=(
            f"{', '.join(details)}. Examples: {examples}. "
            "Review whether new consent, contracts, or controls are required."
        ),
        risk_inputs=RiskInputs(sensitivity=4, exposure=2, control_gap=3, volume=2),
        data_categories=None,
        recommended_actions=[
            "Review the changed fields and confirm the new classification is correct",
            "Check whether the change requires updated notices, consent, or safeguards",
        ],
        source="drift",
    )
    return 1


def run_scan(db: Session, scan_id: uuid.UUID) -> Scan:
    scan = db.get(Scan, scan_id)
    if scan is None:
        raise ValueError("Scan not found")
    org = db.get(Organization, scan.organization_id)
    connector = db.get(Connector, scan.connector_id) if scan.connector_id else None

    # Concurrency guard: refuse to run a second scan on a connector that is already
    # scanning, to avoid duplicate assets/findings from interleaved writes.
    if connector is not None:
        conflict = db.scalar(
            select(Scan).where(
                Scan.connector_id == connector.id,
                Scan.id != scan.id,
                Scan.status == ScanStatus.RUNNING.value,
            )
        )
        if conflict is not None:
            scan.status = ScanStatus.FAILED.value
            scan.error_type = "CONCURRENCY"
            scan.error_message = (
                "Another scan is already running for this connector. "
                "Wait for it to finish before starting a new one."
            )
            scan.completed_at = utcnow()
            db.commit()
            return db.get(Scan, scan_id)

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
            raise ScanConfigError("Scan has no connector")
        conn_impl = build_connector(connector)

        _set_stage(db, scan, *STAGES[1])
        ok, message = conn_impl.test_connection()
        if not ok:
            raise ScanConnectionError(message)

        _set_stage(db, scan, *STAGES[2])
        discovered_assets = conn_impl.discover()

        _set_stage(db, scan, *STAGES[3])
        overrides = _load_overrides(db, org.id)
        items = 0
        for discovered in discovered_assets:
            _persist_asset(db, org.id, connector, discovered, scan, changes, overrides)
            items += 1 + len(discovered.fields)

        _set_stage(db, scan, *STAGES[4])
        db.flush()

        _set_stage(db, scan, *STAGES[5])
        # Code connectors derive flows/vendors from source; DB/file scans update inventory.
        if connector.type == ConnectorType.CODEBASE.value:
            _persist_code_graph(db, org, connector, conn_impl.discover_integrations())
            _persist_code_risks(db, org, connector, conn_impl.discover_code_risks())
            db.flush()

        _set_stage(db, scan, *STAGES[6])
        _set_stage(db, scan, *STAGES[7])
        findings_created = _generate_findings(db, org, scan)
        findings_created += _persist_drift_findings(db, org, changes)

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
        error_type, user_message = _classify_scan_error(exc)
        db.rollback()
        scan = db.get(Scan, scan_id)
        if scan:
            scan.status = ScanStatus.FAILED.value
            scan.error_type = error_type
            scan.error_message = user_message
            scan.stage = "Failed"
            scan.completed_at = utcnow()
            db.commit()
    return db.get(Scan, scan_id)
