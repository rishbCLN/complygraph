"""Audit campaign service (feature #5).

A campaign runs the deterministic control engine over a scoped set of frameworks
and freezes each control's outcome as a CampaignResult. Completed campaigns are
immutable so they can be compared period-over-period.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.controls.effective_date import is_control_active
from app.controls.engine import ControlEvaluation, evaluate
from app.core.database import utcnow
from app.core.enums import ControlStatus
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.campaign import AuditCampaign, CampaignResult
from app.models.identity import Organization
from app.models.regulatory import Control, Obligation, Regulation
from app.services import assessment_service

DRAFT = "DRAFT"
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
ARCHIVED = "ARCHIVED"

# Statuses that count toward "applicable" (i.e. in force and relevant).
_NON_APPLICABLE = {ControlStatus.NOT_APPLICABLE.value, ControlStatus.UPCOMING.value}


def create_campaign(
    db: Session,
    org_id: uuid.UUID,
    user_id: uuid.UUID | None,
    *,
    name: str,
    description: str | None,
    scope_regulation_ids: list[str] | None,
) -> AuditCampaign:
    if not (name or "").strip():
        raise ValidationError("A campaign requires a name.")
    # Validate the scoped frameworks exist and are visible to the org.
    if scope_regulation_ids:
        valid = _visible_regulation_ids(db, org_id)
        for rid in scope_regulation_ids:
            if rid not in valid:
                raise ValidationError(f"Framework {rid} is not available to this organization.")
    campaign = AuditCampaign(
        organization_id=org_id,
        name=name.strip(),
        description=description,
        scope_regulation_ids=scope_regulation_ids or None,
        status=DRAFT,
        created_by=user_id,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(campaign)
    db.flush()
    return campaign


def _visible_regulation_ids(db: Session, org_id: uuid.UUID) -> set[str]:
    rows = db.scalars(
        select(Regulation.id).where(
            (Regulation.organization_id == org_id) | (Regulation.organization_id.is_(None))
        )
    )
    return {str(r) for r in rows}


def get_campaign(db: Session, org_id: uuid.UUID, campaign_id: uuid.UUID) -> AuditCampaign:
    campaign = db.get(AuditCampaign, campaign_id)
    if campaign is None or campaign.organization_id != org_id:
        raise NotFoundError("Campaign not found.")
    return campaign


def list_campaigns(db: Session, org_id: uuid.UUID, *, status: str | None = None) -> list[AuditCampaign]:
    stmt = select(AuditCampaign).where(AuditCampaign.organization_id == org_id)
    if status:
        stmt = stmt.where(AuditCampaign.status == status)
    return list(db.scalars(stmt.order_by(AuditCampaign.created_at.desc())))


def list_results(
    db: Session, campaign_id: uuid.UUID, *, status: str | None = None
) -> list[CampaignResult]:
    stmt = select(CampaignResult).where(CampaignResult.campaign_id == campaign_id)
    if status:
        stmt = stmt.where(CampaignResult.status == status)
    return list(db.scalars(stmt.order_by(CampaignResult.control_code)))


def _scoped_controls(db: Session, org_id: uuid.UUID, scope: list[str] | None) -> list[tuple[Control, str]]:
    """Return (control, regulation_name) pairs in scope for this org.

    Controls come from shipped regulations (organization_id NULL) plus this org's
    custom frameworks. If ``scope`` is set, only controls under those regulations
    are included.
    """
    stmt = (
        select(Control, Regulation.name, Regulation.id)
        .join(Obligation, Obligation.id == Control.obligation_id)
        .join(Regulation, Regulation.id == Obligation.regulation_id)
        .where(
            (Regulation.organization_id == org_id) | (Regulation.organization_id.is_(None))
        )
    )
    pairs: list[tuple[Control, str]] = []
    scope_set = set(scope) if scope else None
    for control, reg_name, reg_id in db.execute(stmt).all():
        if scope_set is not None and str(reg_id) not in scope_set:
            continue
        pairs.append((control, reg_name))
    return pairs


def run_campaign(db: Session, org: Organization, campaign: AuditCampaign) -> AuditCampaign:
    if campaign.status == COMPLETED:
        raise ConflictError("This campaign has already completed and is immutable.")
    if campaign.status == ARCHIVED:
        raise ConflictError("This campaign is archived.")

    campaign.status = RUNNING
    campaign.started_at = utcnow()
    db.flush()

    ctx = assessment_service.build_context(db, org)
    controls = _scoped_controls(db, org.id, campaign.scope_regulation_ids)

    by_status: dict[str, int] = {}
    applicable = 0
    passing = 0
    now = utcnow()

    for control, reg_name in controls:
        if not is_control_active(control.effective_from, ctx.assessment_date):
            evaluation = ControlEvaluation(
                status=ControlStatus.UPCOMING.value,
                score=0.0,
                reason="Not yet in force at the assessment date; shown for preparation.",
            )
        else:
            evaluation = evaluate(control.evaluator_key, ctx, control.code, control.applies_to)

        db.add(
            CampaignResult(
                campaign_id=campaign.id,
                control_id=control.id,
                control_code=control.code,
                control_title=control.title,
                regulation_name=reg_name,
                category=control.category,
                status=evaluation.status,
                score=evaluation.score,
                reason=evaluation.reason,
                created_at=now,
            )
        )
        by_status[evaluation.status] = by_status.get(evaluation.status, 0) + 1
        if evaluation.status not in _NON_APPLICABLE:
            applicable += 1
            if evaluation.status == ControlStatus.PASS.value:
                passing += 1

    coverage = round((passing / applicable) * 100, 1) if applicable else 0.0
    campaign.summary = {
        "total": len(controls),
        "applicable": applicable,
        "passing": passing,
        "by_status": by_status,
        "coverage": coverage,
    }
    campaign.assessment_date = ctx.assessment_date
    campaign.status = COMPLETED
    campaign.completed_at = utcnow()
    campaign.updated_at = utcnow()
    db.flush()
    return campaign


def archive_campaign(db: Session, org_id: uuid.UUID, campaign_id: uuid.UUID) -> AuditCampaign:
    campaign = get_campaign(db, org_id, campaign_id)
    campaign.status = ARCHIVED
    campaign.updated_at = utcnow()
    db.flush()
    return campaign


def delete_campaign(db: Session, org_id: uuid.UUID, campaign_id: uuid.UUID) -> None:
    campaign = get_campaign(db, org_id, campaign_id)
    db.delete(campaign)
    db.flush()


def compare(
    db: Session, org_id: uuid.UUID, campaign_id: uuid.UUID, baseline_id: uuid.UUID
) -> dict:
    """Diff a completed campaign against an earlier completed baseline.

    Classifies each control as regressed (posture worsened), improved, added or
    removed, using the same status ranking as the AI-system change-impact report.
    """
    current = get_campaign(db, org_id, campaign_id)
    baseline = get_campaign(db, org_id, baseline_id)
    if current.status != COMPLETED or baseline.status != COMPLETED:
        raise ValidationError("Both campaigns must be completed to compare them.")

    cur = {r.control_code: r.status for r in list_results(db, current.id)}
    base = {r.control_code: r.status for r in list_results(db, baseline.id)}
    order = assessment_service._STATUS_ORDER

    regressed, improved, added = [], [], []
    for code, status in cur.items():
        if code not in base:
            added.append({"code": code, "status": status})
            continue
        if status == base[code]:
            continue
        transition = {"code": code, "from": base[code], "to": status}
        if order.get(status, 9) < order.get(base[code], 9):
            regressed.append(transition)
        else:
            improved.append(transition)
    removed = [{"code": code, "status": base[code]} for code in base if code not in cur]

    return {
        "campaign_id": str(current.id),
        "baseline_id": str(baseline.id),
        "regressed": regressed,
        "improved": improved,
        "added": added,
        "removed": removed,
    }
