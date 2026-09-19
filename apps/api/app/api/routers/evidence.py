"""Evidence endpoints: list, upload, link, expire, delete."""

from __future__ import annotations

import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.api.query import get_org_scoped
from app.core.audit import record_audit
from app.core.config import settings
from app.core.database import get_db, utcnow
from app.core.enums import EvidenceRelation, EvidenceType
from app.core.errors import NotFoundError, ValidationError
from app.core.rbac import DELETE_EVIDENCE, MANAGE_EVIDENCE
from app.models.evidence import ControlEvidence, Evidence
from app.models.regulatory import Control
from app.services.evidence_service import compute_freshness, hash_bytes

router = APIRouter(prefix="/evidence", tags=["evidence"])


class EvidenceOut(BaseModel):
    id: str
    type: str
    name: str
    description: str | None
    source: str | None
    hash: str | None
    status: str
    owner: str | None
    collected_at: datetime | None
    expires_at: datetime | None
    linked_controls: int


class EvidenceCreate(BaseModel):
    type: str = EvidenceType.MANUAL_ATTESTATION.value
    name: str
    description: str | None = None
    source: str | None = None
    source_url: str | None = None
    collected_at: datetime | None = None
    expires_at: datetime | None = None
    owner: str | None = None


class LinkRequest(BaseModel):
    control_id: uuid.UUID
    relation_type: str = EvidenceRelation.SUPPORTS.value


def _out(db: Session, ctx: AuthContext, e: Evidence) -> EvidenceOut:
    from sqlalchemy import func

    from app.services.assessment_service import get_assessment_date

    links = db.scalar(select(func.count(ControlEvidence.id)).where(ControlEvidence.evidence_id == e.id)) or 0
    status = compute_freshness(e.collected_at, e.expires_at, get_assessment_date(ctx.organization))
    return EvidenceOut(
        id=str(e.id),
        type=e.type,
        name=e.name,
        description=e.description,
        source=e.source,
        hash=e.hash,
        status=status,
        owner=e.owner,
        collected_at=e.collected_at,
        expires_at=e.expires_at,
        linked_controls=int(links),
    )


@router.get("", response_model=list[EvidenceOut])
def list_evidence(
    ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)
) -> list[EvidenceOut]:
    rows = db.scalars(
        select(Evidence)
        .where(Evidence.organization_id == ctx.organization_id)
        .order_by(Evidence.created_at.desc())
    )
    return [_out(db, ctx, e) for e in rows]


@router.post("", response_model=EvidenceOut, status_code=201)
def create_evidence(
    payload: EvidenceCreate,
    ctx: AuthContext = Depends(require_capability(MANAGE_EVIDENCE)),
    db: Session = Depends(get_db),
) -> EvidenceOut:
    if payload.type not in {t.value for t in EvidenceType}:
        raise ValidationError(f"Unsupported evidence type: {payload.type}")
    evidence = Evidence(
        organization_id=ctx.organization_id,
        type=payload.type,
        name=payload.name,
        description=payload.description,
        source=payload.source,
        source_url=payload.source_url,
        collected_at=payload.collected_at or utcnow(),
        expires_at=payload.expires_at,
        owner=payload.owner,
    )
    evidence.status = compute_freshness(evidence.collected_at, evidence.expires_at)
    db.add(evidence)
    db.flush()
    record_audit(
        db,
        action="evidence.created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="evidence",
        entity_id=evidence.id,
    )
    db.commit()
    return _out(db, ctx, evidence)


