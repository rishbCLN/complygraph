"""Consent management endpoints (feature #8, staff side).

Authenticated operators manage the purpose catalogue, versioned notices, and can
view/record consent on a principal's behalf. The public data-principal portal
lives in privacy_center.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.enums import ConsentMethod
from app.core.rbac import MANAGE_CONSENT
from app.models.consent import ConsentEvent, ConsentNotice, ConsentPurpose, ConsentRecord
from app.services import consent_service

router = APIRouter(prefix="/consent", tags=["consent"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class PurposeIn(BaseModel):
    code: str
    name: str
    description: str | None = None
    lawful_basis: str | None = None
    requires_consent: bool = True
    is_sensitive: bool = False
    default_expiry_days: int | None = None
    display_order: int | None = None
    processing_activity_id: uuid.UUID | None = None


class PurposePatch(BaseModel):
    name: str | None = None
    description: str | None = None
    lawful_basis: str | None = None
    requires_consent: bool | None = None
    is_sensitive: bool | None = None
    default_expiry_days: int | None = None
    display_order: int | None = None
    processing_activity_id: uuid.UUID | None = None
    status: str | None = None


class PurposeOut(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    lawful_basis: str
    requires_consent: bool
    is_sensitive: bool
    default_expiry_days: int | None
    display_order: int
    status: str
    processing_activity_id: str | None


class NoticeIn(BaseModel):
    title: str
    body: str
    publish: bool = False


class NoticeOut(BaseModel):
    id: str
    version: int
    title: str
    body: str
    is_current: bool
    published_at: datetime | None


class RecordOut(BaseModel):
    id: str
    purpose_id: str
    principal_identifier: str
    status: str
    method: str
    notice_version: int | None
    granted_at: datetime | None
    withdrawn_at: datetime | None
    expires_at: datetime | None
    verified: bool


class EventOut(BaseModel):
    id: str
    purpose_id: str | None
    purpose_code: str
    purpose_name: str
    principal_identifier: str
    event_type: str
    method: str
    source: str
    notice_version: int | None
    actor: str | None
    created_at: datetime | None


class ConsentActionIn(BaseModel):
    purpose_id: uuid.UUID
    principal_identifier: str


def _purpose_out(p: ConsentPurpose) -> PurposeOut:
    return PurposeOut(
        id=str(p.id),
        code=p.code,
        name=p.name,
        description=p.description,
        lawful_basis=p.lawful_basis,
        requires_consent=p.requires_consent,
        is_sensitive=p.is_sensitive,
        default_expiry_days=p.default_expiry_days,
        display_order=p.display_order,
        status=p.status,
        processing_activity_id=str(p.processing_activity_id) if p.processing_activity_id else None,
    )


def _notice_out(n: ConsentNotice) -> NoticeOut:
    return NoticeOut(
        id=str(n.id),
        version=n.version,
        title=n.title,
        body=n.body,
        is_current=n.is_current,
        published_at=n.published_at,
    )


def _record_out(r: ConsentRecord) -> RecordOut:
    return RecordOut(
        id=str(r.id),
        purpose_id=str(r.purpose_id),
        principal_identifier=r.principal_identifier,
        status=r.status,
        method=r.method,
        notice_version=r.notice_version,
        granted_at=r.granted_at,
        withdrawn_at=r.withdrawn_at,
        expires_at=r.expires_at,
        verified=r.verified,
    )


def _event_out(e: ConsentEvent) -> EventOut:
    return EventOut(
        id=str(e.id),
        purpose_id=str(e.purpose_id) if e.purpose_id else None,
        purpose_code=e.purpose_code,
        purpose_name=e.purpose_name,
        principal_identifier=e.principal_identifier,
        event_type=e.event_type,
        method=e.method,
        source=e.source,
        notice_version=e.notice_version,
        actor=e.actor,
        created_at=e.created_at,
    )


# --------------------------------------------------------------------------- #
# Purposes
# --------------------------------------------------------------------------- #
@router.get("/purposes", response_model=list[PurposeOut])
def list_purposes(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    active_only: bool = Query(False),
) -> list[PurposeOut]:
    return [_purpose_out(p) for p in consent_service.list_purposes(db, ctx.organization_id, active_only=active_only)]


@router.post("/purposes", response_model=PurposeOut, status_code=201)
def create_purpose(
    payload: PurposeIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_CONSENT)),
    db: Session = Depends(get_db),
) -> PurposeOut:
    purpose = consent_service.create_purpose(db, ctx.organization_id, payload.model_dump(exclude_unset=True))
    record_audit(
        db,
        action="consent.purpose_created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="consent_purpose",
        entity_id=purpose.id,
        metadata={"code": purpose.code},
    )
    db.commit()
    db.refresh(purpose)
    return _purpose_out(purpose)


@router.patch("/purposes/{purpose_id}", response_model=PurposeOut)
def update_purpose(
    purpose_id: uuid.UUID,
    payload: PurposePatch,
    ctx: AuthContext = Depends(require_capability(MANAGE_CONSENT)),
    db: Session = Depends(get_db),
) -> PurposeOut:
    purpose = consent_service.update_purpose(
        db, ctx.organization_id, purpose_id, payload.model_dump(exclude_unset=True)
    )
    record_audit(
        db,
        action="consent.purpose_updated",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="consent_purpose",
        entity_id=purpose.id,
    )
    db.commit()
    db.refresh(purpose)
    return _purpose_out(purpose)


@router.delete("/purposes/{purpose_id}", response_model=PurposeOut)
def archive_purpose(
    purpose_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_CONSENT)),
    db: Session = Depends(get_db),
) -> PurposeOut:
    purpose = consent_service.archive_purpose(db, ctx.organization_id, purpose_id)
    record_audit(
        db,
        action="consent.purpose_archived",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="consent_purpose",
        entity_id=purpose.id,
    )
    db.commit()
    db.refresh(purpose)
    return _purpose_out(purpose)


# --------------------------------------------------------------------------- #
# Notices
# --------------------------------------------------------------------------- #
@router.get("/notices", response_model=list[NoticeOut])
def list_notices(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[NoticeOut]:
    return [_notice_out(n) for n in consent_service.list_notices(db, ctx.organization_id)]


@router.post("/notices", response_model=NoticeOut, status_code=201)
def create_notice(
    payload: NoticeIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_CONSENT)),
    db: Session = Depends(get_db),
) -> NoticeOut:
    notice = consent_service.create_notice(
        db, ctx.organization_id, payload.model_dump(), publish=payload.publish, user_id=ctx.user.id
    )
    record_audit(
        db,
        action="consent.notice_created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="consent_notice",
        entity_id=notice.id,
        metadata={"version": notice.version, "published": payload.publish},
    )
    db.commit()
    db.refresh(notice)
    return _notice_out(notice)


@router.post("/notices/{notice_id}/publish", response_model=NoticeOut)
def publish_notice(
    notice_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_CONSENT)),
    db: Session = Depends(get_db),
) -> NoticeOut:
    notice = consent_service.publish_notice(db, ctx.organization_id, notice_id, user_id=ctx.user.id)
    record_audit(
        db,
        action="consent.notice_published",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="consent_notice",
        entity_id=notice.id,
        metadata={"version": notice.version},
    )
    db.commit()
    db.refresh(notice)
    return _notice_out(notice)


# --------------------------------------------------------------------------- #
# Records + ledger + summary
# --------------------------------------------------------------------------- #
@router.get("/summary")
def consent_summary(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    return consent_service.summary(db, ctx.organization_id)


@router.get("/records", response_model=list[RecordOut])
def list_records(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    purpose_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
) -> list[RecordOut]:
    return [
        _record_out(r)
        for r in consent_service.list_records(db, ctx.organization_id, purpose_id=purpose_id, status=status)
    ]


@router.get("/events", response_model=list[EventOut])
def list_events(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    principal: str | None = Query(None),
    purpose_id: uuid.UUID | None = Query(None),
) -> list[EventOut]:
    return [
        _event_out(e)
        for e in consent_service.list_events(db, ctx.organization_id, principal=principal, purpose_id=purpose_id)
    ]


@router.post("/grant", response_model=RecordOut)
def staff_grant(
    payload: ConsentActionIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_CONSENT)),
    db: Session = Depends(get_db),
) -> RecordOut:
    record = consent_service.record_consent(
        db,
        ctx.organization_id,
        purpose_id=payload.purpose_id,
        principal=payload.principal_identifier,
        method=ConsentMethod.STAFF_RECORDED.value,
        source="STAFF",
        actor=str(ctx.user.id),
        verified=True,
    )
    record_audit(
        db,
        action="consent.granted",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="consent_record",
        entity_id=record.id,
    )
    db.commit()
    db.refresh(record)
    return _record_out(record)


@router.post("/withdraw", response_model=RecordOut)
def staff_withdraw(
    payload: ConsentActionIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_CONSENT)),
    db: Session = Depends(get_db),
) -> RecordOut:
    record = consent_service.withdraw_consent(
        db,
        ctx.organization_id,
        purpose_id=payload.purpose_id,
        principal=payload.principal_identifier,
        method=ConsentMethod.STAFF_RECORDED.value,
        source="STAFF",
        actor=str(ctx.user.id),
    )
    record_audit(
        db,
        action="consent.withdrawn",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="consent_record",
        entity_id=record.id,
    )
    db.commit()
    db.refresh(record)
    return _record_out(record)
