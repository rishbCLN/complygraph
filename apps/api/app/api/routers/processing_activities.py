"""Processing activity endpoints (business-to-technical bridge)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.api.query import get_org_scoped
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.rbac import MANAGE_INVENTORY
from app.models.inventory import ProcessingActivity

router = APIRouter(prefix="/processing-activities", tags=["processing-activities"])


class ActivityIn(BaseModel):
    name: str
    purpose: str | None = None
    description: str | None = None
    lawful_basis: str | None = None
    owner: str | None = None
    status: str | None = "ACTIVE"
    retention_period_days: int | None = None
    has_notice: bool | None = None
    has_consent: bool | None = None


class ActivityOut(BaseModel):
    id: str
    name: str
    purpose: str | None
    description: str | None
    lawful_basis: str | None
    owner: str | None
    status: str
    retention_period_days: int | None
    has_notice: bool
    has_consent: bool


def _out(a: ProcessingActivity) -> ActivityOut:
    return ActivityOut(
        id=str(a.id),
        name=a.name,
        purpose=a.purpose,
        description=a.description,
        lawful_basis=a.lawful_basis,
        owner=a.owner,
        status=a.status,
        retention_period_days=a.retention_period_days,
        has_notice=a.has_notice,
        has_consent=a.has_consent,
    )


@router.get("", response_model=list[ActivityOut])
def list_activities(
    ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)
) -> list[ActivityOut]:
    rows = db.scalars(
        select(ProcessingActivity)
        .where(ProcessingActivity.organization_id == ctx.organization_id)
        .order_by(ProcessingActivity.name)
    )
    return [_out(a) for a in rows]


@router.post("", response_model=ActivityOut, status_code=201)
def create_activity(
    payload: ActivityIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_INVENTORY)),
    db: Session = Depends(get_db),
) -> ActivityOut:
    activity = ProcessingActivity(
        organization_id=ctx.organization_id, **payload.model_dump(exclude_none=True)
    )
    db.add(activity)
    db.flush()
    record_audit(
        db,
        action="processing_activity.created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="processing_activity",
        entity_id=activity.id,
    )
    db.commit()
    return _out(activity)


@router.patch("/{activity_id}", response_model=ActivityOut)
def update_activity(
    activity_id: uuid.UUID,
    payload: ActivityIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_INVENTORY)),
    db: Session = Depends(get_db),
) -> ActivityOut:
    activity = get_org_scoped(db, ProcessingActivity, activity_id, ctx.organization_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(activity, key, value)
    db.commit()
    return _out(activity)


@router.delete("/{activity_id}", status_code=204, response_model=None)
def delete_activity(
    activity_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_INVENTORY)),
    db: Session = Depends(get_db),
) -> None:
    activity = get_org_scoped(db, ProcessingActivity, activity_id, ctx.organization_id)
    db.delete(activity)
    record_audit(
        db,
        action="processing_activity.deleted",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="processing_activity",
        entity_id=activity_id,
    )
    db.commit()
