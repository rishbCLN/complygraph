"""SSO endpoints (feature #10): OIDC and SAML login.

These endpoints are PUBLIC (no session required) because they *establish* a
session. When a provider is not configured its login endpoint returns 404 so the
login page simply omits the button.

Flow summary
------------
OIDC:  GET /sso/oidc/login    -> 302 to IdP (sets signed state cookie)
       GET /sso/oidc/callback -> verify code+id_token, set session, 302 to app
SAML:  GET /sso/saml/login    -> 302 to IdP (AuthnRequest)
       POST /sso/saml/acs      -> verify signed assertion, set session, 302 to app
       GET /sso/saml/metadata -> SP metadata XML
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.security.tokens import SESSION_COOKIE_NAME
from app.services import auth_service, sso_service

router = APIRouter(prefix="/sso", tags=["sso"])

_OIDC_STATE_COOKIE = "cg_oidc_state"


class SSOProviderOut(BaseModel):
    protocol: str
    name: str
    login_url: str


class SSOProvidersResponse(BaseModel):
    providers: list[SSOProviderOut]


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


def _establish_and_redirect(db: Session, user, request: Request) -> RedirectResponse:
    token = auth_service.create_session(db, user)
    membership = auth_service.primary_membership(db, user)
    record_audit(
        db,
        action="auth.sso_login",
        organization_id=membership.organization_id,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    redirect = RedirectResponse(url=settings.sso_post_login_redirect, status_code=302)
    _set_session_cookie(redirect, token)
    return redirect


# --------------------------------------------------------------------------- #
# Discovery for the login page
# --------------------------------------------------------------------------- #
@router.get("/providers", response_model=SSOProvidersResponse)
def sso_providers() -> SSOProvidersResponse:
    """List enabled SSO providers so the login page can render buttons."""
    providers: list[SSOProviderOut] = []
    prefix = settings.api_v1_prefix
    if settings.oidc_configured:
        providers.append(
            SSOProviderOut(
                protocol="OIDC",
                name=settings.oidc_provider_name,
                login_url=f"{prefix}/sso/oidc/login",
            )
        )
    if settings.saml_configured:
        providers.append(
            SSOProviderOut(
                protocol="SAML",
                name=settings.saml_provider_name,
                login_url=f"{prefix}/sso/saml/login",
            )
        )
    return SSOProvidersResponse(providers=providers)


# --------------------------------------------------------------------------- #
# OIDC
# --------------------------------------------------------------------------- #
@router.get("/oidc/login")
def oidc_login() -> RedirectResponse:
    if not settings.oidc_configured:
        raise NotFoundError("OIDC SSO is not enabled.")
    import secrets

    nonce = secrets.token_urlsafe(16)
    state_token = sso_service.make_state_token(nonce)
    auth_url = sso_service.oidc_authorization_url(state_token, nonce)
    redirect = RedirectResponse(url=auth_url, status_code=302)
    # Carry state in a short-lived HTTP-only cookie (stateless flow).
    redirect.set_cookie(
        key=_OIDC_STATE_COOKIE,
        value=state_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=600,
        path="/",
    )
    return redirect


@router.get("/oidc/callback")
def oidc_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if not settings.oidc_configured:
        raise NotFoundError("OIDC SSO is not enabled.")
    if error:
        raise sso_service.SSOError(f"OIDC provider returned an error: {error}")
    if not code or not state:
        raise sso_service.SSOError("Missing code or state in OIDC callback.")

    cookie_state = request.cookies.get(_OIDC_STATE_COOKIE)
    if not cookie_state or cookie_state != state:
        raise sso_service.SSOError("OIDC state mismatch (possible CSRF).")
    nonce = sso_service.read_state_token(state)

    identity = sso_service.oidc_exchange_and_verify(code, nonce)
    user = sso_service.resolve_user(db, identity)
    response = _establish_and_redirect(db, user, request)
    response.delete_cookie(_OIDC_STATE_COOKIE, path="/")
    return response


# --------------------------------------------------------------------------- #
# SAML
# --------------------------------------------------------------------------- #
@router.get("/saml/metadata")
def saml_metadata() -> Response:
    if not (settings.saml_sp_entity_id and settings.saml_sp_acs_url):
        raise NotFoundError("SAML SP is not configured.")
    return Response(content=sso_service.saml_metadata_xml(), media_type="application/xml")


@router.get("/saml/login")
def saml_login() -> RedirectResponse:
    if not settings.saml_configured:
        raise NotFoundError("SAML SSO is not enabled.")
    return RedirectResponse(url=sso_service.saml_redirect_url(), status_code=302)


@router.post("/saml/acs")
def saml_acs(
    request: Request,
    SAMLResponse: str = Form(...),
    RelayState: str | None = Form(None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Assertion Consumer Service: verify the signed SAMLResponse and log in."""
    if not settings.saml_configured:
        raise NotFoundError("SAML SSO is not enabled.")
    identity = sso_service.parse_and_verify_saml_response(SAMLResponse)
    user = sso_service.resolve_user(db, identity)
    return _establish_and_redirect(db, user, request)
