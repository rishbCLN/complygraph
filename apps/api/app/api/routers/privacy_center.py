"""Public Privacy Center portal (feature #8, data-principal side).

This is the ONLY unauthenticated, tenant-scoped surface in the API. A data
principal reaches it via their organisation's slug (e.g. the org publishes a
link to /privacy/<slug>). It lets a principal:

  * read the organisation's current privacy notice and purpose catalogue
    (public, transparency-by-design);
  * submit a data-subject request (access/correction/erasure/grievance);
  * grant or withdraw consent for a purpose.

SECURITY POSTURE
----------------
Identity here is self-asserted: the principal supplies an email/identifier but
there is no strong verification (no OTP/magic-link infrastructure exists yet).
To avoid abuse we therefore:

  * NEVER expose any principal's existing consent state or DSR history through
    this surface - it is write-and-notice-read only. (Reading another person's
    consent by guessing their email would be an information-disclosure hole.)
  * record every consent action as source=PRIVACY_CENTER and verified=False so
    staff can see it is self-asserted and confirm out-of-band;
  * create DSRs in the REQUESTED/PENDING-verification state exactly like the
    staff intake path, so identity is verified before anything is fulfilled;
  * apply a per-identifier in-memory rate limit to blunt scripted abuse.

Production hardening (documented, not built here): put email OTP / magic-link
verification in front of the write actions, and add a CAPTCHA + edge rate limit.
"""

from __future__ import annotations

import time
from datetime import timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, utcnow
from app.core.enums import DSRStatus, DSRType
from app.core.errors import NotFoundError, RateLimitError, ValidationError
from app.models.consent import ConsentPurpose
from app.models.identity import Organization
from app.models.operations import DataSubjectRequest
from app.services import consent_service

router = APIRouter(prefix="/privacy", tags=["privacy-center"])

# Per-(slug, identifier) sliding-window write throttle.
_write_attempts: dict[str, list[float]] = {}


def _rate_limit(key: str) -> None:
    window = settings.privacy_center_rate_limit_window_seconds
    limit = settings.privacy_center_rate_limit_attempts
    now = time.monotonic()
    attempts = [t for t in _write_attempts.get(key, []) if now - t < window]
    if len(attempts) >= limit:
        raise RateLimitError("Too many requests. Please wait a few minutes and try again.")
    attempts.append(now)
    _write_attempts[key] = attempts


def _resolve_org(db: Session, slug: str) -> Organization:
    if not settings.privacy_center_enabled:
        raise NotFoundError("Privacy Center is not available.")
    org = db.scalar(select(Organization).where(Organization.slug == slug))
    if org is None:
        raise NotFoundError("Privacy Center not found for this organisation.")
    return org


# --------------------------------------------------------------------------- #
# Schemas (deliberately minimal; no consent-state readback)
# --------------------------------------------------------------------------- #
class PortalPurpose(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    lawful_basis: str
    requires_consent: bool
    is_sensitive: bool


class PortalNotice(BaseModel):
    version: int
    title: str
    body: str
    published_at: str | None


class PortalInfo(BaseModel):
    organization: str
    notice: PortalNotice | None
    purposes: list[PortalPurpose]
    request_types: list[str]


class ConsentSubmit(BaseModel):
    principal_identifier: str
    purpose_id: str
    action: str  # "grant" | "withdraw"


class DSRSubmit(BaseModel):
    principal_identifier: str
    request_type: str
    notes: str | None = None


class SubmitResult(BaseModel):
    ok: bool
    message: str
    reference: str | None = None


# --------------------------------------------------------------------------- #
# Public read: notice + purposes
# --------------------------------------------------------------------------- #
@router.get("/{slug}", response_model=PortalInfo)
def portal_info(slug: str, db: Session = Depends(get_db)) -> PortalInfo:
    org = _resolve_org(db, slug)
    notice = consent_service.current_notice(db, org.id)
    purposes = consent_service.list_purposes(db, org.id, active_only=True)
    return PortalInfo(
        organization=org.name,
        notice=(
            PortalNotice(
                version=notice.version,
                title=notice.title,
                body=notice.body,
                published_at=notice.published_at.isoformat() if notice.published_at else None,
            )
            if notice
            else None
        ),
        purposes=[
            PortalPurpose(
                id=str(p.id),
                code=p.code,
                name=p.name,
                description=p.description,
                lawful_basis=p.lawful_basis,
                requires_consent=p.requires_consent,
                is_sensitive=p.is_sensitive,
            )
            for p in purposes
        ],
        request_types=[t.value for t in DSRType],
    )


# --------------------------------------------------------------------------- #
# Public write: consent grant / withdraw
# --------------------------------------------------------------------------- #
@router.post("/{slug}/consent", response_model=SubmitResult)
def submit_consent(slug: str, payload: ConsentSubmit, db: Session = Depends(get_db)) -> SubmitResult:
    org = _resolve_org(db, slug)
    principal = (payload.principal_identifier or "").strip().lower()
    if not principal:
        raise ValidationError("Please provide the identifier the organisation holds for you.")
    _rate_limit(f"{slug}:{principal}")

    try:
        purpose_uuid = _parse_uuid(payload.purpose_id)
    except ValueError:
        raise ValidationError("Invalid purpose.") from None

    # Ensure the purpose belongs to this org (avoids cross-tenant references).
    purpose = db.get(ConsentPurpose, purpose_uuid)
    if purpose is None or purpose.organization_id != org.id:
        raise NotFoundError("Purpose not found.")

    action = payload.action.strip().lower()
    if action == "grant":
        consent_service.record_consent(
            db, org.id, purpose_id=purpose_uuid, principal=principal, source="PRIVACY_CENTER", verified=False
        )
        msg = f"Your consent for '{purpose.name}' has been recorded."
    elif action == "withdraw":
        consent_service.withdraw_consent(
            db, org.id, purpose_id=purpose_uuid, principal=principal, source="PRIVACY_CENTER"
        )
        msg = f"Your consent for '{purpose.name}' has been withdrawn."
    else:
        raise ValidationError("Action must be 'grant' or 'withdraw'.")

    db.commit()
    return SubmitResult(ok=True, message=msg)


# --------------------------------------------------------------------------- #
# Public write: data-subject request intake
# --------------------------------------------------------------------------- #
@router.post("/{slug}/requests", response_model=SubmitResult)
def submit_request(slug: str, payload: DSRSubmit, db: Session = Depends(get_db)) -> SubmitResult:
    org = _resolve_org(db, slug)
    principal = (payload.principal_identifier or "").strip().lower()
    if not principal:
        raise ValidationError("Please provide a contact identifier so we can respond.")
    if payload.request_type not in {t.value for t in DSRType}:
        raise ValidationError(f"Unsupported request type: {payload.request_type}")
    _rate_limit(f"{slug}:{principal}")

    req = DataSubjectRequest(
        organization_id=org.id,
        requester_identifier=principal,
        request_type=payload.request_type,
        status=DSRStatus.REQUESTED.value,
        verification_status="PENDING",
        received_at=utcnow(),
        due_at=utcnow() + timedelta(days=30),
        notes=(payload.notes or None),
    )
    db.add(req)
    db.flush()
    reference = str(req.id)
    db.commit()
    return SubmitResult(
        ok=True,
        message=(
            "Your request has been received. We will verify your identity and respond within the "
            "statutory timeframe."
        ),
        reference=reference,
    )


def _parse_uuid(value: str):
    import uuid

    return uuid.UUID(value)
