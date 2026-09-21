"""End-to-end tests for SSO (feature #10): OIDC + SAML.

These exercise the real verification paths:
* OIDC: discovery + authorization-URL construction are validated with a mocked
  discovery document (no live IdP needed).
* SAML: a real RSA-signed SAMLResponse is generated with a throwaway cert and
  fed through the actual ``signxml`` verification path, proving signatures are
  genuinely checked (a tampered assertion is rejected).
"""

from __future__ import annotations

import base64
import datetime

import lxml.etree as ET
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient
from signxml import XMLSigner

from app.core.config import settings
from app.services import sso_service

PREFIX = "/api/v1"
SAML_ASSERT = "urn:oasis:names:tc:SAML:2.0:assertion"
SAMLP = "urn:oasis:names:tc:SAML:2.0:protocol"


# --------------------------------------------------------------------------- #
# Dormant behaviour
# --------------------------------------------------------------------------- #
def test_providers_empty_when_dormant(client):
    resp = client.get(f"{PREFIX}/sso/providers")
    assert resp.status_code == 200
    assert resp.json()["providers"] == []


def test_oidc_login_404_when_dormant(client):
    assert client.get(f"{PREFIX}/sso/oidc/login", follow_redirects=False).status_code == 404


def test_saml_login_404_when_dormant(client):
    assert client.get(f"{PREFIX}/sso/saml/login", follow_redirects=False).status_code == 404


# --------------------------------------------------------------------------- #
# OIDC (mocked discovery)
# --------------------------------------------------------------------------- #
def test_oidc_authorization_url_built_from_discovery(monkeypatch):
    monkeypatch.setattr(settings, "oidc_issuer", "https://idp.test")
    monkeypatch.setattr(settings, "oidc_client_id", "client-abc")
    monkeypatch.setattr(settings, "oidc_client_secret", "shh")
    monkeypatch.setattr(settings, "oidc_redirect_url", "https://app.test/cb")
    assert settings.oidc_configured
    monkeypatch.setattr(
        sso_service,
        "_discovery",
        lambda: {
            "authorization_endpoint": "https://idp.test/authorize",
            "token_endpoint": "https://idp.test/token",
            "jwks_uri": "https://idp.test/jwks",
            "issuer": "https://idp.test",
        },
    )
    nonce = "nonce123"
    state = sso_service.make_state_token(nonce)
    url = sso_service.oidc_authorization_url(state, nonce)
    assert url.startswith("https://idp.test/authorize?")
    assert "client_id=client-abc" in url
    assert "response_type=code" in url
    assert f"state={state}" in url


def test_state_token_roundtrip():
    token = sso_service.make_state_token("the-nonce")
    assert sso_service.read_state_token(token) == "the-nonce"


def test_state_token_rejects_tampering():
    from app.core.errors import AuthError

    with pytest.raises(AuthError):
        sso_service.read_state_token("not-a-real-token")


# --------------------------------------------------------------------------- #
# SAML (real signature verification)
# --------------------------------------------------------------------------- #
def _make_cert():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-idp")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    return key_pem, cert_pem


def _signed_saml_response(
    key_pem, cert_pem, email, audience, *, tamper=False, tamper_digest=False
):
    now = datetime.datetime.now(datetime.timezone.utc)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    nsmap = {"samlp": SAMLP, "saml": SAML_ASSERT}
    resp = ET.Element(f"{{{SAMLP}}}Response", nsmap=nsmap)
    resp.set("ID", "_r1")
    resp.set("Version", "2.0")
    resp.set("IssueInstant", now.strftime(fmt))
    a = ET.SubElement(resp, f"{{{SAML_ASSERT}}}Assertion")
    a.set("ID", "_a1")
    a.set("Version", "2.0")
    a.set("IssueInstant", now.strftime(fmt))
    issuer = ET.SubElement(a, f"{{{SAML_ASSERT}}}Issuer")
    issuer.text = "https://idp.test/entity"
    subj = ET.SubElement(a, f"{{{SAML_ASSERT}}}Subject")
    nid = ET.SubElement(subj, f"{{{SAML_ASSERT}}}NameID")
    nid.set("Format", "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress")
    nid.text = email
    cond = ET.SubElement(a, f"{{{SAML_ASSERT}}}Conditions")
    cond.set("NotBefore", (now - datetime.timedelta(minutes=5)).strftime(fmt))
    cond.set("NotOnOrAfter", (now + datetime.timedelta(minutes=5)).strftime(fmt))
    ar = ET.SubElement(cond, f"{{{SAML_ASSERT}}}AudienceRestriction")
    aud = ET.SubElement(ar, f"{{{SAML_ASSERT}}}Audience")
    aud.text = audience

    signer = XMLSigner(signature_algorithm="rsa-sha256", digest_algorithm="sha256")
    signed_assertion = signer.sign(a, key=key_pem, cert=cert_pem, reference_uri="_a1")
    resp.replace(a, signed_assertion)

    if tamper:
        # Flip the NameID *after* signing. Append a guaranteed-distinct suffix
        # so the signed bytes genuinely change regardless of the original value
        # (a plain string swap can silently be a no-op if the replacement text
        # happens to normalise to the original).
        tampered_nid = resp.find(f".//{{{SAML_ASSERT}}}NameID")
        tampered_nid.text = (tampered_nid.text or "") + "+forged-9d21"

    if tamper_digest:
        dv = resp.find(".//{http://www.w3.org/2000/09/xmldsig#}DigestValue")
        dv.text = base64.b64encode(b"x" * 32).decode()

    return base64.b64encode(ET.tostring(resp)).decode()


