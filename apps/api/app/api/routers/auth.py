"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context
from app.core.audit import record_audit
from app.core.config import settings
from app.core.database import get_db
from app.core.rbac import ROLE_CAPABILITIES
from app.security.tokens import SESSION_COOKIE_NAME
from app.services import auth_service

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


@router.post("/login", response_model=MeResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> MeResponse:
    """Authenticate with email + password and start an HTTP-only cookie session."""
    user = auth_service.authenticate(db, payload.email, payload.password)
    token = auth_service.create_session(db, user)
    membership = auth_service.primary_membership(db, user)
    org = auth_service.get_organization(db, membership.organization_id)
    record_audit(
        db,
        action="auth.login",
        organization_id=org.id if org else None,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    _set_session_cookie(response, token)
    return MeResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        capabilities=sorted(ROLE_CAPABILITIES.get(membership.role, set())),
        organization=OrgSummary(
            id=str(org.id), name=org.name, slug=org.slug, role=membership.role
        ),
    )


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
