"""Custom regulatory pack authoring service.

A "pack" is a tenant-authored regulatory framework: one Regulation plus its
Obligations and Controls, scoped to the authoring organization. Packs can be
created from a structured document (parsed from YAML or JSON) or via the
structured API. Validation is strict and honest: legal_status must be a known
value, every control needs a code/title, and control codes must not collide
with controls already visible to the org (system + own).

Unknown evaluator_key values are permitted — the control engine falls back to a
generic evidence check — so a pack can be authored before bespoke evaluators
exist, mirroring the shipped packs.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.enums import CitationStatus, LegalStatus, RegulationStatus
from app.core.errors import NotFoundError, ValidationError
from app.models.regulatory import Control, Obligation, Regulation

_LEGAL_STATUSES = {s.value for s in LegalStatus}
_CITATION_STATUSES = {s.value for s in CitationStatus}
_REG_STATUSES = {s.value for s in RegulationStatus}
_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


# --- Document schema (validated on import) --------------------------------------


class _ControlDoc(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: str = "GENERAL"
    evaluator_key: str | None = None
    severity: str = "MEDIUM"
    applies_to: dict | None = None

    @field_validator("severity")
    @classmethod
    def _sev(cls, v: str) -> str:
        v = (v or "MEDIUM").upper()
        if v not in _SEVERITIES:
            raise ValueError(f"severity must be one of {sorted(_SEVERITIES)}")
        return v


class _ObligationDoc(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    legal_reference: str | None = None
    source_section: str | None = None
    source_url: str | None = None
    legal_status: str | None = None
    citation_status: str = CitationStatus.UNVERIFIED.value
    controls: list[_ControlDoc] = Field(default_factory=list)

    @field_validator("legal_status")
    @classmethod
    def _legal(cls, v: str | None) -> str | None:
        if v is not None and v not in _LEGAL_STATUSES:
            raise ValueError(f"legal_status must be one of {sorted(_LEGAL_STATUSES)}")
        return v

    @field_validator("citation_status")
    @classmethod
    def _cite(cls, v: str) -> str:
        if v not in _CITATION_STATUSES:
            raise ValueError(f"citation_status must be one of {sorted(_CITATION_STATUSES)}")
        return v


class _PackMeta(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    jurisdiction: str = "Internal"
    version: str | None = None
    legal_status: str = LegalStatus.INTERNAL_POLICY.value
    source_document: str | None = None
    source_url: str | None = None
    status: str = RegulationStatus.IN_FORCE.value

    @field_validator("legal_status")
    @classmethod
    def _legal(cls, v: str) -> str:
        if v not in _LEGAL_STATUSES:
            raise ValueError(f"legal_status must be one of {sorted(_LEGAL_STATUSES)}")
        return v

    @field_validator("status")
    @classmethod
    def _status(cls, v: str) -> str:
        if v not in _REG_STATUSES:
            raise ValueError(f"status must be one of {sorted(_REG_STATUSES)}")
        return v


class PackDoc(BaseModel):
    pack: _PackMeta
    obligations: list[_ObligationDoc] = Field(default_factory=list)


def parse_pack_document(raw: str, fmt: str) -> dict:
    """Parse raw pack text (YAML or JSON) into a dict for validation."""
    fmt = (fmt or "yaml").lower()
    if fmt not in {"yaml", "json"}:
        raise ValidationError("format must be 'yaml' or 'json'.")
    try:
        if fmt == "json":
            import json

            data = json.loads(raw)
        else:
            import yaml

            data = yaml.safe_load(raw)
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(f"Could not parse {fmt.upper()} document: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError("Pack document must be a mapping/object at the top level.")
    return data


def validate_pack(data: dict) -> PackDoc:
    try:
        doc = PackDoc.model_validate(data)
    except PydanticValidationError as exc:
        # Surface the first readable error.
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = ".".join(str(p) for p in first.get("loc", []))
        msg = first.get("msg", "invalid pack document")
        raise ValidationError(f"Invalid pack document at '{loc}': {msg}") from exc

    if not doc.obligations:
        raise ValidationError("A pack must contain at least one obligation.")
    total_controls = sum(len(o.controls) for o in doc.obligations)
    if total_controls == 0:
        raise ValidationError("A pack must contain at least one control.")

    # Duplicate control codes within the document are rejected up-front.
    seen: set[str] = set()
    for ob in doc.obligations:
        for c in ob.controls:
            if c.code in seen:
                raise ValidationError(f"Duplicate control code in document: {c.code}")
            seen.add(c.code)
    return doc


# --- Persistence ----------------------------------------------------------------


def _assert_codes_available(db: Session, doc: PackDoc) -> None:
    codes = [c.code for ob in doc.obligations for c in ob.controls]
    existing = db.scalars(select(Control.code).where(Control.code.in_(codes))).all()
    if existing:
        raise ValidationError(
            "These control codes already exist and must be unique: "
            + ", ".join(sorted(set(existing)))
        )


def create_pack_from_doc(
    db: Session, org_id: uuid.UUID, user_id: uuid.UUID | None, doc: PackDoc
) -> Regulation:
    _assert_codes_available(db, doc)

    meta = doc.pack
    regulation = Regulation(
        name=meta.name,
        jurisdiction=meta.jurisdiction,
        version=meta.version,
        source_document=meta.source_document,
        source_url=meta.source_url,
        pack=f"custom:{org_id}",
        pack_version=meta.version or "1.0",
        legal_status=meta.legal_status,
        status=meta.status,
        enabled=True,
        organization_id=org_id,
        created_by=user_id,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(regulation)
    db.flush()

    for ob in doc.obligations:
        obligation = Obligation(
            regulation_id=regulation.id,
            code=ob.code,
            title=ob.title,
            description=ob.description,
            legal_reference=ob.legal_reference,
            source_section=ob.source_section,
            source_url=ob.source_url,
            legal_status=ob.legal_status or meta.legal_status,
            citation_status=ob.citation_status,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(obligation)
        db.flush()
        for c in ob.controls:
            db.add(
                Control(
                    obligation_id=obligation.id,
                    code=c.code,
                    title=c.title,
                    description=c.description,
                    category=c.category or "GENERAL",
                    assessment_method="deterministic",
                    evaluator_key=c.evaluator_key,
                    severity_default=c.severity,
                    applies_to=c.applies_to,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
            )
    db.flush()
    return regulation


def import_pack(
    db: Session, org_id: uuid.UUID, user_id: uuid.UUID | None, raw: str, fmt: str
) -> Regulation:
    data = parse_pack_document(raw, fmt)
    doc = validate_pack(data)
    return create_pack_from_doc(db, org_id, user_id, doc)


def create_pack(
    db: Session, org_id: uuid.UUID, user_id: uuid.UUID | None, data: dict
) -> Regulation:
    doc = validate_pack(data)
    return create_pack_from_doc(db, org_id, user_id, doc)


def list_custom_packs(db: Session, org_id: uuid.UUID) -> list[Regulation]:
    return list(
        db.scalars(
            select(Regulation)
            .where(Regulation.organization_id == org_id)
            .order_by(Regulation.name)
        )
    )


def get_custom_pack(db: Session, org_id: uuid.UUID, regulation_id: uuid.UUID) -> Regulation:
    reg = db.get(Regulation, regulation_id)
    if reg is None or reg.organization_id != org_id:
        raise NotFoundError("Custom pack not found.")
    return reg


def delete_custom_pack(db: Session, org_id: uuid.UUID, regulation_id: uuid.UUID) -> Regulation:
    reg = db.get(Regulation, regulation_id)
    if reg is None:
        raise NotFoundError("Regulation not found.")
    if reg.organization_id is None:
        raise ValidationError("System regulations cannot be deleted.")
    if reg.organization_id != org_id:
        raise NotFoundError("Custom pack not found.")

    # Explicit FK-safe teardown. The ORM would otherwise try to NULL the child
    # FKs (which are NOT NULL); we delete dependents bottom-up instead so the
    # behaviour is identical on SQLite and PostgreSQL.
    from app.models.evidence import ControlEvidence
    from app.models.findings import Finding
    from app.models.regulatory import (
        Control,
        ControlAssessment,
        ControlAssetScope,
        ControlMapping,
        Obligation,
    )

    obligation_ids = db.scalars(
        select(Obligation.id).where(Obligation.regulation_id == regulation_id)
    ).all()
    if obligation_ids:
        control_ids = db.scalars(
            select(Control.id).where(Control.obligation_id.in_(obligation_ids))
        ).all()
        if control_ids:
            db.execute(
                delete(ControlMapping).where(
                    ControlMapping.source_control_id.in_(control_ids)
                )
            )
            db.execute(
                delete(ControlMapping).where(
                    ControlMapping.target_control_id.in_(control_ids)
                )
            )
            db.execute(
                delete(ControlEvidence).where(ControlEvidence.control_id.in_(control_ids))
            )
            db.execute(
                delete(ControlAssetScope).where(ControlAssetScope.control_id.in_(control_ids))
            )
            db.execute(
                delete(ControlAssessment).where(ControlAssessment.control_id.in_(control_ids))
            )
            db.execute(delete(Finding).where(Finding.control_id.in_(control_ids)))
            db.execute(delete(Control).where(Control.id.in_(control_ids)))
        db.execute(delete(Obligation).where(Obligation.id.in_(obligation_ids)))
    db.delete(reg)
    db.flush()
    return reg


def control_count(db: Session, regulation_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count(Control.id))
            .select_from(Control)
            .join(Obligation, Obligation.id == Control.obligation_id)
            .where(Obligation.regulation_id == regulation_id)
        )
        or 0
    )
