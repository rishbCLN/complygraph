"""Findings service: creation with deduplication, risk scoring, and workflow."""

from __future__ import annotations

import hashlib
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.controls.risk import RiskInputs, compute_risk
from app.core.audit import record_audit
from app.core.database import utcnow
from app.core.enums import FindingStatus
from app.models.findings import Finding


def finding_fingerprint(
    control_id: uuid.UUID | None,
    asset_id: uuid.UUID | None,
    finding_type: str,
) -> str:
    raw = f"{control_id}|{asset_id}|{finding_type}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def upsert_finding(
    db: Session,
    *,
    organization_id: uuid.UUID,
    finding_type: str,
    title: str,
    description: str,
    risk_inputs: RiskInputs,
    control_id: uuid.UUID | None = None,
    asset_id: uuid.UUID | None = None,
    data_flow_id: uuid.UUID | None = None,
    vendor_id: uuid.UUID | None = None,
    data_categories: str | None = None,
    recommended_actions: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    source: str = "control_engine",
    owner: str | None = None,
    due_in_days: int = 30,
) -> Finding:
    """Create or update a finding using a deterministic fingerprint for dedup."""
    fingerprint = finding_fingerprint(control_id, asset_id, finding_type)
    risk = compute_risk(risk_inputs)

    existing = db.scalar(
        select(Finding).where(
            Finding.organization_id == organization_id,
            Finding.fingerprint == fingerprint,
        )
    )
    if existing:
        # Update mutable fields but preserve human workflow state / assignment.
        existing.title = title
        existing.description = description
        existing.severity = risk.severity
        existing.risk_score = risk.score
        existing.risk_breakdown = risk.breakdown
        existing.data_categories = data_categories
        existing.recommended_actions = recommended_actions or existing.recommended_actions
        existing.evidence_refs = evidence_refs or existing.evidence_refs
        existing.control_id = control_id or existing.control_id
        existing.asset_id = asset_id or existing.asset_id
        existing.data_flow_id = data_flow_id or existing.data_flow_id
        existing.vendor_id = vendor_id or existing.vendor_id
        if existing.status in {FindingStatus.RESOLVED.value, FindingStatus.FALSE_POSITIVE.value}:
            # Problem re-detected after resolution -> reopen.
            existing.status = FindingStatus.OPEN.value
            existing.resolved_at = None
            existing.resolved_by = None
        return existing

    finding = Finding(
        organization_id=organization_id,
        control_id=control_id,
        asset_id=asset_id,
        data_flow_id=data_flow_id,
        vendor_id=vendor_id,
        title=title,
        description=description,
        severity=risk.severity,
        risk_score=risk.score,
        risk_breakdown=risk.breakdown,
        status=FindingStatus.OPEN.value,
        source=source,
        fingerprint=fingerprint,
        data_categories=data_categories,
        recommended_actions=recommended_actions,
        evidence_refs=evidence_refs,
        owner=owner,
        detected_at=utcnow(),
        due_at=utcnow() + timedelta(days=due_in_days),
    )
    db.add(finding)
    return finding


# --- Workflow transitions -------------------------------------------------------

_TERMINAL = {FindingStatus.RESOLVED.value, FindingStatus.ACCEPTED_RISK.value, FindingStatus.FALSE_POSITIVE.value}


def transition_finding(
    db: Session,
    finding: Finding,
    *,
    new_status: str,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    note: str | None = None,
) -> Finding:
    from app.core.errors import ValidationError

    if new_status in {FindingStatus.ACCEPTED_RISK.value, FindingStatus.FALSE_POSITIVE.value} and not note:
        raise ValidationError(f"A justification note is required to set status {new_status}.")

    finding.status = new_status
    if note:
        finding.resolution_note = note
    if new_status == FindingStatus.RESOLVED.value:
        finding.resolved_at = utcnow()
        finding.resolved_by = user_id
    record_audit(
        db,
        action="finding.status_changed",
        organization_id=organization_id,
        user_id=user_id,
        entity_type="finding",
        entity_id=finding.id,
        metadata={"new_status": new_status},
    )
    return finding
