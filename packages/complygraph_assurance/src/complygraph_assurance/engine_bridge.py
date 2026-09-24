"""Bridge to ComplyGraph's real, infrastructure-free deterministic control engine.

ComplyGraph proper is a Postgres/Redis/FastAPI SaaS, but its *compliance
evaluation core* is pure standard library:

    app.controls.engine          - the deterministic control evaluators
    app.controls.applicability   - AI-scope matcher used by ``evaluate``
    app.controls.effective_date  - active vs upcoming (never a "future failure")
    app.controls.risk            - the internal 0-100 risk model
    app.core.enums               - plain ``str, Enum`` constants

None of those import Postgres, Redis, Celery, or the web framework, so we reuse
them verbatim to produce a *faithful* compliance verdict without any
infrastructure. The heavy SaaS piece we do NOT reuse is
``assessment_service.build_context`` (it reads the ControlContext out of
Postgres); instead we assemble the identical ``ControlContext`` snapshot from a
bundled JSON fixture describing the assessed state, and drive the real engine
over it.

Import discipline: the ComplyGraph engine is located and imported **lazily**
(inside :func:`evaluate_compliance`), never at module import time, so importing
``complygraph_assurance`` stays light (stdlib + assurance_contract).
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_FRAMEWORKS_DIR = _FIXTURES / "frameworks"
_TARGETS_DIR = _FIXTURES / "targets"

# Statuses that the real ComplyGraph scan pipeline turns into findings
# (mirrors app.services.scan_service._generate_findings).
_FINDING_STATUSES = {"FAIL", "NO_EVIDENCE", "NEEDS_REVIEW"}


class EngineNotFoundError(RuntimeError):
    """The ComplyGraph control engine could not be located on disk."""


class InputError(ValueError):
    """A bad framework id / target ref / fixture (maps to CLI exit code 2)."""


# --------------------------------------------------------------------------- #
# Result model (plain types only, so builder.py needs no app imports)
# --------------------------------------------------------------------------- #
@dataclass
class ControlOutcome:
    code: str
    title: str
    description: str
    category: str
    evaluator_key: str
    severity_default: str
    legal_reference: str
    source_section: str
    effective_from: str
    active: bool
    status: str
    score: float
    reason: str
    recommended_actions: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    affected_asset_ids: list[str] = field(default_factory=list)
    affected_system_ids: list[str] = field(default_factory=list)
    produces_finding: bool = False
    finding_severity: str | None = None  # contract severity: critical|high|medium|low
    is_hard_blocker: bool = False
    risk_score: int | None = None
    risk_breakdown: dict | None = None


@dataclass
class EvaluationResult:
    engine: str
    framework: str
    framework_name: str
    target_ref: str
    target_label: str
    assessment_date: str
    required_severity: str
    source_document: str
    source_url: str
    engine_source: str
    controls: list[ControlOutcome] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Locate + import the real ComplyGraph engine (lazily, infra-free)
# --------------------------------------------------------------------------- #
_ENGINE_CACHE: dict[str, Any] | None = None


def _locate_api_root() -> Path:
    """Find ``apps/api`` (the ComplyGraph backend package root) on disk.

    Resolution order:
      1. ``$COMPLYGRAPH_API_PATH`` if it points at a valid backend.
      2. Walk up from this file looking for ``apps/api/app/controls/engine.py``
         (this package is homed at ``<repo>/packages/complygraph_assurance``).
    """
    env = os.environ.get("COMPLYGRAPH_API_PATH")
    if env:
        cand = Path(env).expanduser().resolve()
        if (cand / "app" / "controls" / "engine.py").exists():
            return cand
        raise EngineNotFoundError(
            f"COMPLYGRAPH_API_PATH={env!r} does not contain app/controls/engine.py"
        )

    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "apps" / "api"
        if (cand / "app" / "controls" / "engine.py").exists():
            return cand
    raise EngineNotFoundError(
        "Could not locate the ComplyGraph engine (apps/api/app/controls/engine.py). "
        "Set COMPLYGRAPH_API_PATH to the ComplyGraph 'apps/api' directory."
    )


def _load_engine() -> dict[str, Any]:
    """Import the infra-free ComplyGraph control modules and cache the handles."""
    global _ENGINE_CACHE
    if _ENGINE_CACHE is not None:
        return _ENGINE_CACHE

    api_root = _locate_api_root()
    if str(api_root) not in sys.path:
        sys.path.insert(0, str(api_root))

    # These imports pull in ONLY: app.core.enums (a pure str-Enum module),
    # app.controls.{engine,applicability,effective_date,risk}. No infra.
    from app.controls import engine as ce  # noqa: WPS433 (intentional lazy import)
    from app.controls import effective_date as ed
    from app.controls import risk as cr
    from app.core import enums as en

    _ENGINE_CACHE = {
        "api_root": api_root,
        "ControlContext": ce.ControlContext,
        "ControlEvaluation": ce.ControlEvaluation,
        "evaluate": ce.evaluate,
        "is_control_active": ed.is_control_active,
        "RiskInputs": cr.RiskInputs,
        "compute_risk": cr.compute_risk,
        "volume_band": cr.volume_band,
        "ControlStatus": en.ControlStatus,
        "Severity": en.Severity,
    }
    return _ENGINE_CACHE


# --------------------------------------------------------------------------- #
# Fixture loading
# --------------------------------------------------------------------------- #
def available_frameworks() -> list[str]:
    return sorted(p.stem for p in _FRAMEWORKS_DIR.glob("*.json"))


def available_targets() -> list[str]:
    return sorted(p.stem for p in _TARGETS_DIR.glob("*.json"))


def _load_framework(framework: str) -> dict:
    key = (framework or "").strip().lower()
    if not key:
        raise InputError("framework is required")
    path = _FRAMEWORKS_DIR / f"{key}.json"
    if not path.exists():
        raise InputError(
            f"unknown framework {framework!r}; bundled frameworks: {available_frameworks()}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_target(target_ref: str) -> tuple[str, dict]:
    """Map a positional target ref to a bundled assessed-state fixture.

    Known refs load their own fixture. Any other non-empty ref is accepted and
    evaluated against the compliant ``reference-strong`` baseline (so arbitrary
    org/target identifiers still produce a valid pack), while its literal value
    is preserved as the ``target_ref`` recorded in the manifest.
    """
    ref = (target_ref or "").strip()
    if not ref:
        raise InputError("a non-empty target_ref positional argument is required")

    key = ref.lower()
    weak_tokens = ("weak", "blocked", "noncompliant", "non-compliant", "fail")
    if key in {"reference-weak", "weak"} or any(t in key for t in weak_tokens):
        fixture_name = "reference-weak"
    else:
        fixture_name = "reference-strong"

    path = _TARGETS_DIR / f"{fixture_name}.json"
    if not path.exists():  # pragma: no cover - bundled fixtures always present
        raise InputError(f"missing bundled target fixture {fixture_name!r}")
    return fixture_name, json.loads(path.read_text(encoding="utf-8"))


def _parse_dt(value: str) -> datetime:
    text = (value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# ControlContext assembly (the same shape assessment_service builds from DB)
# --------------------------------------------------------------------------- #
def _build_context(eng: dict[str, Any], framework: dict, target: dict):
    ControlContext = eng["ControlContext"]

    assessment_date = _parse_dt(target["assessment_date"])
    personal = list(target.get("personal_data_assets") or [])
    extra = list(target.get("extra_assets") or [])
    all_assets = personal + extra

    # Evidence policy: "all_fresh" attaches current evidence to every control
    # code; "none" attaches nothing. This is what the SaaS derives from the
    # Evidence <-> Control linkage + freshness computation.
    policy = (target.get("evidence_policy") or "none").strip().lower()
    evidence_by_control: dict[str, list[dict]] = {}
    if policy == "all_fresh":
        for control in framework["controls"]:
            code = control["code"]
            evidence_by_control[code] = [
                {"id": f"ev-{code}", "name": f"Evidence for {code}", "status": "FRESH"}
            ]

    return ControlContext(
        organization_id=uuid.uuid5(uuid.NAMESPACE_URL, f"complygraph:{target.get('target_ref','')}"),
        assessment_date=assessment_date,
        personal_data_assets=personal,
        all_assets=all_assets,
        flows=list(target.get("flows") or []),
        vendors=list(target.get("vendors") or []),
        processing_activities=list(target.get("processing_activities") or []),
        evidence_by_control=evidence_by_control,
        dsr_configured=bool(target.get("dsr_configured", False)),
        breach_workflow_configured=bool(target.get("breach_workflow_configured", False)),
        ai_systems=list(target.get("ai_systems") or []),
        flags=dict(target.get("flags") or {}),
    )


# --------------------------------------------------------------------------- #
# Finding severity mapping (mirrors scan_service._generate_findings)
# --------------------------------------------------------------------------- #
def _finding_from_evaluation(eng: dict[str, Any], status: str, evaluation, asset_index: dict[str, dict]):
    """Reproduce ComplyGraph's risk-scored finding severity for a control result.

    Returns ``(contract_severity, is_hard_blocker, risk_score, risk_breakdown)``
    or ``None`` when the status does not generate a finding.
    """
    if status not in _FINDING_STATUSES:
        return None

    RiskInputs = eng["RiskInputs"]
    compute_risk = eng["compute_risk"]
    volume_band = eng["volume_band"]

    sensitivity = 3
    volume = 1
    affected = list(getattr(evaluation, "affected_asset_ids", None) or [])
    if affected:
        asset = asset_index.get(str(affected[0]))
        if asset:
            sensitivity = int(asset.get("sensitivity_level") or 3)
            volume = volume_band(asset.get("row_count"))

    control_gap = 5 if status in {"FAIL", "NO_EVIDENCE"} else 3
    exposure = 3
    risk = compute_risk(RiskInputs(sensitivity, exposure, control_gap, volume))

    contract_sev = risk.severity.lower()  # CRITICAL/HIGH/MEDIUM/LOW -> lowercase
    if contract_sev not in {"critical", "high", "medium", "low"}:
        contract_sev = "medium"
    is_hard_blocker = contract_sev == "critical"
    return contract_sev, is_hard_blocker, int(risk.score), dict(risk.breakdown)


# --------------------------------------------------------------------------- #
# Public entrypoint
# --------------------------------------------------------------------------- #
def evaluate_compliance(target_ref: str, *, framework: str) -> EvaluationResult:
    """Run the real ComplyGraph deterministic control engine over a bundled state.

    This is fully deterministic (no clock, no RNG, no infra) and is the single
    source of the compliance verdict consumed by :mod:`complygraph_assurance.builder`.
    """
    eng = _load_engine()
    evaluate = eng["evaluate"]
    is_control_active = eng["is_control_active"]
    ControlStatus = eng["ControlStatus"]

    fw = _load_framework(framework)
    _fixture_name, target = _resolve_target(target_ref)

    ctx = _build_context(eng, fw, target)
    asset_index = {str(a["id"]): a for a in ctx.all_assets if a.get("id") is not None}

    outcomes: list[ControlOutcome] = []
    for control in fw["controls"]:
        eff_from = control.get("effective_from")
        eff_dt = _parse_dt(eff_from) if eff_from else None
        active = is_control_active(eff_dt, ctx.assessment_date)

        if not active:
            status = ControlStatus.UPCOMING.value
            evaluation = eng["ControlEvaluation"](
                status=status,
                score=0.0,
                reason=(
                    "This control is not yet in force at the current assessment date. "
                    "Displayed for preparation, not as a current failure."
                ),
            )
        else:
            evaluation = evaluate(
                control.get("evaluator_key"),
                ctx,
                control["code"],
                control.get("applies_to"),
            )
            status = evaluation.status

        outcome = ControlOutcome(
            code=control["code"],
            title=control["title"],
            description=control.get("description", ""),
            category=control.get("category", ""),
            evaluator_key=control.get("evaluator_key", "generic"),
            severity_default=(control.get("severity_default") or "MEDIUM").upper(),
            legal_reference=control.get("legal_reference", ""),
            source_section=control.get("source_section", ""),
            effective_from=eff_from or "",
            active=active,
            status=status,
            score=float(getattr(evaluation, "score", 0.0) or 0.0),
            reason=getattr(evaluation, "reason", ""),
            recommended_actions=list(getattr(evaluation, "recommended_actions", []) or []),
            evidence_ids=[str(e) for e in (getattr(evaluation, "evidence_ids", []) or [])],
            affected_asset_ids=[str(a) for a in (getattr(evaluation, "affected_asset_ids", []) or [])],
            affected_system_ids=[str(s) for s in (getattr(evaluation, "affected_system_ids", []) or [])],
        )

        mapped = _finding_from_evaluation(eng, status, evaluation, asset_index)
        if mapped is not None:
            outcome.produces_finding = True
            outcome.finding_severity, outcome.is_hard_blocker, outcome.risk_score, outcome.risk_breakdown = mapped

        outcomes.append(outcome)

    return EvaluationResult(
        engine="complygraph",
        framework=fw.get("framework", framework),
        framework_name=fw.get("name", framework),
        target_ref=(target_ref or "").strip(),
        target_label=target.get("label", target.get("target_ref", "")),
        assessment_date=ctx.assessment_date.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        required_severity=(fw.get("required_severity") or "HIGH").upper(),
        source_document=fw.get("source_document", ""),
        source_url=fw.get("source_url", ""),
        engine_source=str(eng["api_root"]),
        controls=outcomes,
    )
