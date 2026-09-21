"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context
from app.core.audit import record_audit
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AuthError
from app.core.rbac import ROLE_CAPABILITIES
from app.models.identity import User
from app.security.tokens import SESSION_COOKIE_NAME
from app.services import auth_service, mfa_service

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=10)


class OrgSummary(BaseModel):
    id: str
    name: str
    slug: str
    role: str


class MeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    capabilities: list[str]
    organization: OrgSummary
    mfa_enabled: bool = False


class MfaChallengeResponse(BaseModel):
    """Returned by ``/auth/login`` when the account has MFA enabled.

    No session is created; the caller must complete ``POST /auth/mfa/login``
    with the ``mfa_token`` and a current code.
    """

    mfa_required: bool = True
    mfa_token: str


class MfaLoginRequest(BaseModel):
    mfa_token: str = Field(min_length=1)
    code: str = Field(min_length=1)


class MfaActivateRequest(BaseModel):
    code: str = Field(min_length=1)


class MfaDisableRequest(BaseModel):
    password: str = Field(min_length=1)


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


def _build_me(db: Session, user: User) -> MeResponse:
    membership = auth_service.primary_membership(db, user)
    org = auth_service.get_organization(db, membership.organization_id)
    return MeResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        capabilities=sorted(ROLE_CAPABILITIES.get(membership.role, set())),
        organization=OrgSummary(
            id=str(org.id), name=org.name, slug=org.slug, role=membership.role
        ),
        mfa_enabled=user.mfa_enabled,
    )


def _establish_session(
    db: Session, user: User, request: Request, response: Response
) -> MeResponse:
    token = auth_service.create_session(db, user)
    me = _build_me(db, user)
    record_audit(
        db,
        action="auth.login",
        organization_id=user.memberships[0].organization_id if user.memberships else None,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    _set_session_cookie(response, token)
    return me


@router.post("/login", response_model=None)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> MeResponse | MfaChallengeResponse:
    """Authenticate with email + password.

    Starts a session immediately (returning the user payload) unless the account
    has MFA enabled, in which case a short-lived challenge token is returned and
    the caller must complete ``POST /auth/mfa/login``.
    """
    user = auth_service.authenticate(db, payload.email, payload.password)
    if user.mfa_enabled:
        token = mfa_service.issue_challenge(user)
        return MfaChallengeResponse(mfa_token=token)
    return _establish_session(db, user, request, response)


@router.post("/mfa/login", response_model=MeResponse)
def mfa_login(
    payload: MfaLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> MeResponse:
    """Complete an MFA-gated login with a TOTP or backup code."""
    user_id = mfa_service.decode_challenge(payload.mfa_token)
    user = db.get(User, user_id)
    if not user or not user.is_active or not user.mfa_enabled:
        raise AuthError("Invalid MFA challenge.")
    if not mfa_service.verify_second_factor(user, payload.code):
        raise AuthError("That code is incorrect.")
    me = _establish_session(db, user, request, response)
    return me


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    """Revoke the current session and clear the cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        auth_service.revoke_session(db, token)
        db.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"message": "Logged out."}


@router.get("/me", response_model=MeResponse)
def me(ctx: AuthContext = Depends(get_current_context)) -> MeResponse:
    """Return the authenticated user and active organization."""
    return MeResponse(
        id=str(ctx.user.id),
        email=ctx.user.email,
        full_name=ctx.user.full_name,
        role=ctx.role,
        capabilities=sorted(ROLE_CAPABILITIES.get(ctx.role, set())),
        organization=OrgSummary(
            id=str(ctx.organization.id),
            name=ctx.organization.name,
            slug=ctx.organization.slug,
            role=ctx.role,
        ),
        mfa_enabled=ctx.user.mfa_enabled,
    )


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    """Change the current user's password and revoke other sessions."""
    auth_service.change_password(db, ctx.user, payload.current_password, payload.new_password)
    record_audit(
        db,
        action="auth.password_changed",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="user",
        entity_id=ctx.user.id,
    )
    db.commit()
    return {"message": "Password changed. Please log in again on other devices."}


# --------------------------------------------------------------------------- #
# MFA (TOTP) enrolment management for the current user.
# --------------------------------------------------------------------------- #
class MfaStatusResponse(BaseModel):
    available: bool  # deployment allows MFA enrolment
    enabled: bool  # this user has MFA active
    issuer: str


class MfaEnrollResponse(BaseModel):
    secret: str
    otpauth_uri: str


class MfaCodesResponse(BaseModel):
    backup_codes: list[str]


@router.get("/mfa", response_model=MfaStatusResponse)
def mfa_status(ctx: AuthContext = Depends(get_current_context)) -> MfaStatusResponse:
    return MfaStatusResponse(
        available=settings.mfa_enabled,
        enabled=ctx.user.mfa_enabled,
        issuer=settings.mfa_issuer_name,
    )


@router.post("/mfa/enroll", response_model=MfaEnrollResponse)
def mfa_enroll(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> MfaEnrollResponse:
    """Begin TOTP enrolment: returns a secret + otpauth URI (not yet active)."""
    start = mfa_service.begin_enrollment(ctx.user)
    db.commit()
    return MfaEnrollResponse(secret=start.secret, otpauth_uri=start.otpauth_uri)


@router.post("/mfa/activate", response_model=MfaCodesResponse)
def mfa_activate(
    payload: MfaActivateRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> MfaCodesResponse:
    """Verify the first code, enable MFA, and return one-time backup codes."""
    codes = mfa_service.activate(ctx.user, payload.code)
    record_audit(
        db,
        action="auth.mfa_enabled",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="user",
        entity_id=ctx.user.id,
    )
    db.commit()
    return MfaCodesResponse(backup_codes=codes)


@router.post("/mfa/backup-codes", response_model=MfaCodesResponse)
def mfa_regenerate_backup_codes(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> MfaCodesResponse:
    """Regenerate backup codes, invalidating any previously issued set."""
    codes = mfa_service.regenerate_backup_codes(ctx.user)
    db.commit()
    return MfaCodesResponse(backup_codes=codes)


@router.post("/mfa/disable")
def mfa_disable(
    payload: MfaDisableRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    """Disable MFA after re-verifying the account password."""
    mfa_service.disable(ctx.user, payload.password)
    record_audit(
        db,
        action="auth.mfa_disabled",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="user",
        entity_id=ctx.user.id,
    )
    db.commit()
    return {"message": "MFA disabled."}