@router.post("/upload", response_model=EvidenceOut, status_code=201)
async def upload_evidence(
    file: UploadFile = File(...),
    name: str = Form(...),
    type: str = Form(EvidenceType.DOCUMENT.value),
    description: str | None = Form(None),
    ctx: AuthContext = Depends(require_capability(MANAGE_EVIDENCE)),
    db: Session = Depends(get_db),
) -> EvidenceOut:
    """Upload an evidence file. Validated by extension + size; hashed for integrity."""
    filename = (file.filename or "evidence").strip()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in settings.allowed_extensions:
        raise ValidationError(f"File type .{ext} is not allowed.")
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise ValidationError("File exceeds the 25 MB limit.")

    digest = hash_bytes(content)
    os.makedirs(settings.storage_dir, exist_ok=True)
    # Random storage id; never trust the client filename for the path.
    storage_id = f"{uuid.uuid4().hex}.{ext}"
    storage_path = os.path.join(settings.storage_dir, storage_id)
    with open(storage_path, "wb") as fh:
        fh.write(content)

    evidence = Evidence(
        organization_id=ctx.organization_id,
        type=type if type in {t.value for t in EvidenceType} else EvidenceType.DOCUMENT.value,
        name=name,
        description=description,
        source="upload",
        file_path=storage_path,
        hash=digest,
        collected_at=utcnow(),
    )
    evidence.status = compute_freshness(evidence.collected_at, evidence.expires_at)
    db.add(evidence)
    db.flush()
    record_audit(
        db,
        action="evidence.uploaded",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="evidence",
        entity_id=evidence.id,
        metadata={"hash": digest, "size_bytes": len(content)},
    )
    db.commit()
    return _out(db, ctx, evidence)


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence(
    evidence_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> EvidenceOut:
    return _out(db, ctx, get_org_scoped(db, Evidence, evidence_id, ctx.organization_id))


@router.patch("/{evidence_id}", response_model=EvidenceOut)
def update_evidence(
    evidence_id: uuid.UUID,
    payload: EvidenceCreate,
    ctx: AuthContext = Depends(require_capability(MANAGE_EVIDENCE)),
    db: Session = Depends(get_db),
) -> EvidenceOut:
    evidence = get_org_scoped(db, Evidence, evidence_id, ctx.organization_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(evidence, key, value)
    evidence.status = compute_freshness(evidence.collected_at, evidence.expires_at)
    db.commit()
    return _out(db, ctx, evidence)


@router.post("/{evidence_id}/expire", response_model=EvidenceOut)
def expire_evidence(
    evidence_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_EVIDENCE)),
    db: Session = Depends(get_db),
) -> EvidenceOut:
    evidence = get_org_scoped(db, Evidence, evidence_id, ctx.organization_id)
    evidence.expires_at = utcnow()
    evidence.status = "EXPIRED"
    record_audit(
        db,
        action="evidence.expired",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="evidence",
        entity_id=evidence.id,
    )
    db.commit()
    return _out(db, ctx, evidence)


@router.delete("/{evidence_id}", status_code=204, response_model=None)
def delete_evidence(
    evidence_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(DELETE_EVIDENCE)),
    db: Session = Depends(get_db),
) -> None:
    evidence = get_org_scoped(db, Evidence, evidence_id, ctx.organization_id)
    db.delete(evidence)
    record_audit(
        db,
        action="evidence.deleted",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="evidence",
        entity_id=evidence_id,
    )
    db.commit()


@router.post("/{evidence_id}/link")
def link_evidence(
    evidence_id: uuid.UUID,
    payload: LinkRequest,
    ctx: AuthContext = Depends(require_capability(MANAGE_EVIDENCE)),
    db: Session = Depends(get_db),
) -> dict:
    evidence = get_org_scoped(db, Evidence, evidence_id, ctx.organization_id)
    control = db.get(Control, payload.control_id)
    if not control:
        raise NotFoundError("Control not found.")
    existing = db.scalar(
        select(ControlEvidence).where(
            ControlEvidence.evidence_id == evidence.id,
            ControlEvidence.control_id == control.id,
        )
    )
    if existing is None:
        db.add(
            ControlEvidence(
                control_id=control.id,
                evidence_id=evidence.id,
                relation_type=payload.relation_type,
                created_at=utcnow(),
            )
        )
    record_audit(
        db,
        action="evidence.linked",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="evidence",
        entity_id=evidence.id,
        metadata={"control_code": control.code},
    )
    db.commit()
    return {"message": "Evidence linked to control."}
