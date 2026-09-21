"""Org-wide re-assessment endpoint (feature #6).

Complements the per-control ``POST /controls/{id}/assess`` with a single call
that re-assesses every control, records history, and surfaces regressions. The
same routine runs on the celery-beat cadence.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, require_capability
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.rbac import ASSESS_CONTROLS
from app.services.reassessment_service import run_reassessment

router = APIRouter(prefix="/reassessment", tags=["reassessment"])


class RegressedControl(BaseModel):
    control_id: str
    control_code: str
    from_status: str
    to_status: str


class ReassessmentResult(BaseModel):
    controls_assessed: int
    regressions: int
    improvements: int
    status_counts: dict[str, int]
    regressed_controls: list[RegressedControl]


@router.post("/run", response_model=ReassessmentResult)
def run(
    ctx: AuthContext = Depends(require_capability(ASSESS_CONTROLS)),
    db: Session = Depends(get_db),
) -> ReassessmentResult:
    summary = run_reassessment(db, ctx.organization)
    record_audit(
        db,
        action="reassessment.run",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="reassessment",
        metadata={
            "controls_assessed": summary["controls_assessed"],
            "regressions": summary["regressions"],
        },
    )
    db.commit()
    return ReassessmentResult(
        controls_assessed=summary["controls_assessed"],
        regressions=summary["regressions"],
        improvements=summary["improvements"],
        status_counts=summary["status_counts"],
        regressed_controls=[
            RegressedControl(
                control_id=r["control_id"],
                control_code=r["control_code"],
                from_status=r["from"],
                to_status=r["to"],
            )
            for r in summary["regressed_controls"]
        ],
    )
