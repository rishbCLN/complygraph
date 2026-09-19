"""AI investigation endpoints: list and retrieve stored investigations.

The trigger endpoint lives on the finding resource
(POST /findings/{id}/investigate). These endpoints expose the stored,
sanitized investigation artifacts, including the explicit sanitization notice.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models.operations import AIInvestigation
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


class InvestigationOut(BaseModel):
    id: str
    finding_id: str | None
    mode: str
    model: str | None
    status: str
    summary: str | None
    root_causes: list | None
    recommendations: list | None
    missing_evidence: list | None
    legal_review_required: bool
    uncertainty: str | None
    evidence_considered: list | None
    input_sanitized: bool
    # Explicit privacy notices surfaced in the investigation detail.
    input_sanitized_notice: str = "AI input sanitized"
    raw_pii_excluded_notice: str = "Raw personal data excluded"


def _out(inv: AIInvestigation) -> InvestigationOut:
    return InvestigationOut(
        id=str(inv.id),
        finding_id=str(inv.finding_id) if inv.finding_id else None,
        mode=inv.mode,
        model=inv.model,
        status=inv.status,
        summary=inv.summary,
        root_causes=inv.root_causes,
        recommendations=inv.recommendations,
        missing_evidence=inv.missing_evidence,
        legal_review_required=inv.legal_review_required,
        uncertainty=inv.uncertainty,
        evidence_considered=inv.evidence_considered,
        input_sanitized=inv.input_sanitized,
    )


@router.get("/mode")
def ai_mode() -> dict:
    """Report the effective AI mode so the UI can show availability."""
    return {"ai_mode": settings.effective_ai_mode, "model": settings.anthropic_model}


@router.get("/investigations", response_model=list[InvestigationOut])
def list_investigations(
    finding_id: uuid.UUID | None = None,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[InvestigationOut]:
    rows = ai_service.list_investigations(db, ctx.organization_id, finding_id)
    return [_out(i) for i in rows]


@router.get("/investigations/{investigation_id}", response_model=InvestigationOut)
def get_investigation(
    investigation_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> InvestigationOut:
    inv = ai_service.get_investigation(db, ctx.organization_id, investigation_id)
    if inv is None:
        raise NotFoundError("Investigation not found.")
    return _out(inv)
