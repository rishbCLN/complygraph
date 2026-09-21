"""Regulatory library endpoints (regulations, obligations)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.controls.effective_date import regulation_status
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.core.rbac import MANAGE_REGULATORY
from app.models.regulatory import Control, Obligation, Regulation
from app.services import pack_service
from app.services.assessment_service import get_assessment_date

router = APIRouter(prefix="/regulations", tags=["regulations"])


def _visible_regulations_filter(org_id):
    """System regulations (NULL org) plus the caller org's own custom packs."""
    return or_(
        Regulation.organization_id.is_(None),
        Regulation.organization_id == org_id,
    )


class RegulationOut(BaseModel):
    id: str
    name: str
    jurisdiction: str
    version: str | None
    source_document: str | None
    source_url: str | None
    pack: str | None
    pack_version: str | None
    legal_status: str
    effective_from: datetime | None
    status: str
    enabled: bool
    obligation_count: int
    is_custom: bool


class ObligationOut(BaseModel):
    id: str
    code: str
    title: str
    description: str | None
    legal_reference: str | None
    source_section: str | None
    source_url: str | None
    legal_status: str
    citation_status: str
    effective_from: datetime | None
    control_count: int


@router.get("", response_model=list[RegulationOut])
def list_regulations(
    ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)
) -> list[RegulationOut]:
    from sqlalchemy import func

    assessment_date = get_assessment_date(ctx.organization)
    rows = db.scalars(
        select(Regulation)
        .where(_visible_regulations_filter(ctx.organization_id))
        .order_by(Regulation.name)
    )
    out = []
    for r in rows:
        count = db.scalar(select(func.count(Obligation.id)).where(Obligation.regulation_id == r.id)) or 0
        out.append(_regulation_out(r, int(count), assessment_date))
    return out


def _regulation_out(r: Regulation, obligation_count: int, assessment_date) -> RegulationOut:
    return RegulationOut(
        id=str(r.id),
        name=r.name,
        jurisdiction=r.jurisdiction,
        version=r.version,
        source_document=r.source_document,
        source_url=r.source_url,
        pack=r.pack,
        pack_version=r.pack_version,
        legal_status=r.legal_status,
        effective_from=r.effective_from,
        status=regulation_status(r.effective_from, assessment_date),
        enabled=r.enabled,
        obligation_count=obligation_count,
        is_custom=r.organization_id is not None,
    )


# --- Custom pack authoring (declared before /{regulation_id} to avoid clash) ----


class PackImportIn(BaseModel):
    format: str = "yaml"  # "yaml" | "json"
    content: str


class PackControlIn(BaseModel):
    code: str
    title: str
    description: str | None = None
    category: str = "GENERAL"
    evaluator_key: str | None = None
    severity: str = "MEDIUM"
    applies_to: dict | None = None


class PackObligationIn(BaseModel):
    code: str
    title: str
    description: str | None = None
    legal_reference: str | None = None
    source_section: str | None = None
    source_url: str | None = None
    legal_status: str | None = None
    citation_status: str = "UNVERIFIED"
    controls: list[PackControlIn] = []


class PackMetaIn(BaseModel):
    name: str
    jurisdiction: str = "Internal"
    version: str | None = None
    legal_status: str = "INTERNAL_POLICY"
    source_document: str | None = None
    source_url: str | None = None
    status: str = "IN_FORCE"


class PackCreateIn(BaseModel):
    pack: PackMetaIn
    obligations: list[PackObligationIn] = []


@router.get("/packs", response_model=list[RegulationOut])
def list_packs(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[RegulationOut]:
    """Only this organization's own custom packs."""
    from sqlalchemy import func

    assessment_date = get_assessment_date(ctx.organization)
    out = []
    for r in pack_service.list_custom_packs(db, ctx.organization_id):
        count = db.scalar(select(func.count(Obligation.id)).where(Obligation.regulation_id == r.id)) or 0
        out.append(_regulation_out(r, int(count), assessment_date))
    return out


def _persist_pack_result(db, ctx, regulation) -> RegulationOut:
    from sqlalchemy import func

    record_audit(
        db,
        action="regulatory_pack.created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="regulation",
        entity_id=regulation.id,
        metadata={"name": regulation.name},
    )
    db.commit()
    db.refresh(regulation)
    assessment_date = get_assessment_date(ctx.organization)
    count = db.scalar(select(func.count(Obligation.id)).where(Obligation.regulation_id == regulation.id)) or 0
    return _regulation_out(regulation, int(count), assessment_date)


@router.post("/packs/import", response_model=RegulationOut, status_code=201)
def import_pack(
    payload: PackImportIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_REGULATORY)),
    db: Session = Depends(get_db),
) -> RegulationOut:
    regulation = pack_service.import_pack(
        db, ctx.organization_id, ctx.user.id, payload.content, payload.format
    )
    return _persist_pack_result(db, ctx, regulation)


@router.post("/packs", response_model=RegulationOut, status_code=201)
def create_pack(
    payload: PackCreateIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_REGULATORY)),
    db: Session = Depends(get_db),
) -> RegulationOut:
    regulation = pack_service.create_pack(
        db, ctx.organization_id, ctx.user.id, payload.model_dump()
    )
    return _persist_pack_result(db, ctx, regulation)


@router.delete("/packs/{regulation_id}", status_code=204)
def delete_pack(
    regulation_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_REGULATORY)),
    db: Session = Depends(get_db),
) -> None:
    pack_service.delete_custom_pack(db, ctx.organization_id, regulation_id)
    record_audit(
        db,
        action="regulatory_pack.deleted",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="regulation",
        entity_id=regulation_id,
    )
    db.commit()


@router.get("/{regulation_id}", response_model=RegulationOut)
def get_regulation(
    regulation_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> RegulationOut:
    from sqlalchemy import func

    r = db.get(Regulation, regulation_id)
    if not r or (r.organization_id is not None and r.organization_id != ctx.organization_id):
        raise NotFoundError("Regulation not found.")
    assessment_date = get_assessment_date(ctx.organization)
    count = db.scalar(select(func.count(Obligation.id)).where(Obligation.regulation_id == r.id)) or 0
    return _regulation_out(r, int(count), assessment_date)


@router.get("/{regulation_id}/obligations", response_model=list[ObligationOut])
def get_obligations(
    regulation_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[ObligationOut]:
    from sqlalchemy import func

    reg = db.get(Regulation, regulation_id)
    if not reg or (reg.organization_id is not None and reg.organization_id != ctx.organization_id):
        raise NotFoundError("Regulation not found.")
    rows = db.scalars(
        select(Obligation).where(Obligation.regulation_id == regulation_id).order_by(Obligation.code)
    )
    out = []
    for o in rows:
        count = db.scalar(select(func.count(Control.id)).where(Control.obligation_id == o.id)) or 0
        out.append(
            ObligationOut(
                id=str(o.id),
                code=o.code,
                title=o.title,
                description=o.description,
                legal_reference=o.legal_reference,
                source_section=o.source_section,
                source_url=o.source_url,
                legal_status=o.legal_status,
                citation_status=o.citation_status,
                effective_from=o.effective_from,
                control_count=int(count),
            )
        )
    return out
