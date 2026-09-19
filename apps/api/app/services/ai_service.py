"""AI investigation service.

The AI is an investigation and explanation layer, never the source of regulatory
truth. It analyzes evidence already collected by the deterministic platform.

Key guarantees enforced here:
- Raw personal data is never sent to the model. Inputs are sanitized to field
  names, data categories, asset types, risk levels, masked examples, aggregate
  statistics, control results, and evidence summaries.
- Output is validated against a strict Pydantic schema; on failure we retry once
  and then fall back to a safe deterministic narrative.
- Results are cached by a SHA256 fingerprint of the sanitized input so repeated
  investigations reuse prior output (cost control).
- When ANTHROPIC_API_KEY is absent, we operate in deterministic mode and still
  produce useful output so the platform is fully demoable offline.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import utcnow
from app.core.enums import AIInvestigationStatus, OwnerType, Priority
from app.models.evidence import ControlEvidence, Evidence
from app.models.findings import Finding
from app.models.identity import AuditEvent, Organization
from app.models.inventory import AssetField, DataAsset, DataFlow, Vendor
from app.models.operations import AIInvestigation
from app.models.regulatory import Control, ControlAssessment, Obligation
from app.services.assessment_service import get_assessment_date
from app.services.evidence_service import compute_freshness

SYSTEM_PROMPT = (
    "You are a compliance investigation assistant.\n"
    "You do not determine legal compliance.\n"
    "You analyze evidence collected by the platform.\n"
    "You must not invent regulations, legal obligations, evidence, facts, controls, "
    "or system states.\n"
    "Every factual claim must derive from supplied evidence.\n"
    "When evidence is insufficient, say so.\n"
    "Separate: observed fact, inferred hypothesis, recommendation, legal review required.\n"
    "Never fabricate citations.\n"
    "Respond ONLY with a single JSON object matching the requested schema."
)


# --- Output schema (validated with Pydantic) -----------------------------------


class RootCause(BaseModel):
    title: str
    likelihood: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    reasoning: str


class RecommendedAction(BaseModel):
    action: str
    priority: str = Priority.MEDIUM.value
    owner_type: str = OwnerType.PRIVACY.value
    requires_human_review: bool = True


class InvestigationResult(BaseModel):
    summary: str
    root_causes: list[RootCause] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    legal_review_required: bool = True
    uncertainty: str = ""


# --- Sanitization ---------------------------------------------------------------

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:(?:\+|00)\d{1,3}[\s-]?)?(?:\d[\s-]?){7,13}\d")
_LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9/+_=-]{24,}\b")
_SECRET_KEY_RE = re.compile(
    r"(?i)(password|passwd|secret|api[_-]?key|token|credential|authorization|private[_-]?key)"
    r"\s*[:=]\s*\S+"
)


def sanitize_text(value: str | None) -> str | None:
    """Redact anything that could be raw PII or a secret from free text."""
    if not value:
        return value
    out = _SECRET_KEY_RE.sub(lambda m: m.group(1) + "=[REDACTED]", value)
    out = _EMAIL_RE.sub("[REDACTED_EMAIL]", out)
    out = _LONG_TOKEN_RE.sub("[REDACTED_TOKEN]", out)
    out = _PHONE_RE.sub("[REDACTED_NUMBER]", out)
    return out


def _mask_examples(raw: str | None) -> list[str]:
    """Field.masked_examples already stores masked samples; sanitize defensively."""
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return [sanitize_text(p) or "" for p in parts][:5]


def build_investigation_input(db: Session, org: Organization, finding: Finding) -> dict:
    """Assemble a sanitized, structured context for the investigator.

    Only non-identifying, aggregate, and masked information is included. No raw
    values, names, emails, phone numbers, addresses, secrets, or credentials.
    """
    assessment_date = get_assessment_date(org)

    control_ctx: dict | None = None
    if finding.control_id:
        control = db.get(Control, finding.control_id)
        if control:
            obligation = db.get(Obligation, control.obligation_id)
            latest = db.scalar(
                select(ControlAssessment)
                .where(
                    ControlAssessment.organization_id == org.id,
                    ControlAssessment.control_id == control.id,
                )
                .order_by(ControlAssessment.created_at.desc())
                .limit(1)
            )
            control_ctx = {
                "code": control.code,
                "title": control.title,
                "category": control.category,
                "legal_reference": obligation.legal_reference if obligation else None,
                "source_section": obligation.source_section if obligation else None,
                "assessment_status": latest.status if latest else None,
                "assessment_score": latest.score if latest else None,
                "assessment_reason": sanitize_text(latest.reason) if latest else None,
            }

    asset_ctx: dict | None = None
    if finding.asset_id:
        asset = db.get(DataAsset, finding.asset_id)
        if asset:
            fields = list(
                db.scalars(select(AssetField).where(AssetField.asset_id == asset.id))
            )
            asset_ctx = {
                "asset_type": asset.asset_type,
                "classification": asset.classification,
                "sensitivity_level": asset.sensitivity_level,
                "environment": asset.environment,
                "row_count": asset.row_count,
                "field_summary": [
                    {
                        "field_name": f.name,
                        "category": f.category,
                        "classification": f.classification,
                        "confidence_band": f.confidence_band,
                        "masked_examples": _mask_examples(f.masked_examples),
                    }
                    for f in fields[:40]
                ],
            }

    vendor_ctx: dict | None = None
    if finding.vendor_id:
        vendor = db.get(Vendor, finding.vendor_id)
        if vendor:
            vendor_ctx = {
                "service_type": vendor.service_type,
                "country": vendor.country,
                "contract_status": vendor.contract_status,
                "risk_level": vendor.risk_level,
            }

    flow_ctx: dict | None = None
    if finding.data_flow_id:
        flow = db.get(DataFlow, finding.data_flow_id)
        if flow:
            flow_ctx = {
                "flow_type": flow.flow_type,
                "contains_personal_data": flow.contains_personal_data,
                "contains_sensitive_category": flow.contains_sensitive_category,
                "cross_border": flow.cross_border,
            }

    # Evidence summaries linked to the finding's control (never raw contents).
    evidence_summaries: list[dict] = []
    if finding.control_id:
        rows = db.execute(
            select(Evidence, ControlEvidence)
            .join(ControlEvidence, ControlEvidence.evidence_id == Evidence.id)
            .where(
                ControlEvidence.control_id == finding.control_id,
                Evidence.organization_id == org.id,
            )
        ).all()
        for ev, ce in rows:
            evidence_summaries.append(
                {
                    "id": str(ev.id),
                    "type": ev.type,
                    "name": sanitize_text(ev.name),
                    "relation": ce.relation_type,
                    "freshness": compute_freshness(
                        ev.collected_at, ev.expires_at, assessment_date
                    ),
                    "hash": ev.hash,
                }
            )

    # Recent audit trail for the finding (actions only, no PII).
    audit_trail = [
        {"action": a.action, "at": a.created_at.isoformat() if a.created_at else None}
        for a in db.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.organization_id == org.id,
                AuditEvent.entity_type == "finding",
                AuditEvent.entity_id == str(finding.id),
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(10)
        )
    ]

    return {
        "finding": {
            "title": sanitize_text(finding.title),
            "description": sanitize_text(finding.description),
            "severity": finding.severity,
            "risk_score": finding.risk_score,
            "risk_breakdown": finding.risk_breakdown,
            "status": finding.status,
            "source": finding.source,
            "data_categories": finding.data_categories,
            "recommended_actions": finding.recommended_actions,
        },
        "control": control_ctx,
        "asset": asset_ctx,
        "vendor": vendor_ctx,
        "data_flow": flow_ctx,
        "evidence": evidence_summaries,
        "audit_trail": audit_trail,
        "assessment_date": assessment_date.isoformat(),
    }


def _input_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:64]


# --- Deterministic fallback -----------------------------------------------------


def _deterministic_result(payload: dict) -> InvestigationResult:
    finding = payload.get("finding", {})
    control = payload.get("control") or {}
    evidence = payload.get("evidence") or []
    fresh_evidence = [e for e in evidence if e.get("freshness") == "FRESH"]

    control_desc = control.get("title") or finding.get("title") or "this finding"
    reason = control.get("assessment_reason")

    summary_parts = [
        f"This {finding.get('severity', 'MEDIUM')}-severity finding "
        f"(risk score {finding.get('risk_score', 0)}) concerns {control_desc}."
    ]
    if reason:
        summary_parts.append(f"The deterministic control assessment reported: {reason}")
    if not fresh_evidence:
        summary_parts.append(
            "No current (fresh) supporting evidence is linked, which is the primary "
            "driver of the control gap."
        )
    summary = " ".join(summary_parts)

    root_causes: list[RootCause] = []
    if not fresh_evidence:
        root_causes.append(
            RootCause(
                title="Missing or stale supporting evidence",
                likelihood=0.8,
                evidence=[e["id"] for e in evidence],
                reasoning=(
                    "The control has no fresh evidence linked at the current assessment "
                    "date, so operation of the safeguard cannot be demonstrated."
                ),
            )
        )
    else:
        root_causes.append(
            RootCause(
                title="Control operating but flagged by policy thresholds",
                likelihood=0.5,
                evidence=[e["id"] for e in fresh_evidence],
                reasoning=(
                    "Fresh evidence exists; the finding likely reflects a partial or "
                    "threshold-based gap rather than a complete control failure."
                ),
            )
        )

    recommended: list[RecommendedAction] = []
    actions = finding.get("recommended_actions") or []
    if isinstance(actions, list):
        for a in actions[:5]:
            recommended.append(
                RecommendedAction(
                    action=str(a),
                    priority=finding.get("severity", Priority.MEDIUM.value),
                    owner_type=OwnerType.PRIVACY.value,
                    requires_human_review=True,
                )
            )
    if not recommended:
        recommended.append(
            RecommendedAction(
                action="Attach current evidence demonstrating this control operates.",
                priority=finding.get("severity", Priority.MEDIUM.value),
                owner_type=OwnerType.PRIVACY.value,
                requires_human_review=True,
            )
        )

    missing = [] if fresh_evidence else ["Current evidence that the control operates"]

    return InvestigationResult(
        summary=summary,
        root_causes=root_causes,
        recommended_actions=recommended,
        missing_evidence=missing,
        legal_review_required=True,
        uncertainty=(
            "Generated deterministically from platform evidence. This is an internal "
            "governance aid and does not constitute a legal compliance determination."
        ),
    )


# --- Anthropic adapter ----------------------------------------------------------


def _extract_json(text: str) -> dict:
    """Extract the first JSON object from a model response."""
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response.")
    return json.loads(text[start : end + 1])


def _call_anthropic(payload: dict) -> tuple[InvestigationResult | None, str | None, str]:
    """Call Anthropic and validate. Returns (result, raw_redacted, model)."""
    model = settings.anthropic_model
    schema_hint = json.dumps(InvestigationResult.model_json_schema())
    user_content = (
        "Investigate the following finding using ONLY the supplied evidence. "
        "Return JSON conforming exactly to this schema:\n"
        f"{schema_hint}\n\nContext:\n{json.dumps(payload, default=str)}"
    )
    try:
        import anthropic  # noqa: PLC0415
    except ImportError:
        return None, None, model

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    last_raw: str | None = None
    for _attempt in range(2):
        try:
            message = client.messages.create(
                model=model,
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = "".join(
                block.text for block in message.content if getattr(block, "type", None) == "text"
            )
            last_raw = sanitize_text(raw)
            data = _extract_json(raw)
            return InvestigationResult.model_validate(data), last_raw, model
        except (PydanticValidationError, ValueError, json.JSONDecodeError):
            continue
        except Exception:  # noqa: BLE001 - network/SDK errors -> deterministic fallback
            return None, last_raw, model
    return None, last_raw, model


# --- Public entrypoint ----------------------------------------------------------


def investigate(
    db: Session, org: Organization, finding: Finding, *, user_id: uuid.UUID | None = None
) -> AIInvestigation:
    """Run (or reuse a cached) AI investigation for a finding."""
    payload = build_investigation_input(db, org, finding)
    input_hash = _input_hash(payload)

    cached = db.scalar(
        select(AIInvestigation)
        .where(
            AIInvestigation.organization_id == org.id,
            AIInvestigation.finding_id == finding.id,
            AIInvestigation.input_hash == input_hash,
            AIInvestigation.status == AIInvestigationStatus.COMPLETED.value,
        )
        .order_by(AIInvestigation.created_at.desc())
        .limit(1)
    )
    if cached is not None:
        return cached

    mode = settings.effective_ai_mode
    result: InvestigationResult | None = None
    raw_redacted: str | None = None
    used_model: str | None = None

    if mode == "anthropic":
        result, raw_redacted, used_model = _call_anthropic(payload)

    if result is None:
        # Deterministic fallback (also the default when no API key is configured).
        result = _deterministic_result(payload)
        mode = "deterministic"
        used_model = None

    evidence_considered = [e["id"] for e in payload.get("evidence", [])]

    investigation = AIInvestigation(
        organization_id=org.id,
        finding_id=finding.id,
        input_hash=input_hash,
        model=used_model,
        mode=mode,
        status=AIInvestigationStatus.COMPLETED.value,
        summary=result.summary,
        root_causes=[rc.model_dump() for rc in result.root_causes],
        recommendations=[ra.model_dump() for ra in result.recommended_actions],
        missing_evidence=result.missing_evidence,
        legal_review_required=result.legal_review_required,
        uncertainty=result.uncertainty,
        evidence_considered=evidence_considered,
        raw_response_redacted=raw_redacted,
        input_sanitized=True,
        reviewed_by=None,
        created_at=utcnow(),
        completed_at=utcnow(),
    )
    db.add(investigation)
    db.flush()
    return investigation


def get_investigation(db: Session, org_id: uuid.UUID, investigation_id: uuid.UUID) -> AIInvestigation | None:
    inv = db.get(AIInvestigation, investigation_id)
    if inv is None or inv.organization_id != org_id:
        return None
    return inv


def list_investigations(db: Session, org_id: uuid.UUID, finding_id: uuid.UUID | None = None) -> list[AIInvestigation]:
    stmt = select(AIInvestigation).where(AIInvestigation.organization_id == org_id)
    if finding_id:
        stmt = stmt.where(AIInvestigation.finding_id == finding_id)
    stmt = stmt.order_by(AIInvestigation.created_at.desc())
    return list(db.scalars(stmt))
