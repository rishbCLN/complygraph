"""Vendor endpoints, including vendor flow analysis."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.api.query import get_org_scoped
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.rbac import MANAGE_INVENTORY
from app.models.findings import Finding
from app.models.inventory import DataFlow, Vendor

router = APIRouter(prefix="/vendors", tags=["vendors"])


class VendorIn(BaseModel):
    name: str
    description: str | None = None
    service_type: str | None = None
    country: str | None = None
    data_processing: str | None = None
    contract_status: str | None = "UNKNOWN"
    risk_level: str | None = "MEDIUM"
    owner: str | None = None


class VendorOut(BaseModel):
    id: str
    name: str
    description: str | None
    service_type: str | None
    country: str | None
    data_processing: str | None
    contract_status: str
    risk_level: str
    owner: str | None
    personal_data_flows: int
    open_findings: int


def _out(db: Session, v: Vendor) -> VendorOut:
    from sqlalchemy import func

    flow_count = db.scalar(
        select(func.count(DataFlow.id)).where(
            DataFlow.vendor_id == v.id, DataFlow.contains_personal_data.is_(True)
        )
    ) or 0
    finding_count = db.scalar(
        select(func.count(Finding.id)).where(
            Finding.vendor_id == v.id, Finding.status.in_(["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"])
        )
    ) or 0
    return VendorOut(
        id=str(v.id),
        name=v.name,
        description=v.description,
        service_type=v.service_type,
        country=v.country,
        data_processing=v.data_processing,
        contract_status=v.contract_status,
        risk_level=v.risk_level,
        owner=v.owner,
        personal_data_flows=int(flow_count),
        open_findings=int(finding_count),
    )


@router.get("", response_model=list[VendorOut])
def list_vendors(
    ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)
) -> list[VendorOut]:
    rows = db.scalars(
        select(Vendor).where(Vendor.organization_id == ctx.organization_id).order_by(Vendor.name)
    )
    return [_out(db, v) for v in rows]


@router.post("", response_model=VendorOut, status_code=201)
def create_vendor(
    payload: VendorIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_INVENTORY)),
    db: Session = Depends(get_db),
) -> VendorOut:
    vendor = Vendor(organization_id=ctx.organization_id, **payload.model_dump(exclude_none=True))
    db.add(vendor)
    db.flush()
    record_audit(
        db,
        action="vendor.created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="vendor",
        entity_id=vendor.id,
    )
    db.commit()
    return _out(db, vendor)


@router.get("/{vendor_id}", response_model=VendorOut)
def get_vendor(
    vendor_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> VendorOut:
    return _out(db, get_org_scoped(db, Vendor, vendor_id, ctx.organization_id))


@router.patch("/{vendor_id}", response_model=VendorOut)
def update_vendor(
    vendor_id: uuid.UUID,
    payload: VendorIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_INVENTORY)),
    db: Session = Depends(get_db),
) -> VendorOut:
    vendor = get_org_scoped(db, Vendor, vendor_id, ctx.organization_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(vendor, key, value)
    record_audit(
        db,
        action="vendor.updated",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="vendor",
        entity_id=vendor.id,
    )
    db.commit()
    return _out(db, vendor)
