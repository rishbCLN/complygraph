"""End-to-end tests for MFA (TOTP) enrolment and the login challenge (feature #10).

Uses a dedicated, isolated user (not a shared demo account) so enabling MFA
here never affects the other suites that log in as the demo users.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal, utcnow
from app.core.enums import Role
from app.models.identity import Membership, Organization, User
from app.security.passwords import hash_password
from app.security.totp import generate_totp

PREFIX = "/api/v1"
_PASSWORD = "MfaUserPass123!"


@pytest.fixture
def mfa_user(admin_org_id):
    """Create an isolated ADMIN user in the demo org for MFA testing."""
    db = SessionLocal()
    try:
        email = f"mfa-{uuid.uuid4().hex[:8]}@asterlane.demo"
        user = User(
            email=email,
            full_name="MFA Test User",
            password_hash=hash_password(_PASSWORD),
            is_active=True,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(user)
        db.flush()
        db.add(
            Membership(
                organization_id=uuid.UUID(admin_org_id),
                user_id=user.id,
                role=Role.ADMIN.value,
                created_at=utcnow(),
            )
        )
        db.commit()
        yield {"email": email, "org_id": admin_org_id}
    finally:
        db.close()


@pytest.fixture
def user_client(mfa_user):
    from app.main import app

    with TestClient(app) as c:
        resp = c.post(
            f"{PREFIX}/auth/login",
            json={"email": mfa_user["email"], "password": _PASSWORD},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["organization"]["id"] == mfa_user["org_id"]
        c.headers.update({"x-organization-id": mfa_user["org_id"]})
        yield c, mfa_user


def _enroll_and_activate(client) -> tuple[str, list[str]]:
    enroll = client.post(f"{PREFIX}/auth/mfa/enroll")
    assert enroll.status_code == 200, enroll.text
    secret = enroll.json()["secret"]
    assert enroll.json()["otpauth_uri"].startswith("otpauth://totp/")
    code = generate_totp(secret)
    activate = client.post(f"{PREFIX}/auth/mfa/activate", json={"code": code})
    assert activate.status_code == 200, activate.text
    backup = activate.json()["backup_codes"]
    assert len(backup) == 10
    return secret, backup


def test_mfa_status_defaults_disabled(user_client):
    client, _ = user_client
    status = client.get(f"{PREFIX}/auth/mfa").json()
    assert status["available"] is True
    assert status["enabled"] is False


def test_enroll_activate_flow_enables_mfa(user_client):
    client, _ = user_client
    _enroll_and_activate(client)
    status = client.get(f"{PREFIX}/auth/mfa").json()
    assert status["enabled"] is True
    me = client.get(f"{PREFIX}/auth/me").json()
    assert me["mfa_enabled"] is True


def test_activate_rejects_wrong_code(user_client):
    client, _ = user_client
    client.post(f"{PREFIX}/auth/mfa/enroll")
    resp = client.post(f"{PREFIX}/auth/mfa/activate", json={"code": "000000"})
    assert resp.status_code == 422  # ValidationError: incorrect code


def test_login_requires_second_factor_after_enrolment(user_client):
    client, info = user_client
    secret, _ = _enroll_and_activate(client)

    from app.main import app

    with TestClient(app) as fresh:
        # Password step alone returns a challenge, not a session.
        login = fresh.post(
            f"{PREFIX}/auth/login",
            json={"email": info["email"], "password": _PASSWORD},
        )
        assert login.status_code == 200, login.text
        body = login.json()
        assert body.get("mfa_required") is True
        assert "organization" not in body
        token = body["mfa_token"]

        # Wrong code is rejected.
        bad = fresh.post(
            f"{PREFIX}/auth/mfa/login", json={"mfa_token": token, "code": "000000"}
        )
        assert bad.status_code == 401

        # Correct code completes the login and establishes a session.
        good = fresh.post(
            f"{PREFIX}/auth/mfa/login",
            json={"mfa_token": token, "code": generate_totp(secret)},
        )
        assert good.status_code == 200, good.text
        assert good.json()["organization"]["id"] == info["org_id"]
        assert fresh.get(f"{PREFIX}/auth/me").status_code == 200


def test_backup_code_completes_login_and_is_single_use(user_client):
    client, info = user_client
    _, backup = _enroll_and_activate(client)
    one_time = backup[0]

    from app.main import app

    with TestClient(app) as fresh:
        token = fresh.post(
            f"{PREFIX}/auth/login",
            json={"email": info["email"], "password": _PASSWORD},
        ).json()["mfa_token"]
        ok = fresh.post(
            f"{PREFIX}/auth/mfa/login", json={"mfa_token": token, "code": one_time}
        )
        assert ok.status_code == 200, ok.text

    # The same backup code must not work a second time.
    with TestClient(app) as fresh2:
        token2 = fresh2.post(
            f"{PREFIX}/auth/login",
            json={"email": info["email"], "password": _PASSWORD},
        ).json()["mfa_token"]
        reused = fresh2.post(
            f"{PREFIX}/auth/mfa/login", json={"mfa_token": token2, "code": one_time}
        )
        assert reused.status_code == 401


def test_disable_requires_password_and_turns_mfa_off(user_client):
    client, _ = user_client
    _enroll_and_activate(client)
    # Wrong password rejected.
    assert client.post(f"{PREFIX}/auth/mfa/disable", json={"password": "nope"}).status_code == 401
    # Correct password disables.
    ok = client.post(f"{PREFIX}/auth/mfa/disable", json={"password": _PASSWORD})
    assert ok.status_code == 200, ok.text
    assert client.get(f"{PREFIX}/auth/mfa").json()["enabled"] is False
