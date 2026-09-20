"""Unit tests for the control applicability engine and AI-system evaluators.

The applicability engine decides *whether* an AI-scoped control applies to an
organization's AI systems (by sector / ai_type / declared conditions) before an
evaluator decides *how well* it is met. AI never decides status; these tests
pin the deterministic scoping and status branches.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.controls.applicability import (
    applicable_systems,
    is_ai_scoped,
    system_matches,
)
from app.controls.engine import ControlContext, evaluate
from app.core.enums import ControlStatus, EvidenceStatus

ORG = uuid.uuid4()
DATE = datetime(2026, 9, 19, tzinfo=timezone.utc)


def _facts(**kwargs) -> dict:
    base = {
        "system_id": str(uuid.uuid4()),
        "name": "Test System",
        "sector": "general",
        "system_type": "LLM",
        "lifecycle_stage": "PRODUCTION",
        "processes_personal_data": False,
        "makes_automated_decisions": False,
        "high_risk": False,
        "has_vendors": False,
        "has_external_components": False,
        "has_external_inference": False,
        "uses_external_observability": False,
        "has_cross_border_flow": False,
        "non_india_regions": [],
        "is_production": True,
        "owner_assigned": True,
        "is_reviewed": True,
    }
    base.update(kwargs)
    return base


def _ctx(**kwargs) -> ControlContext:
    return ControlContext(organization_id=ORG, assessment_date=DATE, **kwargs)


# --- is_ai_scoped ---------------------------------------------------------------


def test_is_ai_scoped_false_for_empty():
    assert is_ai_scoped(None) is False
    assert is_ai_scoped({}) is False
    assert is_ai_scoped({"sectors": [], "ai_types": [], "conditions": []}) is False


def test_is_ai_scoped_true_when_any_dimension_present():
    assert is_ai_scoped({"sectors": ["bfsi"]}) is True
    assert is_ai_scoped({"ai_types": ["llm"]}) is True
    assert is_ai_scoped({"conditions": ["high_risk"]}) is True
    assert is_ai_scoped({"sectors": ["all"]}) is True  # wildcard still AI-scoped


# --- system_matches -------------------------------------------------------------


def test_sector_scoping():
    ap = {"sectors": ["bfsi"], "ai_types": ["all"], "conditions": []}
    assert system_matches(ap, _facts(sector="bfsi")) is True
    assert system_matches(ap, _facts(sector="general")) is False


def test_sector_wildcard_matches_any():
    ap = {"sectors": ["all"], "ai_types": ["all"], "conditions": []}
    assert system_matches(ap, _facts(sector="healthcare")) is True


def test_ai_type_scoping_is_case_insensitive():
    ap = {"sectors": ["all"], "ai_types": ["llm", "generative"], "conditions": []}
    assert system_matches(ap, _facts(system_type="LLM")) is True
    assert system_matches(ap, _facts(system_type="ML_MODEL")) is False


def test_conditions_all_must_hold():
    ap = {"sectors": ["all"], "ai_types": ["all"], "conditions": ["high_risk", "makes_automated_decisions"]}
    assert system_matches(ap, _facts(high_risk=True, makes_automated_decisions=True)) is True
    assert system_matches(ap, _facts(high_risk=True, makes_automated_decisions=False)) is False


def test_condition_alias_maps_to_fact_key():
    # "automated_decisions" alias resolves to makes_automated_decisions.
    ap = {"conditions": ["automated_decisions"]}
    assert system_matches(ap, _facts(makes_automated_decisions=True)) is True
    assert system_matches(ap, _facts(makes_automated_decisions=False)) is False


def test_applicable_systems_filters_inventory():
    ap = {"sectors": ["bfsi"], "ai_types": ["all"], "conditions": ["processes_personal_data"]}
    systems = [
        _facts(name="A", sector="bfsi", processes_personal_data=True),
        _facts(name="B", sector="bfsi", processes_personal_data=False),
        _facts(name="C", sector="general", processes_personal_data=True),
    ]
    matched = applicable_systems(ap, systems)
    assert [s["name"] for s in matched] == ["A"]


# --- evaluate() routing ---------------------------------------------------------


def test_ai_scoped_control_not_applicable_when_no_system_matches():
    ap = {"sectors": ["bfsi"], "ai_types": ["all"], "conditions": ["processes_personal_data"]}
    ctx = _ctx(ai_systems=[_facts(sector="general")])
    result = evaluate("rbi_localization", ctx, "RBI-LOCALIZATION-001", ap)
    assert result.status == ControlStatus.NOT_APPLICABLE.value
    assert "scope" in result.reason.lower()


def test_ai_scoped_control_not_applicable_when_inventory_empty():
    ap = {"sectors": ["bfsi"], "ai_types": ["all"], "conditions": []}
    result = evaluate("rbi_localization", _ctx(ai_systems=[]), "RBI-LOCALIZATION-001", ap)
    assert result.status == ControlStatus.NOT_APPLICABLE.value


def test_non_ai_scoped_control_uses_org_level_evaluator():
    # No applies_to -> routed to the generic/org-level evaluator (rights here).
    ctx = _ctx(dsr_configured=True)
    assert evaluate("rights", ctx, "DPDP-RIGHTS-001", None).status == ControlStatus.PASS.value


# --- RBI evaluators -------------------------------------------------------------


def test_rbi_localization_fail_on_non_india_region():
    ap = {"sectors": ["bfsi"], "ai_types": ["all"], "conditions": ["processes_personal_data"]}
    ctx = _ctx(
        ai_systems=[
            _facts(sector="bfsi", processes_personal_data=True, non_india_regions=["us"])
        ]
    )
    result = evaluate("rbi_localization", ctx, "RBI-LOCALIZATION-001", ap)
    assert result.status == ControlStatus.FAIL.value
    assert "us" in result.reason


def test_rbi_localization_pass_when_india_only():
    ap = {"sectors": ["bfsi"], "ai_types": ["all"], "conditions": ["processes_personal_data"]}
    ctx = _ctx(
        ai_systems=[_facts(sector="bfsi", processes_personal_data=True, non_india_regions=[])]
    )
    assert evaluate("rbi_localization", ctx, "RBI-LOCALIZATION-001", ap).status == ControlStatus.PASS.value


def test_rbi_logging_needs_review_with_external_observability():
    ap = {"sectors": ["bfsi"], "ai_types": ["all"], "conditions": ["uses_external_observability"]}
    ctx = _ctx(ai_systems=[_facts(sector="bfsi", uses_external_observability=True)])
    assert evaluate("rbi_logging_telemetry", ctx, "RBI-LOGGING-001", ap).status == ControlStatus.NEEDS_REVIEW.value


def test_ai_inference_needs_review_with_external_inference():
    ap = {"sectors": ["bfsi"], "ai_types": ["llm"], "conditions": ["has_external_inference"]}
    ctx = _ctx(ai_systems=[_facts(sector="bfsi", system_type="LLM", has_external_inference=True)])
    assert evaluate("ai_inference_region", ctx, "RBI-INFERENCE-001", ap).status == ControlStatus.NEEDS_REVIEW.value


def test_vendor_subprocessor_needs_review_with_vendors():
    ap = {"sectors": ["bfsi"], "ai_types": ["all"], "conditions": ["has_vendors"]}
    ctx = _ctx(ai_systems=[_facts(sector="bfsi", has_vendors=True)])
    assert evaluate("vendor_subprocessor", ctx, "RBI-VENDOR-001", ap).status == ControlStatus.NEEDS_REVIEW.value


# --- CERT-In evaluators ---------------------------------------------------------


def test_certin_logging_no_evidence_by_default():
    ap = {"sectors": ["all"], "ai_types": ["all"], "conditions": []}
    ctx = _ctx(ai_systems=[_facts()])
    assert evaluate("certin_logging_retention", ctx, "CERTIN-LOGS-001", ap).status == ControlStatus.NO_EVIDENCE.value


def test_certin_logging_pass_with_fresh_evidence():
    ap = {"sectors": ["all"], "ai_types": ["all"], "conditions": []}
    ctx = _ctx(
        ai_systems=[_facts()],
        evidence_by_control={"CERTIN-LOGS-001": [{"id": uuid.uuid4(), "status": EvidenceStatus.FRESH.value}]},
    )
    assert evaluate("certin_logging_retention", ctx, "CERTIN-LOGS-001", ap).status == ControlStatus.PASS.value


def test_certin_incident_pass_when_breach_workflow_configured():
    ap = {"sectors": ["all"], "ai_types": ["all"], "conditions": []}
    ctx = _ctx(ai_systems=[_facts()], breach_workflow_configured=True)
    assert evaluate("certin_incident", ctx, "CERTIN-INCIDENT-001", ap).status == ControlStatus.PASS.value


def test_certin_incident_no_evidence_without_workflow():
    ap = {"sectors": ["all"], "ai_types": ["all"], "conditions": []}
    ctx = _ctx(ai_systems=[_facts()], breach_workflow_configured=False)
    assert evaluate("certin_incident", ctx, "CERTIN-INCIDENT-001", ap).status == ControlStatus.NO_EVIDENCE.value


# --- MeitY evaluators -----------------------------------------------------------


def test_ai_inventory_no_evidence_when_no_systems():
    # Org-wide scope (all/all/[]) always runs the evaluator; with nothing
    # inventoried the honest result is NO_EVIDENCE (inventory the systems),
    # not NOT_APPLICABLE.
    ap = {"sectors": ["all"], "ai_types": ["all"], "conditions": []}
    assert evaluate("ai_inventory", _ctx(ai_systems=[]), "MEITY-INVENTORY-001", ap).status == ControlStatus.NO_EVIDENCE.value


def test_ai_inventory_partial_when_production_system_unreviewed():
    ap = {"sectors": ["all"], "ai_types": ["all"], "conditions": []}
    ctx = _ctx(ai_systems=[_facts(is_production=True, is_reviewed=False, owner_assigned=True)])
    assert evaluate("ai_inventory", ctx, "MEITY-INVENTORY-001", ap).status == ControlStatus.PARTIAL.value


def test_ai_inventory_pass_when_all_owned_and_reviewed():
    ap = {"sectors": ["all"], "ai_types": ["all"], "conditions": []}
    ctx = _ctx(ai_systems=[_facts(is_production=True, is_reviewed=True, owner_assigned=True)])
    assert evaluate("ai_inventory", ctx, "MEITY-INVENTORY-001", ap).status == ControlStatus.PASS.value


def test_meity_bias_no_evidence_for_high_risk_without_evidence():
    ap = {"sectors": ["all"], "ai_types": ["ml_model", "llm"], "conditions": ["high_risk"]}
    ctx = _ctx(ai_systems=[_facts(system_type="LLM", high_risk=True)])
    assert evaluate("meity_bias", ctx, "MEITY-BIAS-001", ap).status == ControlStatus.NO_EVIDENCE.value


def test_meity_bias_not_applicable_when_not_high_risk():
    ap = {"sectors": ["all"], "ai_types": ["ml_model", "llm"], "conditions": ["high_risk"]}
    ctx = _ctx(ai_systems=[_facts(system_type="LLM", high_risk=False)])
    assert evaluate("meity_bias", ctx, "MEITY-BIAS-001", ap).status == ControlStatus.NOT_APPLICABLE.value


def test_meity_oversight_no_evidence_for_automated_decisions():
    ap = {"sectors": ["all"], "ai_types": ["all"], "conditions": ["automated_decisions"]}
    ctx = _ctx(ai_systems=[_facts(makes_automated_decisions=True)])
    assert evaluate("meity_human_oversight", ctx, "MEITY-OVERSIGHT-001", ap).status == ControlStatus.NO_EVIDENCE.value


def test_model_lineage_pass_with_evidence():
    ap = {"sectors": ["all"], "ai_types": ["all"], "conditions": []}
    ctx = _ctx(
        ai_systems=[_facts()],
        evidence_by_control={"MEITY-LINEAGE-001": [{"id": uuid.uuid4(), "status": EvidenceStatus.FRESH.value}]},
    )
    assert evaluate("model_lineage", ctx, "MEITY-LINEAGE-001", ap).status == ControlStatus.PASS.value
