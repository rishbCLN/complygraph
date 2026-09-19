"""Data-map / graph endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context
from app.core.database import get_db
from app.services import graph_service

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/data")
def get_data_graph(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    """Return the full data-flow map ({nodes, edges}) for the organization."""
    return graph_service.data_graph(db, ctx.organization_id)


@router.get("/asset/{asset_id}")
def get_asset_graph(
    asset_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    """Return the neighborhood graph for a single asset."""
    return graph_service.asset_graph(db, ctx.organization_id, asset_id)


@router.get("/control")
def get_control_graph(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    """Return the control-overlay graph linking controls, evidence, and findings."""
    return graph_service.control_graph(db, ctx.organization_id)
