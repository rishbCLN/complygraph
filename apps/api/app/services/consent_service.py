"""Consent management service (feature #8).

Handles the purpose catalogue, versioned notices, and the consent ledger. The
ledger (ConsentEvent) is append-only and is the audit source of truth; every
grant/withdrawal writes a ledger row and upserts the materialised ConsentRecord
current-state row in the same transaction.

Nothing here decides compliance status - it records the data principal's
affirmative acts deterministically.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.enums import (
    ConsentEventType,
    ConsentMethod,
    ConsentStatus,
    PurposeStatus,
)
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.consent import (
    ConsentEvent,
    ConsentNotice,
    ConsentPurpose,
    ConsentRecord,
)

_VALID_METHODS = {m.value for m in ConsentMethod}


# --------------------------------------------------------------------------- #
# Purpose catalogue
# --------------------------------------------------------------------------- #
def list_purposes(db: Session, org_id: uuid.UUID, *, active_only: bool = False) -> list[ConsentPurpose]:
    stmt = select(ConsentPurpose).where(ConsentPurpose.organization_id == org_id)
    if active_only:
        stmt = stmt.where(ConsentPurpose.status == PurposeStatus.ACTIVE.value)
    stmt = stmt.order_by(ConsentPurpose.display_order, ConsentPurpose.name)
    return list(db.scalars(stmt))


def get_purpose(db: Session, org_id: uuid.UUID, purpose_id: uuid.UUID) -> ConsentPurpose:
    p = db.get(ConsentPurpose, purpose_id)
    if p is None or p.organization_id != org_id:
        raise NotFoundError("Consent purpose not found.")
    return p


def create_purpose(db: Session, org_id: uuid.UUID, data: dict) -> ConsentPurpose:
    code = (data.get("code") or "").strip()
    if not code:
        raise ValidationError("A stable purpose code is required.")
    existing = db.scalar(
        select(ConsentPurpose).where(
            ConsentPurpose.organization_id == org_id, ConsentPurpose.code == code
        )
    )
    if existing is not None:
        raise ConflictError(f"A purpose with code '{code}' already exists.")
    purpose = ConsentPurpose(
        organization_id=org_id,
        code=code,
        name=data["name"],
        description=data.get("description"),
        lawful_basis=data.get("lawful_basis") or "Consent",
        requires_consent=data.get("requires_consent", True),
        is_sensitive=data.get("is_sensitive", False),
        default_expiry_days=data.get("default_expiry_days"),
        display_order=data.get("display_order", 100),
        processing_activity_id=data.get("processing_activity_id"),
        status=PurposeStatus.ACTIVE.value,
    )
    db.add(purpose)
    db.flush()
    return purpose


def update_purpose(db: Session, org_id: uuid.UUID, purpose_id: uuid.UUID, data: dict) -> ConsentPurpose:
    purpose = get_purpose(db, org_id, purpose_id)
    for key in (
        "name",
        "description",
        "lawful_basis",
        "requires_consent",
        "is_sensitive",
        "default_expiry_days",
        "display_order",
        "processing_activity_id",
        "status",
    ):
        if key in data and data[key] is not None:
            setattr(purpose, key, data[key])
    db.flush()
    return purpose


def archive_purpose(db: Session, org_id: uuid.UUID, purpose_id: uuid.UUID) -> ConsentPurpose:
    purpose = get_purpose(db, org_id, purpose_id)
    purpose.status = PurposeStatus.ARCHIVED.value
    db.flush()
    return purpose


# --------------------------------------------------------------------------- #
# Notices (versioned)
# --------------------------------------------------------------------------- #
def list_notices(db: Session, org_id: uuid.UUID) -> list[ConsentNotice]:
    return list(
        db.scalars(
            select(ConsentNotice)
            .where(ConsentNotice.organization_id == org_id)
            .order_by(ConsentNotice.version.desc())
        )
    )


def current_notice(db: Session, org_id: uuid.UUID) -> ConsentNotice | None:
    return db.scalar(
        select(ConsentNotice).where(
            ConsentNotice.organization_id == org_id, ConsentNotice.is_current.is_(True)
        )
    )


def create_notice(
    db: Session, org_id: uuid.UUID, data: dict, *, publish: bool = False, user_id: uuid.UUID | None = None
) -> ConsentNotice:
    max_version = db.scalar(
        select(func.max(ConsentNotice.version)).where(ConsentNotice.organization_id == org_id)
    )
    notice = ConsentNotice(
        organization_id=org_id,
        version=(max_version or 0) + 1,
        title=data["title"],
        body=data["body"],
        is_current=False,
    )
    db.add(notice)
    db.flush()
    if publish:
        publish_notice(db, org_id, notice.id, user_id=user_id)
    return notice


def publish_notice(
    db: Session, org_id: uuid.UUID, notice_id: uuid.UUID, *, user_id: uuid.UUID | None = None
) -> ConsentNotice:
    notice = db.get(ConsentNotice, notice_id)
    if notice is None or notice.organization_id != org_id:
        raise NotFoundError("Notice version not found.")
    # Demote any currently-published version.
    for other in db.scalars(
        select(ConsentNotice).where(
            ConsentNotice.organization_id == org_id, ConsentNotice.is_current.is_(True)
        )
    ):
        other.is_current = False
    notice.is_current = True
    notice.published_at = utcnow()
    notice.published_by = user_id
    db.flush()
    return notice


# --------------------------------------------------------------------------- #
# Consent ledger
# --------------------------------------------------------------------------- #
def _get_record(db: Session, purpose_id: uuid.UUID, principal: str) -> ConsentRecord | None:
    return db.scalar(
        select(ConsentRecord).where(
            ConsentRecord.purpose_id == purpose_id,
            ConsentRecord.principal_identifier == principal,
        )
    )


def _append_event(
    db: Session,
    *,
    org_id: uuid.UUID,
    purpose: ConsentPurpose,
    principal: str,
    event_type: str,
    method: str,
    source: str,
    notice_version: int | None,
    actor: str | None,
    detail: str | None,
) -> ConsentEvent:
    event = ConsentEvent(
        organization_id=org_id,
        purpose_id=purpose.id,
        purpose_code=purpose.code,
        purpose_name=purpose.name,
        principal_identifier=principal,
        event_type=event_type,
        method=method,
        source=source,
        notice_version=notice_version,
        actor=actor,
        detail=detail,
        created_at=utcnow(),
    )
    db.add(event)
    return event


def record_consent(
    db: Session,
    org_id: uuid.UUID,
    *,
    purpose_id: uuid.UUID,
    principal: str,
    method: str = ConsentMethod.PRIVACY_CENTER.value,
    source: str = "PRIVACY_CENTER",
    actor: str | None = None,
    verified: bool = False,
) -> ConsentRecord:
    """Grant (or renew) consent for one purpose. Writes ledger + upserts record."""
    principal = (principal or "").strip().lower()
    if not principal:
        raise ValidationError("A data principal identifier is required.")
    purpose = get_purpose(db, org_id, purpose_id)
    if purpose.status != PurposeStatus.ACTIVE.value:
        raise ValidationError("Consent cannot be recorded against an archived purpose.")
    if not purpose.requires_consent:
        raise ValidationError(
            f"Purpose '{purpose.name}' does not rely on consent (lawful basis: {purpose.lawful_basis})."
        )
    if method not in _VALID_METHODS:
        raise ValidationError(f"Unknown consent method '{method}'.")

    now = utcnow()
    notice = current_notice(db, org_id)
    notice_version = notice.version if notice else None
    expires_at = (
        now + timedelta(days=purpose.default_expiry_days) if purpose.default_expiry_days else None
    )

    record = _get_record(db, purpose_id, principal)
    is_renewal = record is not None and record.status == ConsentStatus.GRANTED.value
    if record is None:
        record = ConsentRecord(
            organization_id=org_id,
            purpose_id=purpose_id,
            principal_identifier=principal,
        )
        db.add(record)
    record.status = ConsentStatus.GRANTED.value
    record.method = method
    record.notice_version = notice_version
    record.granted_at = now
    record.withdrawn_at = None
    record.expires_at = expires_at
    record.verified = verified

    _append_event(
        db,
        org_id=org_id,
        purpose=purpose,
        principal=principal,
        event_type=ConsentEventType.RENEWED.value if is_renewal else ConsentEventType.GRANTED.value,
        method=method,
        source=source,
        notice_version=notice_version,
        actor=actor,
        detail=None,
    )
    db.flush()
    return record


def withdraw_consent(
    db: Session,
    org_id: uuid.UUID,
    *,
    purpose_id: uuid.UUID,
    principal: str,
    method: str = ConsentMethod.PRIVACY_CENTER.value,
    source: str = "PRIVACY_CENTER",
    actor: str | None = None,
) -> ConsentRecord:
    """Withdraw consent. DPDP: withdrawal must be as easy as granting."""
    principal = (principal or "").strip().lower()
    if not principal:
        raise ValidationError("A data principal identifier is required.")
    purpose = get_purpose(db, org_id, purpose_id)
    if method not in _VALID_METHODS:
        raise ValidationError(f"Unknown consent method '{method}'.")

    now = utcnow()
    record = _get_record(db, purpose_id, principal)
    if record is None:
        # Withdrawal with no prior grant: still record it (idempotent, honours intent).
        record = ConsentRecord(
            organization_id=org_id,
            purpose_id=purpose_id,
            principal_identifier=principal,
        )
        db.add(record)
    record.status = ConsentStatus.WITHDRAWN.value
    record.method = method
    record.withdrawn_at = now

    _append_event(
        db,
        org_id=org_id,
        purpose=purpose,
        principal=principal,
        event_type=ConsentEventType.WITHDRAWN.value,
        method=method,
        source=source,
        notice_version=record.notice_version,
        actor=actor,
        detail=None,
    )
    db.flush()
    return record


def principal_consents(db: Session, org_id: uuid.UUID, principal: str) -> list[ConsentRecord]:
    principal = (principal or "").strip().lower()
    return list(
        db.scalars(
            select(ConsentRecord).where(
                ConsentRecord.organization_id == org_id,
                ConsentRecord.principal_identifier == principal,
            )
        )
    )


def list_records(
    db: Session, org_id: uuid.UUID, *, purpose_id: uuid.UUID | None = None, status: str | None = None
) -> list[ConsentRecord]:
    stmt = select(ConsentRecord).where(ConsentRecord.organization_id == org_id)
    if purpose_id:
        stmt = stmt.where(ConsentRecord.purpose_id == purpose_id)
    if status:
        stmt = stmt.where(ConsentRecord.status == status)
    stmt = stmt.order_by(ConsentRecord.updated_at.desc())
    return list(db.scalars(stmt))


def list_events(
    db: Session,
    org_id: uuid.UUID,
    *,
    principal: str | None = None,
    purpose_id: uuid.UUID | None = None,
    limit: int = 200,
) -> list[ConsentEvent]:
    stmt = select(ConsentEvent).where(ConsentEvent.organization_id == org_id)
    if principal:
        stmt = stmt.where(ConsentEvent.principal_identifier == principal.strip().lower())
    if purpose_id:
        stmt = stmt.where(ConsentEvent.purpose_id == purpose_id)
    stmt = stmt.order_by(ConsentEvent.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))


def summary(db: Session, org_id: uuid.UUID) -> dict:
    """Per-purpose grant/withdraw tallies for the staff dashboard."""
    purposes = list_purposes(db, org_id)
    records = list_records(db, org_id)
    by_purpose: dict[uuid.UUID, dict] = {}
    for p in purposes:
        by_purpose[p.id] = {
            "purpose_id": str(p.id),
            "code": p.code,
            "name": p.name,
            "requires_consent": p.requires_consent,
            "granted": 0,
            "withdrawn": 0,
            "expired": 0,
        }
    total_granted = 0
    total_withdrawn = 0
    for r in records:
        bucket = by_purpose.get(r.purpose_id)
        if bucket is None:
            continue
        if r.status == ConsentStatus.GRANTED.value:
            bucket["granted"] += 1
            total_granted += 1
        elif r.status == ConsentStatus.WITHDRAWN.value:
            bucket["withdrawn"] += 1
            total_withdrawn += 1
        elif r.status == ConsentStatus.EXPIRED.value:
            bucket["expired"] += 1

    notice = current_notice(db, org_id)
    return {
        "purposes_total": len(purposes),
        "active_purposes": sum(1 for p in purposes if p.status == PurposeStatus.ACTIVE.value),
        "total_granted": total_granted,
        "total_withdrawn": total_withdrawn,
        "distinct_principals": len({r.principal_identifier for r in records}),
        "current_notice_version": notice.version if notice else None,
        "by_purpose": list(by_purpose.values()),
    }
