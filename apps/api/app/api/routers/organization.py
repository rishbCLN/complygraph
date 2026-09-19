"""Organization + settings endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.rbac import MANAGE_ORG

router = APIRouter(prefix="/organization", tags=["organization"])


class OrganizationOut(BaseModel):
    id: str
    name: str
    slug: str
    industry: str | None
    country: str
    plan: str
    assessment_date: datetime | None


class OrganizationUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    country: str | None = None
    plan: str | None = None
    assessment_date: datetime | None = None


def _to_out(org) -> OrganizationOut:
    return OrganizationOut(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        industry=org.industry,
        country=org.country,
        plan=org.plan,
        assessment_date=org.assessment_date,
    )


@router.get("", response_model=OrganizationOut)
def get_organization(ctx: AuthContext = Depends(get_current_context)) -> OrganizationOut:
    return _to_out(ctx.organization)


@router.patch("", response_model=OrganizationOut)
def update_organization(
    payload: OrganizationUpdate,
    ctx: AuthContext = Depends(require_capability(MANAGE_ORG)),
    db: Session = Depends(get_db),
) -> OrganizationOut:
    """Update org settings, including the assessment date used by the effective-date engine."""
    org = ctx.organization
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(org, key, value)
    db.add(org)
    record_audit(
        db,
        action="organization.updated",
        organization_id=org.id,
        user_id=ctx.user.id,
        entity_type="organization",
        entity_id=org.id,
        metadata={"fields": list(data.keys())},
    )
    db.commit()
    db.refresh(org)
    return _to_out(org)
