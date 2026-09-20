"""End-to-end proof of the applicability engine.

This is the test that was missing: it imports a real AI-system architecture
through the actual import service, then runs the full assessment
(``assess_all``) against a real database, and asserts the concrete status of
every AI-scoped control (RBI / CERT-In / MeitY).

It proves the whole chain works together:
    import architecture -> derive facts -> applicability match -> evaluator
rather than testing evaluators against hand-built fact dicts.

Two scenarios are covered:
  * a BFSI LLM in production that trips every AI control, and
  * a general, low-risk dev system that must make the sector/condition-scoped
    controls NOT_APPLICABLE (proving applicability gating, not blanket findings).
"""

from __future__ import annotations

import uuid

from app.core.database import SessionLocal, utcnow
from app.core.enums import ControlStatus
from app.models.identity import Organization
from app.models.inventory import Vendor
from app.services import ai_system_service, assessment_service


def _make_org(db, slug_prefix: str) -> Organization:
    org = Organization(
        name=f"{slug_prefix} Ltd.",
        slug=f"{slug_prefix}-{uuid.uuid4().hex[:8]}",
        industry="BFSI",
        country="India",
        plan="STARTER",
        assessment_date=utcnow(),
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(org)
    db.flush()
    return org


def _statuses_by_code(db, org: Organization) -> dict[str, str]:
    results = assessment_service.assess_all(db, org)
    return {control.code: evaluation.status for control, _assessment, evaluation in results}


def test_bfsi_production_system_trips_every_ai_control():
    """A BFSI LLM in production with external inference, external observability,
    a third-party vendor and a non-India region must produce the full expected
    matrix of AI-control statuses."""
    db = SessionLocal()
    try:
        org = _make_org(db, "proofbfsi")
        # A vendor the system's component can reference (drives has_vendors).
        vendor = Vendor(
            organization_id=org.id,
            name="Foreign Model Vendor",
            contract_status="MISSING",
            country="US",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(vendor)
        db.flush()

        body = {
            "system": {
                "name": "Credit Decisioning Copilot",
                "system_type": "LLM",
                "sector": "bfsi",
                "lifecycle_stage": "PRODUCTION",
                "review_status": "NOT_REVIEWED",
                "processes_personal_data": True,
                "makes_automated_decisions": True,
                "high_risk": True,
                "regions": ["India"],
            },
            "components": [
                {
                    "key": "llm",
                    "name": "Hosted LLM",
                    "type": "MODEL",
                    "external": True,
                    "region": "us",              # -> non_india_regions + external inference
                    "vendor": "Foreign Model Vendor",  # -> has_vendors
                },
                {
                    "key": "obs",
                    "name": "External APM",
                    "type": "SERVICE",
                    "external": True,            # external SERVICE -> uses_external_observability
                    "region": "us",
                },
                {"key": "store", "name": "Vector Store", "type": "DATA_STORE", "region": "India"},
            ],
            "flows": [
                {
                    "from": "store",
                    "to": "llm",
                    "relation": "SENDS_TO",
                    "contains_personal_data": True,
                    "cross_border": True,
                }
            ],
        }
        system = ai_system_service.import_architecture(db, org.id, uuid.uuid4(), body)
        db.flush()

        # Sanity-check the derived facts the applicability engine will consume.
        facts = ai_system_service.derive_facts(db, system)
        assert facts["sector"] == "bfsi"
        assert facts["non_india_regions"] == ["us"]
        assert facts["has_external_inference"] is True
        assert facts["uses_external_observability"] is True
        assert facts["has_vendors"] is True
        assert facts["is_production"] is True

        status = _statuses_by_code(db, org)

        # RBI (BFSI-scoped) — the system is in scope for all four.
        assert status["RBI-LOCALIZATION-001"] == ControlStatus.FAIL.value
        assert status["RBI-LOGGING-001"] == ControlStatus.NEEDS_REVIEW.value
        assert status["RBI-INFERENCE-001"] == ControlStatus.NEEDS_REVIEW.value
        assert status["RBI-VENDOR-001"] == ControlStatus.NEEDS_REVIEW.value

        # CERT-In (org-wide) — no evidence / no breach workflow in a fresh org.
        assert status["CERTIN-LOGS-001"] == ControlStatus.NO_EVIDENCE.value
        assert status["CERTIN-INCIDENT-001"] == ControlStatus.NO_EVIDENCE.value

        # MeitY — inventory has an unowned, unreviewed production system.
        assert status["MEITY-INVENTORY-001"] == ControlStatus.PARTIAL.value
        assert status["MEITY-BIAS-001"] == ControlStatus.NO_EVIDENCE.value
        assert status["MEITY-OVERSIGHT-001"] == ControlStatus.NO_EVIDENCE.value
        assert status["MEITY-LINEAGE-001"] == ControlStatus.NO_EVIDENCE.value
    finally:
        db.rollback()
        db.close()


def test_general_low_risk_system_gates_scoped_controls_not_applicable():
    """A general-sector, low-risk dev system must make the BFSI/condition-scoped
    controls NOT_APPLICABLE while org-wide controls still evaluate."""
    db = SessionLocal()
    try:
        org = _make_org(db, "proofgeneral")
        body = {
            "system": {
                "name": "Internal Docs Search",
                "system_type": "LLM",
                "sector": "general",
                "lifecycle_stage": "DEVELOPMENT",
                "processes_personal_data": False,
                "makes_automated_decisions": False,
                "high_risk": False,
                "regions": ["India"],
            },
            "components": [
                {"key": "store", "name": "Index", "type": "DATA_STORE", "region": "India"},
            ],
            "flows": [],
        }
        ai_system_service.import_architecture(db, org.id, uuid.uuid4(), body)
        db.flush()

        status = _statuses_by_code(db, org)

        # BFSI-sector-scoped controls: no matching system -> NOT_APPLICABLE.
        assert status["RBI-LOCALIZATION-001"] == ControlStatus.NOT_APPLICABLE.value
        assert status["RBI-LOGGING-001"] == ControlStatus.NOT_APPLICABLE.value
        assert status["RBI-INFERENCE-001"] == ControlStatus.NOT_APPLICABLE.value
        assert status["RBI-VENDOR-001"] == ControlStatus.NOT_APPLICABLE.value

        # Condition-scoped MeitY controls: conditions unmet -> NOT_APPLICABLE.
        assert status["MEITY-BIAS-001"] == ControlStatus.NOT_APPLICABLE.value
        assert status["MEITY-OVERSIGHT-001"] == ControlStatus.NOT_APPLICABLE.value

        # Org-wide controls still evaluate regardless of AI inventory scope.
        assert status["CERTIN-LOGS-001"] == ControlStatus.NO_EVIDENCE.value
        assert status["CERTIN-INCIDENT-001"] == ControlStatus.NO_EVIDENCE.value
        assert status["MEITY-LINEAGE-001"] == ControlStatus.NO_EVIDENCE.value
        # Inventory exists but nothing is in production yet -> PASS.
        assert status["MEITY-INVENTORY-001"] == ControlStatus.PASS.value
    finally:
        db.rollback()
        db.close()
