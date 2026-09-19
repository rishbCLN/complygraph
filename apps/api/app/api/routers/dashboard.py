"""Dashboard endpoints: summary metrics, risk trend, top findings, data posture."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context
from app.core.database import get_db
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    return dashboard_service.summary(db, ctx.organization)


@router.get("/risk-trend")
def dashboard_risk_trend(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[dict]:
    return dashboard_service.risk_trend(db, ctx.organization)


@router.get("/top-findings")
def dashboard_top_findings(
    limit: int = 5,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[dict]:
    return dashboard_service.top_findings(db, ctx.organization, limit=max(1, min(50, limit)))


@router.get("/data-posture")
def dashboard_data_posture(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    return dashboard_service.data_posture(db, ctx.organization)
