"""Classifier feedback: analyst-managed classification overrides.

Analysts confirm or correct the automatic PII classifier. Overrides are keyed by
field name (optionally scoped to an asset) and are re-applied on every scan, so
corrections persist and steadily improve inventory accuracy.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.api.query import get_org_scoped
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.enums import Classification, DataCategory
from app.core.errors import ValidationError
from app.core.rbac import MANAGE_INVENTORY
from app.models.inventory import ClassificationOverride

router = APIRouter(tags=["classification-overrides"])

_VALID_CLASSIFICATIONS = {c.value for c in Classification}
_VALID_CATEGORIES = {c.value for c in DataCategory}


class OverrideCreate(BaseModel):
    field_name: str = Field(min_length=1, max_length=255)
    classification: str
    category: str = DataCategory.UNKNOWN.value
    asset_name: str | None = None  # None = applies org-wide
    note: str | None = None


class OverrideOut(BaseModel):
    id: str
    field_name: str
    asset_name: str | None
    classification: str
    category: str
    note: str | None
    created_at: datetime


def _to_out(o: ClassificationOverride) -> OverrideOut:
    return OverrideOut(
        id=str(o.id),
        field_name=o.field_name,
        asset_name=o.asset_name,
        classification=o.classification,
        category=o.category,
        note=o.note,
        created_at=o.created_at,
    )


@router.get("/classification-overrides", response_model=list[OverrideOut])
def list_overrides(
    ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)
) -> list[OverrideOut]:
    rows = db.scalars(
        select(ClassificationOverride)
        .where(ClassificationOverride.organization_id == ctx.organization_id)
        .order_by(ClassificationOverride.created_at.desc())
    )
    return [_to_out(o) for o in rows]


@router.post("/classification-overrides", response_model=OverrideOut, status_code=201)
def create_override(
    payload: OverrideCreate,
    ctx: AuthContext = Depends(require_capability(MANAGE_INVENTORY)),
    db: Session = Depends(get_db),
) -> OverrideOut:
    if payload.classification not in _VALID_CLASSIFICATIONS:
        raise ValidationError(f"Unknown classification: {payload.classification}")
    if payload.category not in _VALID_CATEGORIES:
        raise ValidationError(f"Unknown data category: {payload.category}")

    # Upsert on (org, field_name, asset_name) so re-submitting updates in place.
    existing = db.scalar(
        select(ClassificationOverride).where(
            ClassificationOverride.organization_id == ctx.organization_id,
            ClassificationOverride.field_name == payload.field_name,
            ClassificationOverride.asset_name.is_(payload.asset_name)
            if payload.asset_name is None
            else ClassificationOverride.asset_name == payload.asset_name,
        )
    )
    if existing is not None:
        existing.classification = payload.classification
        existing.category = payload.category
        existing.note = payload.note
        override = existing
    else:
        override = ClassificationOverride(
            organization_id=ctx.organization_id,
            field_name=payload.field_name,
            asset_name=payload.asset_name,
            classification=payload.classification,
            category=payload.category,
            note=payload.note,
            created_by=ctx.user.id,
        )
        db.add(override)
        db.flush()

    record_audit(
        db,
        action="classification.override_set",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="classification_override",
        entity_id=override.id,
        metadata={
            "field_name": payload.field_name,
            "classification": payload.classification,
            "asset_name": payload.asset_name,
        },
    )
    db.commit()
    db.refresh(override)
    return _to_out(override)


@router.delete("/classification-overrides/{override_id}", status_code=204, response_model=None)
def delete_override(
    override_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_INVENTORY)),
    db: Session = Depends(get_db),
) -> None:
    override = get_org_scoped(db, ClassificationOverride, override_id, ctx.organization_id)
    db.delete(override)
    record_audit(
        db,
        action="classification.override_deleted",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="classification_override",
        entity_id=override_id,
    )
    db.commit()
