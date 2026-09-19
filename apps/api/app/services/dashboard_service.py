"""Dashboard aggregation service. All metrics are derived from the database."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.controls.effective_date import is_control_active
from app.core.enums import Classification, ControlStatus, FindingStatus, Severity
from app.models.evidence import Evidence
from app.models.findings import Finding
from app.models.inventory import AssetField, DataAsset, DataFlow, Vendor
from app.models.regulatory import Control, ControlAssessment
from app.services.assessment_service import get_assessment_date, latest_assessment
from app.services.evidence_service import compute_freshness

_PERSONAL = {Classification.PERSONAL_DATA.value, Classification.SENSITIVE_PERSONAL_DATA.value}
_OPEN = {FindingStatus.OPEN.value, FindingStatus.ACKNOWLEDGED.value, FindingStatus.IN_PROGRESS.value}


def summary(db: Session, org) -> dict:
    org_id = org.id
    assessment_date = get_assessment_date(org)

    total_assets = db.scalar(
        select(func.count(DataAsset.id)).where(DataAsset.organization_id == org_id)
    ) or 0
    personal_assets = db.scalar(
        select(func.count(DataAsset.id)).where(
            DataAsset.organization_id == org_id, DataAsset.classification.in_(_PERSONAL)
        )
    ) or 0

    open_findings = db.scalar(
        select(func.count(Finding.id)).where(
            Finding.organization_id == org_id, Finding.status.in_(_OPEN)
        )
    ) or 0
    critical_findings = db.scalar(
        select(func.count(Finding.id)).where(
            Finding.organization_id == org_id,
            Finding.status.in_(_OPEN),
            Finding.severity == Severity.CRITICAL.value,
        )
    ) or 0

    # Control coverage: active controls with a PASS/PARTIAL assessment vs total active.
    controls = list(db.scalars(select(Control)))
    active_controls = [c for c in controls if is_control_active(c.effective_from, assessment_date)]
    upcoming_controls = [c for c in controls if not is_control_active(c.effective_from, assessment_date)]
    passing = 0
    status_counts: Counter = Counter()
    for c in active_controls:
        la = latest_assessment(db, org_id, c.id)
        st = la.status if la else ControlStatus.NO_EVIDENCE.value
        status_counts[st] += 1
        if st in {ControlStatus.PASS.value, ControlStatus.PARTIAL.value}:
            passing += 1
    control_coverage = round(passing / len(active_controls) * 100) if active_controls else 0

    # Evidence freshness.
    evidence_rows = list(db.scalars(select(Evidence).where(Evidence.organization_id == org_id)))
    fresh_counter: Counter = Counter()
    for e in evidence_rows:
        fresh_counter[compute_freshness(e.collected_at, e.expires_at, assessment_date)] += 1
    total_ev = sum(fresh_counter.values()) or 1
    evidence_stale_pct = round((fresh_counter.get("STALE", 0) + fresh_counter.get("EXPIRED", 0)) / total_ev * 100)

    unmapped_flows = db.scalar(
        select(func.count(DataFlow.id)).where(
            DataFlow.organization_id == org_id,
            DataFlow.contains_personal_data.is_(True),
            DataFlow.purpose.is_(None),
        )
    ) or 0

    vendors_pd = db.scalar(
        select(func.count(func.distinct(DataFlow.vendor_id))).where(
            DataFlow.organization_id == org_id,
            DataFlow.contains_personal_data.is_(True),
            DataFlow.vendor_id.isnot(None),
        )
    ) or 0

    return {
        "organization": org.name,
        "assessment_date": assessment_date.isoformat(),
        "data_assets": int(total_assets),
        "personal_data_assets": int(personal_assets),
        "open_findings": int(open_findings),
        "critical_findings": int(critical_findings),
        "control_coverage": control_coverage,
        "evidence_stale_pct": evidence_stale_pct,
        "unmapped_data_flows": int(unmapped_flows),
        "vendors_processing_personal_data": int(vendors_pd),
        "upcoming_obligations": len(upcoming_controls),
        "control_status_breakdown": dict(status_counts),
        "evidence_freshness": dict(fresh_counter),
    }


def data_posture(db: Session, org) -> dict:
    """Distribution of data categories across discovered personal-data fields."""
    org_id = org.id
    rows = db.execute(
        select(AssetField.category, func.count(AssetField.id))
        .join(DataAsset, DataAsset.id == AssetField.asset_id)
        .where(
            DataAsset.organization_id == org_id,
            AssetField.classification.in_(_PERSONAL),
        )
        .group_by(AssetField.category)
    ).all()
    categories = [{"category": c, "count": int(n)} for c, n in rows]

    sensitivity_rows = db.execute(
        select(DataAsset.sensitivity_level, func.count(DataAsset.id))
        .where(DataAsset.organization_id == org_id)
        .group_by(DataAsset.sensitivity_level)
    ).all()
    sensitivity = [{"level": int(lvl), "count": int(n)} for lvl, n in sensitivity_rows]
    return {"categories": categories, "sensitivity": sensitivity}


def top_findings(db: Session, org, limit: int = 5) -> list[dict]:
    rows = db.scalars(
        select(Finding)
        .where(Finding.organization_id == org.id, Finding.status.in_(_OPEN))
        .order_by(Finding.risk_score.desc())
        .limit(limit)
    )
    return [
        {
            "id": str(f.id),
            "title": f.title,
            "severity": f.severity,
            "risk_score": f.risk_score,
            "status": f.status,
        }
        for f in rows
    ]


def risk_trend(db: Session, org) -> list[dict]:
    """Findings grouped by severity for a distribution view."""
    rows = db.execute(
        select(Finding.severity, func.count(Finding.id))
        .where(Finding.organization_id == org.id, Finding.status.in_(_OPEN))
        .group_by(Finding.severity)
    ).all()
    return [{"severity": s, "count": int(n)} for s, n in rows]
