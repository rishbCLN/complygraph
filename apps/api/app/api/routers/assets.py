"""Data asset endpoints with filtering."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.api.query import get_org_scoped, paginate
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.rbac import MANAGE_INVENTORY
from app.models.inventory import AssetField, DataAsset, DataFlow, Vendor
from app.models.regulatory import Control, ControlAssetScope
from app.schemas.common import Page

router = APIRouter(tags=["assets"])


class AssetFieldOut(BaseModel):
    id: str
    name: str
    data_type: str | None
    classification: str
    category: str
    confidence: float
    confidence_band: str
    detection_method: str | None
    needs_review: bool
    masked_examples: str | None


class AssetOut(BaseModel):
    id: str
    name: str
    display_name: str | None
    asset_type: str
    system_name: str | None
    environment: str | None
    classification: str
    sensitivity_level: int
    owner: str | None
    row_count: int | None
    field_count: int
    personal_data: bool
    last_seen_at: datetime | None


class AssetUpdate(BaseModel):
    display_name: str | None = None
    owner: str | None = None
    description: str | None = None


def _asset_out(db: Session, a: DataAsset) -> AssetOut:
    field_count = db.scalar(
        select(__import__("sqlalchemy").func.count(AssetField.id)).where(AssetField.asset_id == a.id)
    ) or 0
    personal = a.classification in {"PERSONAL_DATA", "SENSITIVE_PERSONAL_DATA"}
    return AssetOut(
        id=str(a.id),
        name=a.name,
        display_name=a.display_name,
        asset_type=a.asset_type,
        system_name=a.system_name,
        environment=a.environment,
        classification=a.classification,
        sensitivity_level=a.sensitivity_level,
        owner=a.owner,
        row_count=a.row_count,
        field_count=int(field_count),
        personal_data=personal,
        last_seen_at=a.last_seen_at,
    )


@router.get("/assets", response_model=Page[AssetOut])
def list_assets(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    classification: str | None = None,
    asset_type: str | None = None,
    system: str | None = None,
    owner: str | None = None,
    sensitivity: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> Page[AssetOut]:
    stmt = select(DataAsset).where(DataAsset.organization_id == ctx.organization_id)
    if classification:
        stmt = stmt.where(DataAsset.classification == classification)
    if asset_type:
        stmt = stmt.where(DataAsset.asset_type == asset_type)
    if system:
        stmt = stmt.where(DataAsset.system_name == system)
    if owner:
        stmt = stmt.where(DataAsset.owner == owner)
    if sensitivity:
        stmt = stmt.where(DataAsset.sensitivity_level == sensitivity)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(DataAsset.name.ilike(like), DataAsset.display_name.ilike(like)))
    stmt = stmt.order_by(DataAsset.sensitivity_level.desc(), DataAsset.name)
    rows, total = paginate(db, stmt, page, page_size)
    return Page(items=[_asset_out(db, a) for a in rows], total=total, page=page, page_size=page_size)


@router.get("/assets/{asset_id}", response_model=AssetOut)
def get_asset(
    asset_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> AssetOut:
    return _asset_out(db, get_org_scoped(db, DataAsset, asset_id, ctx.organization_id))


@router.get("/assets/{asset_id}/fields", response_model=list[AssetFieldOut])
def get_asset_fields(
    asset_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[AssetFieldOut]:
    get_org_scoped(db, DataAsset, asset_id, ctx.organization_id)
    rows = db.scalars(select(AssetField).where(AssetField.asset_id == asset_id).order_by(AssetField.name))
    return [
        AssetFieldOut(
            id=str(f.id),
            name=f.name,
            data_type=f.data_type,
            classification=f.classification,
            category=f.category,
            confidence=f.confidence,
            confidence_band=f.confidence_band,
            detection_method=f.detection_method,
            needs_review=f.needs_review,
            masked_examples=f.masked_examples,
        )
        for f in rows
    ]


class FlowOut(BaseModel):
    id: str
    source_asset_id: str | None
    destination_asset_id: str | None
    flow_type: str
    purpose: str | None
    contains_personal_data: bool
    cross_border: bool
    vendor_id: str | None
    categories: str | None


@router.get("/assets/{asset_id}/flows", response_model=list[FlowOut])
def get_asset_flows(
    asset_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[FlowOut]:
    get_org_scoped(db, DataAsset, asset_id, ctx.organization_id)
    rows = db.scalars(
        select(DataFlow).where(
            DataFlow.organization_id == ctx.organization_id,
            or_(DataFlow.source_asset_id == asset_id, DataFlow.destination_asset_id == asset_id),
        )
    )
    return [
        FlowOut(
            id=str(f.id),
            source_asset_id=str(f.source_asset_id) if f.source_asset_id else None,
            destination_asset_id=str(f.destination_asset_id) if f.destination_asset_id else None,
            flow_type=f.flow_type,
            purpose=f.purpose,
            contains_personal_data=f.contains_personal_data,
            cross_border=f.cross_border,
            vendor_id=str(f.vendor_id) if f.vendor_id else None,
            categories=f.categories,
        )
        for f in rows
    ]


class AssetControlOut(BaseModel):
    control_id: str
    code: str
    title: str
    reason: str | None
    applicable: bool


@router.get("/assets/{asset_id}/controls", response_model=list[AssetControlOut])
def get_asset_controls(
    asset_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[AssetControlOut]:
    get_org_scoped(db, DataAsset, asset_id, ctx.organization_id)
    rows = db.execute(
        select(Control, ControlAssetScope)
        .join(ControlAssetScope, ControlAssetScope.control_id == Control.id)
        .where(ControlAssetScope.asset_id == asset_id)
    ).all()
    return [
        AssetControlOut(
            control_id=str(c.id),
            code=c.code,
            title=c.title,
            reason=s.reason,
            applicable=s.applicable,
        )
        for c, s in rows
    ]


@router.patch("/assets/{asset_id}", response_model=AssetOut)
def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    ctx: AuthContext = Depends(require_capability(MANAGE_INVENTORY)),
    db: Session = Depends(get_db),
) -> AssetOut:
    asset = get_org_scoped(db, DataAsset, asset_id, ctx.organization_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(asset, key, value)
    record_audit(
        db,
        action="asset.updated",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="asset",
        entity_id=asset.id,
    )
    db.commit()
    return _asset_out(db, asset)
