"""Policy document analysis endpoint.

Upload a privacy notice / policy document; ComplyGraph extracts its text and
checks for the DPDP clauses it should contain, then records the document as
Evidence with the coverage summary. This makes document evidence content-aware
instead of metadata-only.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, require_capability
from app.core.audit import record_audit
from app.core.config import settings
from app.core.database import get_db, utcnow
from app.core.enums import EvidenceStatus, EvidenceType
from app.core.errors import ValidationError
from app.core.rbac import MANAGE_EVIDENCE
from app.models.evidence import ControlEvidence, Evidence
from app.models.regulatory import Control
from app.services import document_analysis
from app.services.evidence_service import hash_bytes

router = APIRouter(tags=["documents"])

_ALLOWED_EXTS = {"txt", "md", "markdown", "rst", "pdf"}


class ClauseResult(BaseModel):
    key: str
    title: str
    present: bool
    required: bool


class DocumentAnalysisOut(BaseModel):
    evidence_id: str
    document_name: str
    coverage: float
    is_adequate: bool
    missing_required: list[str]
    present_optional: list[str]
    clauses: list[ClauseResult]
    linked_control: str | None = None


@router.post("/documents/analyze", response_model=DocumentAnalysisOut, status_code=201)
async def analyze_document(
    file: UploadFile = File(...),
    control_code: str | None = Form(default=None),
    ctx: AuthContext = Depends(require_capability(MANAGE_EVIDENCE)),
    db: Session = Depends(get_db),
) -> DocumentAnalysisOut:
    filename = (file.filename or "policy").strip()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_EXTS:
        raise ValidationError(
            "Supported document types: " + ", ".join(sorted(_ALLOWED_EXTS)) + "."
        )
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise ValidationError("Document exceeds the upload size limit.")

    try:
        text = document_analysis.extract_text(content, filename)
    except document_analysis.DocumentExtractionError as exc:
        raise ValidationError(str(exc)) from exc

    analysis = document_analysis.analyze_policy(text)
    titles = document_analysis.clause_titles()

    # Optionally link to a specific control (e.g. the notice/transparency control).
    linked_control: Control | None = None
    if control_code:
        linked_control = db.scalar(select(Control).where(Control.code == control_code))
        if linked_control is None:
            raise ValidationError(f"Unknown control code: {control_code}")

    # A document that covers all required clauses is treated as FRESH supporting
    # evidence; otherwise it is recorded but flagged UNKNOWN (inadequate content).
    status = EvidenceStatus.FRESH.value if analysis.is_adequate else EvidenceStatus.UNKNOWN.value
    missing = ", ".join(titles.get(k, k) for k in analysis.missing_required) or "none"
    evidence = Evidence(
        organization_id=ctx.organization_id,
        type=EvidenceType.POLICY.value,
        name=filename,
        description=(
            f"Automated clause check: {int(analysis.coverage * 100)}% of required DPDP "
            f"clauses present. Missing: {missing}."
        ),
        source="document-analysis",
        hash=hash_bytes(content),
        collected_at=utcnow(),
        status=status,
    )
    db.add(evidence)
    db.flush()

    if linked_control is not None:
        db.add(
            ControlEvidence(
                control_id=linked_control.id,
                evidence_id=evidence.id,
                relation_type="SUPPORTS" if analysis.is_adequate else "PARTIAL",
                created_at=utcnow(),
            )
        )

    record_audit(
        db,
        action="document.analyzed",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="evidence",
        entity_id=evidence.id,
        metadata={
            "coverage": analysis.coverage,
            "missing_required": analysis.missing_required,
            "control_code": control_code,
        },
    )
    db.commit()

    return DocumentAnalysisOut(
        evidence_id=str(evidence.id),
        document_name=filename,
        coverage=analysis.coverage,
        is_adequate=analysis.is_adequate,
        missing_required=analysis.missing_required,
        present_optional=analysis.present_optional,
        clauses=[
            ClauseResult(
                key=key,
                title=titles.get(key, key),
                present=present,
                required=key not in {"cross_border", "children", "breach"},
            )
            for key, present in analysis.clause_detail.items()
        ],
        linked_control=linked_control.code if linked_control else None,
    )
