"""Regulatory library endpoints (regulations, obligations)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context
from app.controls.effective_date import regulation_status
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models.regulatory import Control, Obligation, Regulation
from app.services.assessment_service import get_assessment_date

router = APIRouter(prefix="/regulations", tags=["regulations"])


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
    rows = db.scalars(select(Regulation).order_by(Regulation.name))
    out = []
    for r in rows:
        count = db.scalar(select(func.count(Obligation.id)).where(Obligation.regulation_id == r.id)) or 0
        out.append(
            RegulationOut(
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
                obligation_count=int(count),
            )
        )
    return out


@router.get("/{regulation_id}", response_model=RegulationOut)
def get_regulation(
    regulation_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> RegulationOut:
    from sqlalchemy import func

    r = db.get(Regulation, regulation_id)
    if not r:
        raise NotFoundError("Regulation not found.")
    assessment_date = get_assessment_date(ctx.organization)
    count = db.scalar(select(func.count(Obligation.id)).where(Obligation.regulation_id == r.id)) or 0
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
        obligation_count=int(count),
    )


@router.get("/{regulation_id}/obligations", response_model=list[ObligationOut])
def get_obligations(
    regulation_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[ObligationOut]:
    from sqlalchemy import func

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
