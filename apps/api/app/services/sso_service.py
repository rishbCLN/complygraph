"""Single Sign-On service (feature #10): OIDC and SAML 2.0.

Both protocols are DORMANT until their environment configuration is present
(``settings.oidc_configured`` / ``settings.saml_configured``). Nothing here runs
unless an administrator has wired up an identity provider.

Design notes
------------
* **OIDC** uses the Authorization Code flow. We fetch the provider's discovery
  document, redirect the browser to the authorization endpoint with ``state`` +
  ``nonce`` (carried in a signed, short-lived cookie so the flow is stateless),
  then exchange the code for tokens at the callback and verify the ``id_token``
  signature against the provider JWKS with ``PyJWKClient`` (issuer + audience +
  nonce all checked).
* **SAML** uses SP-initiated SSO. We build a deflated ``AuthnRequest`` for the
  HTTP-Redirect binding, and at the ACS endpoint verify the IdP's XML-DSig
  signature with ``signxml`` against the configured IdP certificate, then check
  the assertion Conditions (audience + notBefore/notOnOrAfter) before trusting
  the NameID/attributes.

User resolution is deliberately conservative: an authenticated federated
identity is matched to an existing user by verified email. Auto-provisioning is
OFF unless explicitly enabled (``sso_auto_provision``).
"""

from __future__ import annotations

import base64
import secrets
import uuid
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import utcnow
from app.core.errors import AppError, AuthError
from app.models.identity import Membership, Organization, User

_STATE_PURPOSE_OIDC = "oidc_state"
_STATE_TTL_SECONDS = 600


class SSOError(AppError):
    status_code = 400


@dataclass
class FederatedIdentity:
    email: str
    display_name: str | None = None


# --------------------------------------------------------------------------- #
# Shared: resolve a federated identity to a local session-eligible user
# --------------------------------------------------------------------------- #
def resolve_user(db: Session, identity: FederatedIdentity) -> User:
    email = (identity.email or "").strip().lower()
    if not email:
        raise AuthError("The identity provider did not return an email address.")
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        if not user.is_active:
            raise AuthError("User account is inactive.")
        return user
    if not settings.sso_auto_provision:
        raise AuthError(
            "No ComplyGraph account exists for this identity. Contact your administrator."
        )
    return _auto_provision(db, email, identity.display_name or email)


