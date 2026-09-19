"""Deterministic control engine.

Controls are evaluated deterministically first (no LLM decides status). Each
control maps to an evaluator via `evaluator_key`. Evaluators receive a
ControlContext (a read-only snapshot of relevant org state) and return a
ControlEvaluation.

Every assessment produces a human-readable reason so the UI can answer
"Why is this a finding?".
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.core.enums import ControlStatus, EvidenceStatus


@dataclass
class ControlContext:
    """Read-only snapshot passed to evaluators."""

    organization_id: uuid.UUID
    assessment_date: datetime
    # Inventory
    personal_data_assets: list[dict] = field(default_factory=list)
    all_assets: list[dict] = field(default_factory=list)
    flows: list[dict] = field(default_factory=list)
    vendors: list[dict] = field(default_factory=list)
    processing_activities: list[dict] = field(default_factory=list)
    # Evidence indexed by control code -> list of evidence dicts
    evidence_by_control: dict[str, list[dict]] = field(default_factory=dict)
    # Operational
    dsr_configured: bool = False
    breach_workflow_configured: bool = False
    # Ad-hoc flags used by specific evaluators
    flags: dict = field(default_factory=dict)


@dataclass
class ControlEvaluation:
    status: str
    score: float  # 0-1
    reason: str
    evidence_ids: list[str] = field(default_factory=list)
    affected_asset_ids: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)


def _fresh_evidence(evidence: list[dict]) -> list[dict]:
    return [e for e in evidence if e.get("status") in {EvidenceStatus.FRESH.value, None}]


def _has_fresh_evidence(ctx: ControlContext, code: str) -> bool:
    ev = ctx.evidence_by_control.get(code, [])
    return any(e.get("status") == EvidenceStatus.FRESH.value for e in ev)


def _evidence_ids(ctx: ControlContext, code: str) -> list[str]:
    return [str(e["id"]) for e in ctx.evidence_by_control.get(code, [])]


def _any_expired(ctx: ControlContext, code: str) -> bool:
    return any(
        e.get("status") == EvidenceStatus.EXPIRED.value
        for e in ctx.evidence_by_control.get(code, [])
    )


# --- Individual evaluators ------------------------------------------------------


def eval_notice(ctx: ControlContext, code: str) -> ControlEvaluation:
    has_activity = bool(ctx.processing_activities)
    has_purpose = any(a.get("purpose") for a in ctx.processing_activities)
    has_notice = any(a.get("has_notice") for a in ctx.processing_activities)
    personal_mapped = bool(ctx.personal_data_assets)
    ev_ids = _evidence_ids(ctx, code)

    if has_activity and has_purpose and personal_mapped and (has_notice or _has_fresh_evidence(ctx, code)):
        return ControlEvaluation(
            ControlStatus.PASS.value, 1.0,
            "Processing activities define purposes, personal-data categories are mapped, "
            "and notice evidence is present.",
            evidence_ids=ev_ids,
        )
    if not personal_mapped:
        return ControlEvaluation(
            ControlStatus.NOT_APPLICABLE.value, 1.0,
            "No personal-data assets are currently mapped, so notice obligations are not yet applicable.",
        )
    missing = []
    if not has_activity:
        missing.append("processing activity")
    if not has_purpose:
        missing.append("declared purpose")
    if not (has_notice or ev_ids):
        missing.append("notice evidence")
    status = ControlStatus.NO_EVIDENCE.value if not ev_ids else ControlStatus.PARTIAL.value
    return ControlEvaluation(
        status, 0.4 if ev_ids else 0.0,
        f"Notice transparency incomplete. Missing: {', '.join(missing)}.",
        evidence_ids=ev_ids,
        recommended_actions=["Document processing purposes", "Publish and attach a privacy notice"],
    )


def eval_consent(ctx: ControlContext, code: str) -> ControlEvaluation:
    has_consent = any(a.get("has_consent") for a in ctx.processing_activities)
    has_purpose = any(a.get("purpose") for a in ctx.processing_activities)
    ev_ids = _evidence_ids(ctx, code)
    if has_purpose and (has_consent or _has_fresh_evidence(ctx, code)):
        return ControlEvaluation(
            ControlStatus.PASS.value, 1.0,
            "Purposes are defined and consent-capture evidence is present.",
            evidence_ids=ev_ids,
        )
    if not ev_ids and not has_consent:
        return ControlEvaluation(
            ControlStatus.NO_EVIDENCE.value, 0.0,
            "No consent-capture evidence is linked to this control.",
            recommended_actions=["Attach consent-capture configuration or logs"],
        )
    return ControlEvaluation(
        ControlStatus.PARTIAL.value, 0.5,
        "Consent handling is partially evidenced; withdrawal workflow evidence should be verified.",
        evidence_ids=ev_ids,
    )


def eval_consent_withdrawal(ctx: ControlContext, code: str) -> ControlEvaluation:
    ev_ids = _evidence_ids(ctx, code)
    if _has_fresh_evidence(ctx, code):
        return ControlEvaluation(
            ControlStatus.PASS.value, 1.0,
            "A consent-withdrawal workflow is evidenced.", evidence_ids=ev_ids,
        )
    return ControlEvaluation(
        ControlStatus.NO_EVIDENCE.value, 0.0,
        "No evidence of a consent-withdrawal mechanism was found.",
        recommended_actions=["Implement and evidence a consent-withdrawal workflow"],
    )


def eval_rights(ctx: ControlContext, code: str) -> ControlEvaluation:
    ev_ids = _evidence_ids(ctx, code)
    if ctx.dsr_configured:
        return ControlEvaluation(
            ControlStatus.PASS.value, 1.0,
            "A Data Principal rights-request intake and tracking workflow is operational.",
            evidence_ids=ev_ids,
        )
    return ControlEvaluation(
        ControlStatus.FAIL.value, 0.0,
        "No rights-request intake/tracking workflow is configured.",
        recommended_actions=["Enable the data-requests workflow and assign an owner"],
    )


def eval_security(ctx: ControlContext, code: str) -> ControlEvaluation:
    """Generic security evaluator; specialized by code suffix."""
    ev_ids = _evidence_ids(ctx, code)
    if _any_expired(ctx, code):
        return ControlEvaluation(
            ControlStatus.NEEDS_REVIEW.value, 0.5,
            "Supporting security evidence has expired and requires review.",
            evidence_ids=ev_ids,
            recommended_actions=["Refresh the expired security evidence"],
        )
    if _has_fresh_evidence(ctx, code):
        return ControlEvaluation(
            ControlStatus.PASS.value, 1.0,
            "Current security evidence supports this control.", evidence_ids=ev_ids,
        )
    if not ctx.personal_data_assets:
        return ControlEvaluation(
            ControlStatus.NOT_APPLICABLE.value, 1.0,
            "No personal-data assets are in scope for this security control yet.",
        )
    return ControlEvaluation(
        ControlStatus.NO_EVIDENCE.value, 0.0,
        "No current evidence demonstrates this security safeguard operates.",
        affected_asset_ids=[str(a["id"]) for a in ctx.personal_data_assets],
        recommended_actions=["Attach configuration or scan evidence for this safeguard"],
    )


def eval_breach(ctx: ControlContext, code: str) -> ControlEvaluation:
    ev_ids = _evidence_ids(ctx, code)
    if ctx.breach_workflow_configured or _has_fresh_evidence(ctx, code):
        return ControlEvaluation(
            ControlStatus.PASS.value, 1.0,
            "Breach intake, incident workflow and notification workflow are configured with an owner.",
            evidence_ids=ev_ids,
        )
    return ControlEvaluation(
        ControlStatus.NO_EVIDENCE.value, 0.0,
        "No breach-response workflow evidence was found.",
        recommended_actions=["Document the incident-response workflow and attach the policy"],
    )


def eval_retention(ctx: ControlContext, code: str) -> ControlEvaluation:
    ev_ids = _evidence_ids(ctx, code)
    personal_assets = ctx.personal_data_assets
    retention_defined = any(
        a.get("retention_period_days") for a in ctx.processing_activities
    )
    deletion_failed = ctx.flags.get("deletion_last_status") == "FAILED"

    if personal_assets and not retention_defined and not _has_fresh_evidence(ctx, code):
        return ControlEvaluation(
            ControlStatus.FAIL.value, 0.0,
            "Personal-data assets exist but no purpose-based retention policy is defined and "
            "no retention evidence is attached.",
            affected_asset_ids=[str(a["id"]) for a in personal_assets],
            recommended_actions=[
                "Define retention periods per purpose",
                "Attach evidence of scheduled deletion",
            ],
        )
    if deletion_failed:
        return ControlEvaluation(
            ControlStatus.FAIL.value, 0.2,
            "A retention policy exists but the most recent deletion execution failed.",
            evidence_ids=ev_ids,
            recommended_actions=["Investigate the failed deletion job", "Re-run and verify deletion"],
        )
    if retention_defined and _has_fresh_evidence(ctx, code):
        return ControlEvaluation(
            ControlStatus.PASS.value, 1.0,
            "Retention periods are defined and deletion execution evidence is current.",
            evidence_ids=ev_ids,
        )
    if not personal_assets:
        return ControlEvaluation(
            ControlStatus.NOT_APPLICABLE.value, 1.0,
            "No personal-data assets are currently in scope for retention.",
        )
    return ControlEvaluation(
        ControlStatus.PARTIAL.value, 0.5,
        "Retention is partially addressed; deletion execution evidence should be verified.",
        evidence_ids=ev_ids,
    )


def eval_vendor(ctx: ControlContext, code: str) -> ControlEvaluation:
    if not ctx.vendors:
        return ControlEvaluation(
            ControlStatus.NOT_APPLICABLE.value, 1.0, "No vendors are registered."
        )
    problem_vendors = [
        v for v in ctx.vendors
        if v.get("contract_status") in {None, "MISSING", "UNKNOWN"}
        and any(f.get("vendor_id") == v.get("id") and f.get("contains_personal_data") for f in ctx.flows)
    ]
    if problem_vendors:
        return ControlEvaluation(
            ControlStatus.FAIL.value, 0.0,
            "One or more vendors receive personal data without recorded processor-contract status.",
            recommended_actions=[
                "Record processor contract status",
                "Map data categories and purpose for each vendor flow",
            ],
        )
    return ControlEvaluation(
        ControlStatus.PASS.value, 1.0,
        "Registered vendors have contract status recorded and processing purposes mapped.",
    )


def eval_children(ctx: ControlContext, code: str) -> ControlEvaluation:
    ev_ids = _evidence_ids(ctx, code)
    if ctx.flags.get("processes_children_data"):
        if _has_fresh_evidence(ctx, code):
            return ControlEvaluation(
                ControlStatus.PASS.value, 1.0,
                "Age-verification / verifiable parental consent workflow is evidenced.",
                evidence_ids=ev_ids,
            )
        return ControlEvaluation(
            ControlStatus.NO_EVIDENCE.value, 0.0,
            "Children's data may be processed but no age-verification evidence exists.",
            recommended_actions=["Attach age-verification / parental-consent workflow evidence"],
        )
    return ControlEvaluation(
        ControlStatus.NOT_APPLICABLE.value, 1.0,
        "The organization does not indicate processing of children's personal data.",
    )


def eval_sdf(ctx: ControlContext, code: str) -> ControlEvaluation:
    ev_ids = _evidence_ids(ctx, code)
    if not ctx.flags.get("is_significant_data_fiduciary"):
        return ControlEvaluation(
            ControlStatus.NOT_APPLICABLE.value, 1.0,
            "The organization is not configured as a Significant Data Fiduciary.",
        )
    if _has_fresh_evidence(ctx, code):
        return ControlEvaluation(
            ControlStatus.PASS.value, 1.0,
            "DPIA / periodic audit evidence is present for the Significant Data Fiduciary obligations.",
            evidence_ids=ev_ids,
        )
    return ControlEvaluation(
        ControlStatus.NO_EVIDENCE.value, 0.0,
        "Significant Data Fiduciary obligations require DPIA / audit evidence that is not present.",
        recommended_actions=["Conduct and attach a DPIA", "Schedule and evidence a periodic audit"],
    )


def eval_crossborder(ctx: ControlContext, code: str) -> ControlEvaluation:
    cross = [f for f in ctx.flows if f.get("cross_border") and f.get("contains_personal_data")]
    if not cross:
        return ControlEvaluation(
            ControlStatus.NOT_APPLICABLE.value, 1.0,
            "No cross-border personal-data flows are currently mapped.",
        )
    if _has_fresh_evidence(ctx, code):
        return ControlEvaluation(
            ControlStatus.PASS.value, 1.0,
            "Cross-border transfers are governed with current evidence.",
            evidence_ids=_evidence_ids(ctx, code),
        )
    return ControlEvaluation(
        ControlStatus.NEEDS_REVIEW.value, 0.4,
        f"{len(cross)} cross-border personal-data flow(s) require governance review.",
        recommended_actions=["Review cross-border transfer basis and attach governance evidence"],
    )


def eval_governance(ctx: ControlContext, code: str) -> ControlEvaluation:
    ev_ids = _evidence_ids(ctx, code)
    if _has_fresh_evidence(ctx, code):
        return ControlEvaluation(
            ControlStatus.PASS.value, 1.0,
            "Privacy contact / responsible-person information is published and evidenced.",
            evidence_ids=ev_ids,
        )
    return ControlEvaluation(
        ControlStatus.NO_EVIDENCE.value, 0.0,
        "No evidence of published privacy-contact information.",
        recommended_actions=["Publish and attach privacy-contact information"],
    )


def eval_generic(ctx: ControlContext, code: str) -> ControlEvaluation:
    ev_ids = _evidence_ids(ctx, code)
    if _has_fresh_evidence(ctx, code):
        return ControlEvaluation(
            ControlStatus.PASS.value, 1.0, "Current supporting evidence is present.",
            evidence_ids=ev_ids,
        )
    return ControlEvaluation(
        ControlStatus.NO_EVIDENCE.value, 0.0, "No supporting evidence is linked to this control.",
    )


EVALUATORS = {
    "notice": eval_notice,
    "consent": eval_consent,
    "consent_withdrawal": eval_consent_withdrawal,
    "rights": eval_rights,
    "security": eval_security,
    "breach": eval_breach,
    "retention": eval_retention,
    "vendor": eval_vendor,
    "children": eval_children,
    "sdf": eval_sdf,
    "crossborder": eval_crossborder,
    "governance": eval_governance,
    "generic": eval_generic,
}


def evaluate(evaluator_key: str | None, ctx: ControlContext, code: str) -> ControlEvaluation:
    evaluator = EVALUATORS.get(evaluator_key or "generic", eval_generic)
    return evaluator(ctx, code)
