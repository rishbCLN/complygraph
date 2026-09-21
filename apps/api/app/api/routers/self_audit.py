"""Self-audit / data-quality endpoints.

Read-only. Surfaces the completeness/quality of the compliance data itself so a
team can see where its inventory is too thin to trust downstream conclusions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context
from app.core.database import get_db
from app.services import self_audit_service

router = APIRouter(prefix="/self-audit", tags=["self-audit"])


class QualityItemOut(BaseModel):
    type: str
    id: str
    label: str
    detail: str


class QualityCheckOut(BaseModel):
    key: str
    title: str
    category: str
    severity: str
    recommendation: str
    total: int
    complete: int
    incomplete: int
    score: int
    items: list[QualityItemOut]
    items_truncated: bool


class SelfAuditOut(BaseModel):
    organization: str
    assessment_date: str
    overall_score: int
    total_gaps: int
    check_count: int
    checks: list[QualityCheckOut]


@router.get("", response_model=SelfAuditOut)
def self_audit(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> SelfAuditOut:
    return SelfAuditOut(**self_audit_service.run_self_audit(db, ctx.organization))
