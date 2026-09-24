"""Assemble a Contract v1 ``assurance.json`` proof pack from an evaluation.

This module owns the mapping from ComplyGraph's domain (control assessments +
risk-scored findings) to the frozen Assurance Contract v1 shape (§2.3/§2.4 of
``D:\\assura\\PRODUCTION_READINESS.md`` and ``ASSURANCE_CONTRACT.md``):

  * ComplyGraph status  -> a shared Finding (severity/is_hard_blocker/...)
  * open findings       -> ``release_status`` (PASS / PASS_WITH_CONDITIONS / BLOCKED)
  * control coverage    -> the ``headline`` metrics block

It has no infrastructure or third-party dependencies beyond ``assurance_contract``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .engine_bridge import ControlOutcome, EvaluationResult

CONTRACT_VERSION = "1.0.0"
ENGINE = "complygraph"

CANONICAL_STATUSES = ("PASS", "PASS_WITH_CONDITIONS", "BLOCKED")
_FAILED_STATUSES = {"FAIL", "NO_EVIDENCE"}
_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

DISCLAIMER = (
    "This assurance pack is an automated engineering compliance signal produced by "
    "ComplyGraph's deterministic control engine. It is not a legal certification, "
    "audit opinion, or legal advice."
)
NATIVE_REPORT_NAME = "complygraph.report.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _status_label(status: str) -> str:
    return status.replace("_", " ").title()


# --------------------------------------------------------------------------- #
# Verdict + findings
# --------------------------------------------------------------------------- #
def _derive_release_status(outcomes: list[ControlOutcome]) -> str:
    """Map open findings to the canonical verdict (ComplyGraph rule, runbook §1).

    * any open critical / hard-blocker finding      -> BLOCKED
    * else any open high or medium finding           -> PASS_WITH_CONDITIONS
    * else                                           -> PASS
    """
    has_blocker = any(o.is_hard_blocker for o in outcomes if o.produces_finding)
    if has_blocker:
        return "BLOCKED"
    has_high_med = any(
        (o.finding_severity in {"high", "medium"}) for o in outcomes if o.produces_finding
    )
    if has_high_med:
        return "PASS_WITH_CONDITIONS"
    return "PASS"


def _finding_from_outcome(o: ControlOutcome, framework: str) -> dict[str, Any]:
    remediation = "; ".join(o.recommended_actions) if o.recommended_actions else (
        "Attach current evidence or configure the workflow that satisfies this control."
    )
    evidence: dict[str, Any] = {
        "control_code": o.code,
        "framework": framework,
        "category": o.category,
        "evaluator_key": o.evaluator_key,
        "control_status": o.status,
        "control_score": round(o.score, 4),
        "severity_default": o.severity_default,
        "legal_reference": o.legal_reference,
        "source_section": o.source_section,
    }
    if o.risk_score is not None:
        evidence["risk_score"] = o.risk_score
    if o.risk_breakdown:
        evidence["risk_breakdown"] = o.risk_breakdown
    if o.evidence_ids:
        evidence["evidence_ids"] = o.evidence_ids
    if o.affected_asset_ids:
        evidence["affected_asset_ids"] = o.affected_asset_ids
    if o.affected_system_ids:
        evidence["affected_system_ids"] = o.affected_system_ids

    return {
        "title": f"{o.title} - {_status_label(o.status)}",
        "severity": o.finding_severity or "medium",
        "is_hard_blocker": bool(o.is_hard_blocker),
        "what_happened": o.reason,
        "expected": (
            f"Control {o.code} ({o.title}) is satisfied with current, sufficient evidence "
            f"under {framework}."
        ),
        "actual": f"Control evaluated {o.status} (score {round(o.score, 4)}).",
        "remediation": remediation,
        "evidence": evidence,
        "source_ref": f"complygraph.controls.{o.evaluator_key}",
    }


def _build_findings(outcomes: list[ControlOutcome], framework: str) -> list[dict[str, Any]]:
    findings = [
        _finding_from_outcome(o, framework) for o in outcomes if o.produces_finding
    ]
    findings.sort(key=lambda f: (_SEVERITY_RANK.get(f["severity"], 9), f["title"]))
    return findings


# --------------------------------------------------------------------------- #
# Headline metrics (Contract §6: complygraph)
# --------------------------------------------------------------------------- #
def _build_headline(result: EvaluationResult, findings: list[dict[str, Any]]) -> dict[str, Any]:
    outcomes = result.controls
    total = len(outcomes)
    active = [o for o in outcomes if o.active]
    upcoming = [o for o in outcomes if not o.active]
    not_applicable = [o for o in active if o.status == "NOT_APPLICABLE"]
    applicable = [o for o in active if o.status != "NOT_APPLICABLE"]
    passed = [o for o in applicable if o.status == "PASS"]
    failed = [o for o in applicable if o.status in _FAILED_STATUSES]
    partial = [o for o in applicable if o.status == "PARTIAL"]
    needs_review = [o for o in applicable if o.status == "NEEDS_REVIEW"]

    by_sev = {s: 0 for s in ("critical", "high", "medium", "low", "info")}
    for f in findings:
        by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1

    unmet_required = sorted(
        o.code
        for o in applicable
        if o.status in _FAILED_STATUSES and o.severity_default == result.required_severity
    )

    coverage = round(len(passed) / len(applicable), 4) if applicable else 1.0

    return {
        "framework": result.framework,
        "framework_name": result.framework_name,
        "assessed_at": result.assessment_date,
        "controls_total": total,
        "controls_active": len(active),
        "controls_upcoming": len(upcoming),
        "controls_applicable": len(applicable),
        "controls_passed": len(passed),
        "controls_failed": len(failed),
        "controls_partial": len(partial),
        "controls_needs_review": len(needs_review),
        "controls_not_applicable": len(not_applicable),
        "control_coverage": coverage,
        "coverage": coverage,
        "open_findings_total": len(findings),
        "open_findings_by_severity": by_sev,
        "required_severity": result.required_severity,
        "unmet_required_controls": unmet_required,
    }


# --------------------------------------------------------------------------- #
# Manifest / provenance
# --------------------------------------------------------------------------- #
def _content_hash(result: EvaluationResult, release_status: str, seed: int) -> str:
    """Stable hash over inputs + result (never the wall-clock ``created_at``)."""
    payload = {
        "engine": ENGINE,
        "contract_version": CONTRACT_VERSION,
        "framework": result.framework,
        "target_ref": result.target_ref,
        "assessment_date": result.assessment_date,
        "seed": int(seed),
        "release_status": release_status,
        "controls": sorted(
            (
                {
                    "code": o.code,
                    "status": o.status,
                    "finding_severity": o.finding_severity,
                    "is_hard_blocker": o.is_hard_blocker,
                }
                for o in result.controls
            ),
            key=lambda c: c["code"],
        ),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Public builders
# --------------------------------------------------------------------------- #
def build_assurance_pack(result: EvaluationResult, *, seed: int, target_ref: str, framework: str) -> dict[str, Any]:
    """Produce the Contract v1 §2.3 proof-pack dict for a compliance evaluation."""
    outcomes = result.controls
    findings = _build_findings(outcomes, framework)
    release_status = _derive_release_status(outcomes)

    # Fail closed: an indeterminate verdict is treated as BLOCKED with a
    # CRITICAL hard-blocker finding (Contract §2 fail-closed rule).
    if release_status not in CANONICAL_STATUSES:
        release_status = "BLOCKED"
        findings.insert(
            0,
            {
                "title": "Indeterminate compliance verdict - failing closed",
                "severity": "critical",
                "is_hard_blocker": True,
                "what_happened": "The compliance evaluation returned an unrecognized verdict.",
                "expected": "A verdict in {PASS, PASS_WITH_CONDITIONS, BLOCKED}.",
                "actual": f"Unrecognized verdict {release_status!r}.",
                "remediation": "Investigate the ComplyGraph export; treat the release as blocked.",
                "evidence": {"framework": framework, "target_ref": target_ref},
                "source_ref": "complygraph.assurance.builder",
            },
        )

    headline = _build_headline(result, findings)

    pack: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "engine": ENGINE,
        "engine_version": _engine_version(),
        "release_status": release_status,
        "headline": headline,
        "findings": findings,
        "manifest": {
            "content_hash": _content_hash(result, release_status, seed),
            "seed": int(seed),
            "created_at": _now_iso(),
            "target_ref": (target_ref or result.target_ref or "").strip(),
        },
        "evidence_paths": {"native_json": NATIVE_REPORT_NAME},
        "disclaimer": DISCLAIMER,
    }
    return pack


def build_native_report(result: EvaluationResult, pack: dict[str, Any]) -> dict[str, Any]:
    """A richer, ComplyGraph-native view (every control, not just findings)."""
    return {
        "engine": ENGINE,
        "engine_version": pack["engine_version"],
        "framework": result.framework,
        "framework_name": result.framework_name,
        "target_ref": result.target_ref,
        "target_label": result.target_label,
        "assessment_date": result.assessment_date,
        "release_status": pack["release_status"],
        "engine_source": result.engine_source,
        "source_document": result.source_document,
        "source_url": result.source_url,
        "controls": [
            {
                "code": o.code,
                "title": o.title,
                "category": o.category,
                "evaluator_key": o.evaluator_key,
                "severity_default": o.severity_default,
                "effective_from": o.effective_from,
                "active": o.active,
                "status": o.status,
                "score": round(o.score, 4),
                "reason": o.reason,
                "produces_finding": o.produces_finding,
                "finding_severity": o.finding_severity,
                "is_hard_blocker": o.is_hard_blocker,
                "risk_score": o.risk_score,
                "recommended_actions": o.recommended_actions,
                "evidence_ids": o.evidence_ids,
            }
            for o in result.controls
        ],
    }


def write_assurance(result: EvaluationResult, out_dir, *, seed: int, target_ref: str, framework: str) -> Path:
    """Build the pack and write ``<out_dir>/assurance.json`` (+ a native report).

    Returns the path to the written ``assurance.json``.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    pack = build_assurance_pack(result, seed=seed, target_ref=target_ref, framework=framework)

    native = build_native_report(result, pack)
    (out / NATIVE_REPORT_NAME).write_text(
        json.dumps(native, indent=2, sort_keys=False), encoding="utf-8"
    )

    pack_path = out / "assurance.json"
    pack_path.write_text(json.dumps(pack, indent=2, sort_keys=False), encoding="utf-8")
    return pack_path


def _engine_version() -> str:
    from . import __version__

    return __version__
