"""Unified search across assets, findings, controls, and vendors."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context
from app.core.database import get_db
from app.models.findings import Finding
from app.models.inventory import DataAsset, Vendor
from app.models.regulatory import Control

router = APIRouter(tags=["search"])


@router.get("/search")
def unified_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    """Search assets, findings, controls, and vendors for a term."""
    like = f"%{q}%"
    org_id = ctx.organization_id

    assets = db.scalars(
        select(DataAsset)
        .where(
            DataAsset.organization_id == org_id,
            or_(DataAsset.name.ilike(like), DataAsset.display_name.ilike(like)),
        )
        .limit(limit)
    )
    findings = db.scalars(
        select(Finding)
        .where(
            Finding.organization_id == org_id,
            or_(Finding.title.ilike(like), Finding.description.ilike(like)),
        )
        .limit(limit)
    )
    # Controls are global (framework definitions), not org-scoped.
    controls = db.scalars(
        select(Control)
        .where(or_(Control.code.ilike(like), Control.title.ilike(like), Control.description.ilike(like)))
        .limit(limit)
    )
    vendors = db.scalars(
        select(Vendor)
        .where(Vendor.organization_id == org_id, Vendor.name.ilike(like))
        .limit(limit)
    )

    return {
        "query": q,
        "assets": [
            {"id": str(a.id), "label": a.display_name or a.name, "type": a.asset_type}
            for a in assets
        ],
        "findings": [
            {"id": str(f.id), "label": f.title, "severity": f.severity} for f in findings
        ],
        "controls": [
            {"id": str(c.id), "label": f"{c.code} - {c.title}", "code": c.code} for c in controls
        ],
        "vendors": [{"id": str(v.id), "label": v.name} for v in vendors],
    }