def _auto_provision(db: Session, email: str, display_name: str) -> User:
    from app.security.passwords import hash_password

    org = _target_org(db)
    if org is None:
        raise SSOError("Auto-provisioning is enabled but no target organization exists.")
    user = User(
        email=email,
        full_name=display_name,
        # Unusable random password; SSO users authenticate via the IdP.
        password_hash=hash_password(secrets.token_urlsafe(32)),
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(
        Membership(
            organization_id=org.id,
            user_id=user.id,
            role=settings.sso_auto_provision_role,
            created_at=utcnow(),
        )
    )
    db.flush()
    return user


def _target_org(db: Session) -> Organization | None:
    if settings.sso_default_org_slug.strip():
        return db.scalar(
            select(Organization).where(Organization.slug == settings.sso_default_org_slug.strip())
        )
    return db.scalar(select(Organization).order_by(Organization.created_at.asc()))


# --------------------------------------------------------------------------- #
# OIDC
# --------------------------------------------------------------------------- #
def _discovery() -> dict:
    url = settings.oidc_issuer.rstrip("/") + "/.well-known/openid-configuration"
    try:
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise SSOError(f"Could not fetch OIDC discovery document: {exc}") from exc
    return resp.json()


def make_state_token(nonce: str) -> str:
    now = utcnow()
    payload = {
        "purpose": _STATE_PURPOSE_OIDC,
        "nonce": nonce,
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + _STATE_TTL_SECONDS,
        "jti": secrets.token_urlsafe(8),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def read_state_token(token: str) -> str:
    """Return the nonce carried by a state token, or raise."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise AuthError("Invalid or expired SSO state.") from None
    if payload.get("purpose") != _STATE_PURPOSE_OIDC:
        raise AuthError("Invalid SSO state.")
    return payload["nonce"]


def oidc_authorization_url(state_token: str, nonce: str) -> str:
    if not settings.oidc_configured:
        raise SSOError("OIDC is not configured for this deployment.")
    disco = _discovery()
    params = {
        "response_type": "code",
        "client_id": settings.oidc_client_id,
        "redirect_uri": settings.oidc_redirect_url,
        "scope": settings.oidc_scopes,
        "state": state_token,
        "nonce": nonce,
    }
    return f"{disco['authorization_endpoint']}?{urlencode(params)}"


def oidc_exchange_and_verify(code: str, nonce: str) -> FederatedIdentity:
    """Exchange an auth code for tokens and verify the id_token."""
    if not settings.oidc_configured:
        raise SSOError("OIDC is not configured for this deployment.")
    disco = _discovery()
    # 1. Exchange the code for tokens.
    try:
        token_resp = httpx.post(
            disco["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.oidc_redirect_url,
                "client_id": settings.oidc_client_id,
                "client_secret": settings.oidc_client_secret,
            },
            headers={"Accept": "application/json"},
            timeout=10.0,
        )
        token_resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise AuthError(f"OIDC token exchange failed: {exc}") from exc
    tokens = token_resp.json()
    id_token = tokens.get("id_token")
    if not id_token:
        raise AuthError("OIDC provider did not return an id_token.")

    # 2. Verify the id_token signature against the provider JWKS.
    claims = verify_id_token(id_token, disco, nonce)
    email = claims.get("email")
    if not email:
        raise AuthError("OIDC id_token did not include an email claim.")
    return FederatedIdentity(email=email, display_name=claims.get("name"))


def verify_id_token(id_token: str, disco: dict, nonce: str) -> dict:
    jwks_uri = disco.get("jwks_uri")
    if not jwks_uri:
        raise AuthError("OIDC discovery document is missing jwks_uri.")
    try:
        jwk_client = jwt.PyJWKClient(jwks_uri)
        signing_key = jwk_client.get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "RS384", "RS512", "ES256"],
            audience=settings.oidc_client_id,
            issuer=disco.get("issuer", settings.oidc_issuer),
        )
    except jwt.PyJWTError as exc:
        raise AuthError(f"OIDC id_token verification failed: {exc}") from exc
    if nonce and claims.get("nonce") != nonce:
        raise AuthError("OIDC nonce mismatch (possible replay).")
    return claims


# --------------------------------------------------------------------------- #
# SAML 2.0
# --------------------------------------------------------------------------- #
_SAML_NS = {
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}


def saml_metadata_xml() -> str:
    """Return SP metadata XML for registering ComplyGraph with an IdP."""
    if not (settings.saml_sp_entity_id and settings.saml_sp_acs_url):
        raise SSOError("SAML SP entity id / ACS URL are not configured.")
    return (
        '<?xml version="1.0"?>'
        '<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" '
        f'entityID="{settings.saml_sp_entity_id}">'
        '<md:SPSSODescriptor AuthnRequestsSigned="false" WantAssertionsSigned="true" '
        'protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">'
        '<md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>'
        '<md:AssertionConsumerService '
        'Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" '
        f'Location="{settings.saml_sp_acs_url}" index="0" isDefault="true"/>'
        "</md:SPSSODescriptor></md:EntityDescriptor>"
    )


def saml_redirect_url(relay_state: str | None = None) -> str:
    """Build an SP-initiated AuthnRequest for the HTTP-Redirect binding."""
    if not settings.saml_configured:
        raise SSOError("SAML is not configured for this deployment.")
    request_id = "_" + uuid.uuid4().hex
    issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    authn_request = (
        '<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" '
        'xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" '
        f'ID="{request_id}" Version="2.0" IssueInstant="{issue_instant}" '
        f'Destination="{settings.saml_idp_sso_url}" '
        'ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" '
        f'AssertionConsumerServiceURL="{settings.saml_sp_acs_url}">'
        f"<saml:Issuer>{settings.saml_sp_entity_id}</saml:Issuer>"
        '<samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress" '
        'AllowCreate="true"/>'
        "</samlp:AuthnRequest>"
    )
    # HTTP-Redirect binding: raw-DEFLATE + base64 + urlencode.
    compressed = zlib.compress(authn_request.encode("utf-8"))[2:-4]
    encoded = base64.b64encode(compressed).decode("ascii")
    params = {"SAMLRequest": encoded}
    if relay_state:
        params["RelayState"] = relay_state
    sep = "&" if "?" in settings.saml_idp_sso_url else "?"
    return f"{settings.saml_idp_sso_url}{sep}{urlencode(params)}"


def _idp_cert_pem() -> str:
    """Normalise the configured IdP certificate to PEM form."""
    raw = settings.saml_idp_x509_cert.strip()
    if "BEGIN CERTIFICATE" in raw:
        return raw
    # Bare base64 DER -> wrap in PEM armor (64-char lines).
    body = "".join(raw.split())
    lines = "\n".join(body[i : i + 64] for i in range(0, len(body), 64))
    return f"-----BEGIN CERTIFICATE-----\n{lines}\n-----END CERTIFICATE-----\n"


def parse_and_verify_saml_response(saml_response_b64: str) -> FederatedIdentity:
    """Verify a base64 SAMLResponse's signature + conditions and return the identity."""
    if not settings.saml_configured:
        raise SSOError("SAML is not configured for this deployment.")
    import lxml.etree as ET
    from signxml import XMLVerifier

    try:
        xml_bytes = base64.b64decode(saml_response_b64)
    except Exception as exc:  # noqa: BLE001
        raise AuthError("SAMLResponse is not valid base64.") from exc

    # Parse defensively (no entity resolution / network / huge trees).
    parser = ET.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
    try:
        doc = ET.fromstring(xml_bytes, parser=parser)
    except ET.XMLSyntaxError as exc:
        raise AuthError("SAMLResponse is not well-formed XML.") from exc

    cert_pem = _idp_cert_pem()
    # Verify the XML-DSig signature; raises if absent/invalid/untrusted.
    try:
        result = XMLVerifier().verify(doc, x509_cert=cert_pem)
    except Exception as exc:  # noqa: BLE001 - signxml raises many types
        raise AuthError(f"SAML signature verification failed: {exc}") from exc

    # SECURITY: read the identity ONLY from the cryptographically-verified
    # subtree, never from the original parsed document. Trusting the raw doc
    # would expose us to XML signature-wrapping attacks, where an attacker adds
    # an unsigned assertion alongside a validly-signed (but unrelated) one.
    verified = result[0].signed_xml if isinstance(result, list) else result.signed_xml
    if verified is None:
        raise AuthError("SAML signature did not cover any assertion.")

    assertion = _find_assertion(verified)
    _check_conditions(assertion)
    email = _extract_nameid(assertion)
    name = _extract_attribute(assertion, ("displayName", "name", "cn"))
    return FederatedIdentity(email=email, display_name=name)


def _find_assertion(verified):
    """Locate the Assertion strictly within the signature-verified subtree."""
    tag = "{urn:oasis:names:tc:SAML:2.0:assertion}Assertion"
    if verified.tag == tag:
        return verified
    found = verified.find(".//saml:Assertion", _SAML_NS)
    if found is None:
        raise AuthError(
            "The signed portion of the SAMLResponse did not contain an assertion."
        )
    return found


def _check_conditions(assertion) -> None:
    conditions = assertion.find("saml:Conditions", _SAML_NS)
    if conditions is None:
        return
    now = datetime.now(timezone.utc)
    not_before = conditions.get("NotBefore")
    not_on_or_after = conditions.get("NotOnOrAfter")
    if not_before and now < _parse_instant(not_before):
        raise AuthError("SAML assertion is not yet valid.")
    if not_on_or_after and now >= _parse_instant(not_on_or_after):
        raise AuthError("SAML assertion has expired.")
    # Audience restriction must include our SP entity id when present.
    audiences = [a.text for a in assertion.findall(".//saml:Audience", _SAML_NS)]
    if audiences and settings.saml_sp_entity_id not in audiences:
        raise AuthError("SAML assertion audience does not match this service.")


def _parse_instant(value: str) -> datetime:
    value = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _extract_nameid(assertion) -> str:
    nameid = assertion.find(".//saml:Subject/saml:NameID", _SAML_NS)
    if nameid is None or not (nameid.text or "").strip():
        # Fall back to an email-like attribute.
        email = _extract_attribute(assertion, ("email", "emailAddress", "mail"))
        if email:
            return email
        raise AuthError("SAML assertion did not contain a NameID or email.")
    return nameid.text.strip()


def _extract_attribute(assertion, names: tuple[str, ...]) -> str | None:
    for attr in assertion.findall(".//saml:AttributeStatement/saml:Attribute", _SAML_NS):
        attr_name = (attr.get("Name") or "").split("/")[-1].lower()
        friendly = (attr.get("FriendlyName") or "").lower()
        if attr_name in {n.lower() for n in names} or friendly in {n.lower() for n in names}:
            value = attr.find("saml:AttributeValue", _SAML_NS)
            if value is not None and (value.text or "").strip():
                return value.text.strip()
    return None
