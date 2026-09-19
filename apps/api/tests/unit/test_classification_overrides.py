"""Tests for the classifier feedback loop (analyst classification overrides).

An override must win over the automatic classifier and persist across scans,
turning a field the classifier would mark UNKNOWN into a confirmed classification.
"""

from __future__ import annotations

import base64
import io
import uuid
import zipfile

from sqlalchemy import select

from app.core.database import SessionLocal, utcnow
from app.core.enums import Classification, ConnectorType
from app.models.findings import Scan
from app.models.identity import Organization
from app.models.inventory import (
    AssetField,
    ClassificationOverride,
    Connector,
    DataAsset,
)
from app.scanners.classifier import FieldSample, classify_field
from app.security.encryption import encrypt_json
from app.services.scan_service import run_scan


def _zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_baseline_field_is_unknown_without_override():
    # Sanity: this field name carries no signal, so the classifier says UNKNOWN.
    result = classify_field(FieldSample(name="loyalty_ref", values=[]))
    assert result.classification == Classification.UNKNOWN.value


def test_override_applied_during_scan_persists_classification():
    zip_bytes = _zip(
        {
            "app/models.py": (
                "class Member(Base):\n"
                "    loyalty_ref = Column(String)\n"
                "    email = Column(String)\n"
            )
        }
    )

    db = SessionLocal()
    try:
        org = Organization(name="OverrideCorp", slug=f"ovr-{uuid.uuid4().hex[:8]}")
        db.add(org)
        db.flush()

        # Analyst confirms loyalty_ref is actually an identity personal-data field.
        db.add(
            ClassificationOverride(
                organization_id=org.id,
                field_name="loyalty_ref",
                asset_name=None,  # org-wide
                classification=Classification.PERSONAL_DATA.value,
                category="IDENTITY",
                note="Loyalty reference maps 1:1 to a person.",
            )
        )
        db.flush()

        cfg = {
            "filename": "override.zip",
            "content_b64": base64.b64encode(zip_bytes).decode("ascii"),
        }
        connector = Connector(
            organization_id=org.id,
            name="override.zip",
            type=ConnectorType.CODEBASE.value,
            status="CONFIGURED",
            configuration_encrypted=encrypt_json(cfg),
        )
        db.add(connector)
        db.flush()
        scan = Scan(
            organization_id=org.id,
            connector_id=connector.id,
            status="QUEUED",
            stage="Queued",
            progress=0,
            created_at=utcnow(),
        )
        db.add(scan)
        db.flush()
        scan_id = scan.id
        db.commit()

        result = run_scan(db, scan_id)
        assert result.status == "COMPLETED", result.error_message

        member = db.scalar(
            select(DataAsset).where(
                DataAsset.organization_id == org.id, DataAsset.display_name == "Member"
            )
        )
        assert member is not None
        loyalty = db.scalar(
            select(AssetField).where(
                AssetField.asset_id == member.id, AssetField.name == "loyalty_ref"
            )
        )
        assert loyalty is not None
        # The override, not the classifier, decided the outcome.
        assert loyalty.classification == Classification.PERSONAL_DATA.value
        assert loyalty.category == "IDENTITY"
        assert loyalty.confidence_band == "HIGH"
        assert loyalty.needs_review is False
        assert "override" in (loyalty.detection_method or "")
    finally:
        db.close()
