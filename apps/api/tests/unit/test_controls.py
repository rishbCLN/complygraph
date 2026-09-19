"""Unit tests for the deterministic control engine.

Every evaluator returns a status + human-readable reason. No LLM decides status.
These tests exercise the representative FAIL/PASS/NEEDS_REVIEW/NOT_APPLICABLE
branches for the evaluators that drive the demo findings.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.controls.engine import (
    ControlContext,
    eval_crossborder,
    eval_retention,
    eval_rights,
    eval_security,
    eval_vendor,
    evaluate,
)
from app.core.enums import ControlStatus, EvidenceStatus

ORG = uuid.uuid4()
DATE = datetime(2026, 9, 19, tzinfo=timezone.utc)


def _ctx(**kwargs) -> ControlContext:
    return ControlContext(organization_id=ORG, assessment_date=DATE, **kwargs)


# --- Vendor governance ----------------------------------------------------------


def test_vendor_fail_when_processor_contract_missing():
    vid = uuid.uuid4()
    ctx = _ctx(
        vendors=[{"id": vid, "contract_status": "MISSING"}],
        flows=[{"vendor_id": vid, "contains_personal_data": True}],
    )
    result = eval_vendor(ctx, "DPDP-VENDOR-001")
    assert result.status == ControlStatus.FAIL.value
    assert "contract" in result.reason.lower()


def test_vendor_pass_when_contract_recorded():
    vid = uuid.uuid4()
    ctx = _ctx(
        vendors=[{"id": vid, "contract_status": "SIGNED"}],
        flows=[{"vendor_id": vid, "contains_personal_data": True}],
    )
    assert eval_vendor(ctx, "DPDP-VENDOR-001").status == ControlStatus.PASS.value


def test_vendor_not_applicable_without_vendors():
    assert eval_vendor(_ctx(), "DPDP-VENDOR-001").status == ControlStatus.NOT_APPLICABLE.value


# --- Retention ------------------------------------------------------------------


def test_retention_fail_when_no_policy_defined():
    ctx = _ctx(
        personal_data_assets=[{"id": uuid.uuid4()}],
        processing_activities=[{"retention_period_days": None}],
        flags={},
    )
    result = eval_retention(ctx, "DPDP-RETENTION-001")
    assert result.status == ControlStatus.FAIL.value
    assert "retention" in result.reason.lower()


def test_retention_fail_when_last_deletion_failed():
    ctx = _ctx(
        personal_data_assets=[{"id": uuid.uuid4()}],
        processing_activities=[{"retention_period_days": 730}],
        flags={"deletion_last_status": "FAILED"},
    )
    result = eval_retention(ctx, "DPDP-RETENTION-002")
    assert result.status == ControlStatus.FAIL.value
    assert "deletion" in result.reason.lower()


def test_retention_not_applicable_without_personal_assets():
    ctx = _ctx(processing_activities=[{"retention_period_days": 730}], flags={})
    assert eval_retention(ctx, "DPDP-RETENTION-001").status == ControlStatus.NOT_APPLICABLE.value


# --- Rights ---------------------------------------------------------------------


def test_rights_pass_when_dsr_configured():
    assert eval_rights(_ctx(dsr_configured=True), "DPDP-RIGHTS-001").status == ControlStatus.PASS.value


def test_rights_fail_when_no_workflow():
    assert eval_rights(_ctx(dsr_configured=False), "DPDP-RIGHTS-001").status == ControlStatus.FAIL.value


# --- Security -------------------------------------------------------------------


def test_security_pass_with_fresh_evidence():
    ctx = _ctx(
        personal_data_assets=[{"id": uuid.uuid4()}],
        evidence_by_control={"DPDP-SECURITY-001": [{"id": uuid.uuid4(), "status": EvidenceStatus.FRESH.value}]},
    )
    assert eval_security(ctx, "DPDP-SECURITY-001").status == ControlStatus.PASS.value


def test_security_needs_review_with_expired_evidence():
    ctx = _ctx(
        personal_data_assets=[{"id": uuid.uuid4()}],
        evidence_by_control={"DPDP-SECURITY-003": [{"id": uuid.uuid4(), "status": EvidenceStatus.EXPIRED.value}]},
    )
    assert eval_security(ctx, "DPDP-SECURITY-003").status == ControlStatus.NEEDS_REVIEW.value


def test_security_no_evidence_when_personal_assets_unprotected():
    ctx = _ctx(personal_data_assets=[{"id": uuid.uuid4()}])
    assert eval_security(ctx, "DPDP-SECURITY-005").status == ControlStatus.NO_EVIDENCE.value


# --- Cross-border ---------------------------------------------------------------


def test_crossborder_needs_review_without_governance_evidence():
    ctx = _ctx(flows=[{"cross_border": True, "contains_personal_data": True}])
    assert eval_crossborder(ctx, "DPDP-CROSSBORDER-001").status == ControlStatus.NEEDS_REVIEW.value


def test_crossborder_not_applicable_without_cross_border_flows():
    ctx = _ctx(flows=[{"cross_border": False, "contains_personal_data": True}])
    assert eval_crossborder(ctx, "DPDP-CROSSBORDER-001").status == ControlStatus.NOT_APPLICABLE.value


# --- Dispatch -------------------------------------------------------------------


def test_evaluate_unknown_key_falls_back_to_generic():
    # generic evaluator returns NO_EVIDENCE when nothing is linked.
    result = evaluate("does-not-exist", _ctx(), "SOME-CODE")
    assert result.status == ControlStatus.NO_EVIDENCE.value


def test_evaluate_dispatches_to_named_evaluator():
    assert evaluate("rights", _ctx(dsr_configured=True), "DPDP-RIGHTS-001").status == ControlStatus.PASS.value