@pytest.fixture
def saml_configured(monkeypatch):
    key_pem, cert_pem = _make_cert()
    monkeypatch.setattr(settings, "saml_sp_entity_id", "complygraph-sp")
    monkeypatch.setattr(settings, "saml_sp_acs_url", "https://app.test/acs")
    monkeypatch.setattr(settings, "saml_idp_entity_id", "https://idp.test/entity")
    monkeypatch.setattr(settings, "saml_idp_sso_url", "https://idp.test/sso")
    monkeypatch.setattr(settings, "saml_idp_x509_cert", cert_pem.decode())
    assert settings.saml_configured
    return key_pem, cert_pem


def test_saml_verifies_valid_signed_response(saml_configured):
    key_pem, cert_pem = saml_configured
    b64 = _signed_saml_response(key_pem, cert_pem, "[email protected]", "complygraph-sp")
    identity = sso_service.parse_and_verify_saml_response(b64)
    assert identity.email == "[email protected]"


def test_saml_rejects_tampered_nameid(saml_configured):
    """Editing the NameID text after signing invalidates the XML-DSig digest.

    ``signxml`` recomputes the reference digest over the (now-modified)
    assertion and finds it no longer matches the signed DigestValue, so
    verification raises - which the service surfaces as ``AuthError``. The
    forged identity never reaches user resolution.
    """
    from app.core.errors import AuthError

    key_pem, cert_pem = saml_configured
    b64 = _signed_saml_response(
        key_pem, cert_pem, "[email protected]", "complygraph-sp", tamper=True
    )
    with pytest.raises(AuthError):
        sso_service.parse_and_verify_saml_response(b64)


def test_saml_rejects_wrong_signing_cert(saml_configured):
    from app.core.errors import AuthError

    key_pem, _ = saml_configured
    # Sign with a DIFFERENT cert than the one configured on the SP.
    other_key, other_cert = _make_cert()
    b64 = _signed_saml_response(other_key, other_cert, "[email protected]", "complygraph-sp")
    with pytest.raises(AuthError):
        sso_service.parse_and_verify_saml_response(b64)


def test_saml_rejects_tampered_digest(saml_configured):
    """A modified DigestValue (real signature forgery) must be rejected."""
    from app.core.errors import AuthError

    key_pem, cert_pem = saml_configured
    b64 = _signed_saml_response(
        key_pem, cert_pem, "[email protected]", "complygraph-sp", tamper_digest=True
    )
    with pytest.raises(AuthError):
        sso_service.parse_and_verify_saml_response(b64)


def test_saml_metadata_endpoint(saml_configured):
    from app.main import app

    with TestClient(app) as c:
        resp = c.get(f"{PREFIX}/sso/saml/metadata")
        assert resp.status_code == 200
        assert "EntityDescriptor" in resp.text
        assert "complygraph-sp" in resp.text


def test_saml_login_redirects_when_configured(saml_configured):
    from app.main import app

    with TestClient(app) as c:
        resp = c.get(f"{PREFIX}/sso/saml/login", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"].startswith("https://idp.test/sso")
        assert "SAMLRequest=" in resp.headers["location"]


def test_saml_acs_establishes_session_for_existing_user(saml_configured):
    key_pem, cert_pem = saml_configured
    # admin@asterlane.demo exists in the seeded org.
    b64 = _signed_saml_response(key_pem, cert_pem, "admin@asterlane.demo", "complygraph-sp")

    from app.main import app

    with TestClient(app) as c:
        resp = c.post(
            f"{PREFIX}/sso/saml/acs",
            data={"SAMLResponse": b64},
            follow_redirects=False,
        )
        assert resp.status_code == 302, resp.text
        # A session cookie is set and /auth/me now works.
        me = c.get(f"{PREFIX}/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == "admin@asterlane.demo"


def test_saml_acs_rejects_unknown_user_without_autoprovision(saml_configured):
    key_pem, cert_pem = saml_configured
    b64 = _signed_saml_response(
        key_pem, cert_pem, "[email protected]", "complygraph-sp"
    )

    from app.main import app

    with TestClient(app) as c:
        resp = c.post(
            f"{PREFIX}/sso/saml/acs",
            data={"SAMLResponse": b64},
            follow_redirects=False,
        )
        assert resp.status_code == 401  # AuthError: no account, auto-provision off
