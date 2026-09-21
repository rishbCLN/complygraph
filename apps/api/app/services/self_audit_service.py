"""Self-audit / data-quality engine.

Distinct from control *assessment* (which asks "is the control satisfied?"), the
self-audit asks "is our compliance data complete and trustworthy enough to rely
on?". It inspects the inventory for the gaps that quietly undermine every
downstream conclusion — assets with no owner, processing activities with no
retention period, vendors handling personal data with no contract, in-force
controls with no evidence, expired evidence, production AI systems with no
documented review, and overdue findings.

Every check is deterministic and read-only. Results are advisory: they measure
data hygiene, not legal compliance.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.controls.effective_date import control_temporal_status
from app.core.enums import EvidenceStatus
from app.models.ai_systems import AISystem
from app.models.evidence import ControlEvidence, Evidence
from app.models.findings import Finding
from app.models.identity import Organization
from app.models.inventory import DataAsset, DataFlow, ProcessingActivity, Vendor
from app.models.regulatory import Control, Obligation, Regulation
from app.services.assessment_service import get_assessment_date
from app.services.evidence_service import compute_freshness

_ITEM_CAP = 25
_PERSONAL = {"PERSONAL_DATA", "SENSITIVE_PERSONAL_DATA"}
_MISSING_CONTRACT = {"MISSING", "UNKNOWN", "NONE", ""}


@dataclass
class QualityItem:
    type: str
    id: str
    label: str
    detail: str


@dataclass
class QualityCheck:
    key: str
    title: str
    category: str
    weight: int
    severity: str
    recommendation: str
    total: int = 0
    incomplete_items: list[QualityItem] = field(default_factory=list)

    @property
    def incomplete(self) -> int:
        return len(self.incomplete_items)

    @property
    def complete(self) -> int:
        return max(0, self.total - self.incomplete)

    @property
    def score(self) -> int:
        # A check with nothing to measure is fully complete (100), never a false gap.
        if self.total == 0:
            return 100
        return round(self.complete / self.total * 100)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "title": self.title,
            "category": self.category,
            "severity": self.severity,
            "recommendation": self.recommendation,
            "total": self.total,
            "complete": self.complete,
            "incomplete": self.incomplete,
            "score": self.score,
            "items": [
                {"type": i.type, "id": i.id, "label": i.label, "detail": i.detail}
                for i in self.incomplete_items[:_ITEM_CAP]
            ],
            "items_truncated": self.incomplete > _ITEM_CAP,
        }


def _visible_controls(db: Session, org_id: uuid.UUID):
    return db.scalars(
        select(Control)
        .join(Obligation, Obligation.id == Control.obligation_id)
        .join(Regulation, Regulation.id == Obligation.regulation_id)
        .where(
            or_(
                Regulation.organization_id.is_(None),
                Regulation.organization_id == org_id,
            )
        )
    ).all()


def run_self_audit(db: Session, org: Organization) -> dict:
    org_id = org.id
    assessment_date = get_assessment_date(org)
    checks: list[QualityCheck] = []

    # 1) Assets missing an owner.
    assets = db.scalars(select(DataAsset).where(DataAsset.organization_id == org_id)).all()
    c = QualityCheck(
        key="asset_ownership",
        title="Data assets have an assigned owner",
        category="INVENTORY",
        weight=2,
        severity="MEDIUM",
        recommendation="Assign an accountable owner to each data asset.",
        total=len(assets),
    )
    for a in assets:
        if not (a.owner or "").strip():
            c.incomplete_items.append(
                QualityItem("asset", str(a.id), a.display_name or a.name, "No owner set")
            )
    checks.append(c)

    # 2) Personal-data fields still needing classification review.
    personal_assets = [a for a in assets if a.classification in _PERSONAL]
    c = QualityCheck(
        key="classification_review",
        title="Personal-data assets have reviewed classifications",
        category="INVENTORY",
        weight=2,
        severity="MEDIUM",
        recommendation="Review low-confidence field classifications flagged needs_review.",
        total=len(personal_assets),
    )
    if personal_assets:
        from app.models.inventory import AssetField

        for a in personal_assets:
            needs = db.scalar(
                select(AssetField.id)
                .where(AssetField.asset_id == a.id, AssetField.needs_review.is_(True))
                .limit(1)
            )
            if needs is not None:
                c.incomplete_items.append(
                    QualityItem("asset", str(a.id), a.display_name or a.name, "Has fields needing review")
                )
    checks.append(c)

    # 3) Processing activities missing a retention period.
    activities = db.scalars(
        select(ProcessingActivity).where(ProcessingActivity.organization_id == org_id)
    ).all()
    c = QualityCheck(
        key="retention_defined",
        title="Processing activities define a retention period",
        category="GOVERNANCE",
        weight=3,
        severity="HIGH",
        recommendation="Define a retention period for every processing activity.",
        total=len(activities),
    )
    for act in activities:
        if act.retention_period_days is None:
            c.incomplete_items.append(
                QualityItem("processing_activity", str(act.id), act.name, "No retention period")
            )
    checks.append(c)

    # 4) Processing activities missing a lawful basis.
    c = QualityCheck(
        key="lawful_basis_declared",
        title="Processing activities declare a lawful basis",
        category="GOVERNANCE",
        weight=2,
        severity="MEDIUM",
        recommendation="Record the declared lawful basis (subject to legal review).",
        total=len(activities),
    )
    for act in activities:
        if not (act.lawful_basis or "").strip():
            c.incomplete_items.append(
                QualityItem("processing_activity", str(act.id), act.name, "No lawful basis")
            )
    checks.append(c)

    # 5) Vendors processing personal data without a contract.
    vendors = db.scalars(select(Vendor).where(Vendor.organization_id == org_id)).all()
    vendor_with_pd_flow = {
        v_id
        for (v_id,) in db.execute(
            select(DataFlow.vendor_id).where(
                DataFlow.organization_id == org_id,
                DataFlow.vendor_id.isnot(None),
                DataFlow.contains_personal_data.is_(True),
            )
        ).all()
    }
    relevant_vendors = [
        v for v in vendors if v.id in vendor_with_pd_flow or (v.data_processing or "").strip()
    ]
    c = QualityCheck(
        key="vendor_contracts",
        title="Personal-data vendors have a recorded contract",
        category="VENDOR",
        weight=3,
        severity="HIGH",
        recommendation="Record a data processing agreement for every vendor handling personal data.",
        total=len(relevant_vendors),
    )
    for v in relevant_vendors:
        if (v.contract_status or "").upper() in _MISSING_CONTRACT:
            c.incomplete_items.append(
                QualityItem("vendor", str(v.id), v.name, f"Contract status: {v.contract_status}")
            )
    checks.append(c)

    # 6) Data flows missing a documented purpose.
    flows = db.scalars(select(DataFlow).where(DataFlow.organization_id == org_id)).all()
    c = QualityCheck(
        key="flow_purpose",
        title="Data flows document a purpose",
        category="INVENTORY",
        weight=1,
        severity="LOW",
        recommendation="Document the purpose of each data flow.",
        total=len(flows),
    )
    for fl in flows:
        if not (fl.purpose or "").strip():
            c.incomplete_items.append(
                QualityItem("data_flow", str(fl.id), fl.categories or "flow", "No purpose recorded")
            )
    checks.append(c)

    # 7) In-force controls with no linked evidence.
    controls = _visible_controls(db, org_id)
    in_force = [
        ctrl
        for ctrl in controls
        if control_temporal_status(ctrl.effective_from, assessment_date) != "upcoming"
    ]
    c = QualityCheck(
        key="control_evidence_coverage",
        title="In-force controls have linked evidence",
        category="EVIDENCE",
        weight=3,
        severity="HIGH",
        recommendation="Attach evidence to controls that currently have none.",
        total=len(in_force),
    )
    for ctrl in in_force:
        has_ev = db.scalar(
            select(ControlEvidence.id).where(ControlEvidence.control_id == ctrl.id).limit(1)
        )
        if has_ev is None:
            c.incomplete_items.append(
                QualityItem("control", str(ctrl.id), ctrl.code, "No evidence linked")
            )
    checks.append(c)

    # 8) Evidence freshness (expired items).
    evidence = db.scalars(select(Evidence).where(Evidence.organization_id == org_id)).all()
    c = QualityCheck(
        key="evidence_freshness",
        title="Evidence is not expired",
        category="EVIDENCE",
        weight=2,
        severity="MEDIUM",
        recommendation="Refresh or replace expired evidence artifacts.",
        total=len(evidence),
    )
    for ev in evidence:
        if compute_freshness(ev.collected_at, ev.expires_at) == EvidenceStatus.EXPIRED.value:
            c.incomplete_items.append(
                QualityItem("evidence", str(ev.id), ev.name, "Expired")
            )
    checks.append(c)

    # 9) Production AI systems without a documented review.
    systems = db.scalars(select(AISystem).where(AISystem.organization_id == org_id)).all()
    prod = [s for s in systems if s.lifecycle_stage == "PRODUCTION"]
    c = QualityCheck(
        key="ai_system_review",
        title="Production AI systems are reviewed",
        category="GOVERNANCE",
        weight=2,
        severity="MEDIUM",
        recommendation="Complete a documented review for production AI systems.",
        total=len(prod),
    )
    for s in prod:
        if s.review_status != "REVIEWED":
            c.incomplete_items.append(
                QualityItem("ai_system", str(s.id), s.name, f"Review status: {s.review_status}")
            )
    checks.append(c)

    # 10) Overdue open findings.
    open_findings = db.scalars(
        select(Finding).where(
            Finding.organization_id == org_id,
            Finding.status.in_(["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"]),
        )
    ).all()
    c = QualityCheck(
        key="findings_on_time",
        title="Open findings are within their due date",
        category="REMEDIATION",
        weight=2,
        severity="MEDIUM",
        recommendation="Address or re-plan findings past their due date.",
        total=len(open_findings),
    )
    for f in open_findings:
        if f.due_at is not None:
            due = f.due_at if f.due_at.tzinfo else f.due_at.replace(tzinfo=assessment_date.tzinfo)
            if due < assessment_date:
                c.incomplete_items.append(
                    QualityItem("finding", str(f.id), f.title, "Past due date")
                )
    checks.append(c)

    # Weighted overall score. Checks with nothing to measure (total==0) score 100
    # and still contribute, which is correct: an org with no vendors is not
    # penalised on vendor contracts.
    total_weight = sum(ck.weight for ck in checks) or 1
    overall = round(sum(ck.score * ck.weight for ck in checks) / total_weight)

    total_gaps = sum(ck.incomplete for ck in checks)
    return {
        "organization": org.name,
        "assessment_date": assessment_date.isoformat(),
        "overall_score": overall,
        "total_gaps": total_gaps,
        "check_count": len(checks),
        "checks": [ck.to_dict() for ck in checks],
    }
