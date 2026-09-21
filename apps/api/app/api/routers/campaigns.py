"""Audit campaign endpoints (feature #5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.rbac import ASSESS_CONTROLS
from app.models.campaign import AuditCampaign, CampaignResult
from app.services import campaign_service

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignIn(BaseModel):
    name: str
    description: str | None = None
    scope_regulation_ids: list[str] | None = None


class CampaignOut(BaseModel):
    id: str
    name: str
    description: str | None
    scope_regulation_ids: list[str] | None
    status: str
    assessment_date: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    summary: dict | None
    created_at: datetime | None


class ResultOut(BaseModel):
    id: str
    control_id: str | None
    control_code: str
    control_title: str | None
    regulation_name: str | None
    category: str | None
    status: str
    score: float
    reason: str | None


def _out(c: AuditCampaign) -> CampaignOut:
    return CampaignOut(
        id=str(c.id),
        name=c.name,
        description=c.description,
        scope_regulation_ids=c.scope_regulation_ids,
        status=c.status,
        assessment_date=c.assessment_date,
        started_at=c.started_at,
        completed_at=c.completed_at,
        summary=c.summary,
        created_at=c.created_at,
    )


def _result_out(r: CampaignResult) -> ResultOut:
    return ResultOut(
        id=str(r.id),
        control_id=str(r.control_id) if r.control_id else None,
        control_code=r.control_code,
        control_title=r.control_title,
        regulation_name=r.regulation_name,
        category=r.category,
        status=r.status,
        score=r.score,
        reason=r.reason,
    )


@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    status: str | None = Query(None),
) -> list[CampaignOut]:
    return [_out(c) for c in campaign_service.list_campaigns(db, ctx.organization_id, status=status)]


@router.post("", response_model=CampaignOut, status_code=201)
def create_campaign(
    payload: CampaignIn,
    ctx: AuthContext = Depends(require_capability(ASSESS_CONTROLS)),
    db: Session = Depends(get_db),
) -> CampaignOut:
    campaign = campaign_service.create_campaign(
        db,
        ctx.organization_id,
        ctx.user.id,
        name=payload.name,
        description=payload.description,
        scope_regulation_ids=payload.scope_regulation_ids,
    )
    record_audit(
        db,
        action="campaign.created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="audit_campaign",
        entity_id=campaign.id,
    )
    db.commit()
    db.refresh(campaign)
    return _out(campaign)


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(
    campaign_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> CampaignOut:
    return _out(campaign_service.get_campaign(db, ctx.organization_id, campaign_id))


@router.get("/{campaign_id}/results", response_model=list[ResultOut])
def get_results(
    campaign_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    status: str | None = Query(None),
) -> list[ResultOut]:
    campaign_service.get_campaign(db, ctx.organization_id, campaign_id)  # scope check
    return [_result_out(r) for r in campaign_service.list_results(db, campaign_id, status=status)]


@router.post("/{campaign_id}/run", response_model=CampaignOut)
def run_campaign(
    campaign_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(ASSESS_CONTROLS)),
    db: Session = Depends(get_db),
) -> CampaignOut:
    campaign = campaign_service.get_campaign(db, ctx.organization_id, campaign_id)
    campaign = campaign_service.run_campaign(db, ctx.organization, campaign)
    record_audit(
        db,
        action="campaign.completed",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="audit_campaign",
        entity_id=campaign.id,
        metadata={"coverage": (campaign.summary or {}).get("coverage")},
    )
    db.commit()
    db.refresh(campaign)
    return _out(campaign)


@router.get("/{campaign_id}/compare/{baseline_id}")
def compare_campaigns(
    campaign_id: uuid.UUID,
    baseline_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    return campaign_service.compare(db, ctx.organization_id, campaign_id, baseline_id)


@router.post("/{campaign_id}/archive", response_model=CampaignOut)
def archive_campaign(
    campaign_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(ASSESS_CONTROLS)),
    db: Session = Depends(get_db),
) -> CampaignOut:
    campaign = campaign_service.archive_campaign(db, ctx.organization_id, campaign_id)
    db.commit()
    db.refresh(campaign)
    return _out(campaign)


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(
    campaign_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(ASSESS_CONTROLS)),
    db: Session = Depends(get_db),
) -> None:
    campaign_service.delete_campaign(db, ctx.organization_id, campaign_id)
    record_audit(
        db,
        action="campaign.deleted",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="audit_campaign",
        entity_id=campaign_id,
    )
    db.commit()
