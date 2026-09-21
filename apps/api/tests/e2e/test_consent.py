"""End-to-end tests for consent management + Privacy Center portal (feature #8)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

PREFIX = "/api/v1"


# --------------------------------------------------------------------------- #
# Staff-side: purposes
# --------------------------------------------------------------------------- #
def test_seeded_purposes_present(admin_client):
    purposes = admin_client.get(f"{PREFIX}/consent/purposes").json()
    codes = {p["code"] for p in purposes}
    assert {"account", "marketing", "analytics", "health-personalisation"} <= codes
    # account is contract-based, not consent
    account = next(p for p in purposes if p["code"] == "account")
    assert account["requires_consent"] is False
    health = next(p for p in purposes if p["code"] == "health-personalisation")
    assert health["is_sensitive"] is True


def test_create_and_update_purpose(admin_client):
    resp = admin_client.post(
        f"{PREFIX}/consent/purposes",
        json={"code": "newsletter", "name": "Newsletter", "requires_consent": True},
    )
    assert resp.status_code == 201, resp.text
    pid = resp.json()["id"]
    # Duplicate code -> conflict
    dup = admin_client.post(
        f"{PREFIX}/consent/purposes", json={"code": "newsletter", "name": "Dup"}
    )
    assert dup.status_code == 409
    # Patch
    patched = admin_client.patch(
        f"{PREFIX}/consent/purposes/{pid}", json={"name": "Weekly Newsletter"}
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Weekly Newsletter"


def test_purpose_requires_code(admin_client):
    resp = admin_client.post(f"{PREFIX}/consent/purposes", json={"code": "", "name": "x"})
    assert resp.status_code == 422


def test_archive_purpose(admin_client):
    resp = admin_client.post(
        f"{PREFIX}/consent/purposes", json={"code": "to-archive", "name": "Temp"}
    )
    pid = resp.json()["id"]
    archived = admin_client.delete(f"{PREFIX}/consent/purposes/{pid}")
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"


# --------------------------------------------------------------------------- #
# Staff-side: notices
# --------------------------------------------------------------------------- #
def test_notice_versioning_and_publish(admin_client):
    notices = admin_client.get(f"{PREFIX}/consent/notices").json()
    assert any(n["is_current"] for n in notices), "seed should publish version 1"
    prev_version = max(n["version"] for n in notices)

    created = admin_client.post(
        f"{PREFIX}/consent/notices",
        json={"title": "Updated Notice", "body": "New body", "publish": True},
    )
    assert created.status_code == 201
    new = created.json()
    assert new["version"] == prev_version + 1
    assert new["is_current"] is True

    # Only one current version.
    after = admin_client.get(f"{PREFIX}/consent/notices").json()
    assert sum(1 for n in after if n["is_current"]) == 1


def test_publish_older_notice_switches_current(admin_client):
    v_new = admin_client.post(
        f"{PREFIX}/consent/notices",
        json={"title": "Draft", "body": "draft body", "publish": False},
    ).json()
    assert v_new["is_current"] is False
    published = admin_client.post(f"{PREFIX}/consent/notices/{v_new['id']}/publish")
    assert published.status_code == 200
    assert published.json()["is_current"] is True


# --------------------------------------------------------------------------- #
# Staff-side: grant / withdraw + ledger
# --------------------------------------------------------------------------- #
def _purpose_id(admin_client, code):
    purposes = admin_client.get(f"{PREFIX}/consent/purposes").json()
    return next(p["id"] for p in purposes if p["code"] == code)


def test_staff_grant_and_withdraw_writes_ledger(admin_client):
    pid = _purpose_id(admin_client, "analytics")
    principal = "[email protected]"
    granted = admin_client.post(
        f"{PREFIX}/consent/grant", json={"purpose_id": pid, "principal_identifier": principal}
    )
    assert granted.status_code == 200, granted.text
    assert granted.json()["status"] == "GRANTED"
    assert granted.json()["verified"] is True

    withdrawn = admin_client.post(
        f"{PREFIX}/consent/withdraw", json={"purpose_id": pid, "principal_identifier": principal}
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "WITHDRAWN"

    # Ledger has both events for this principal (append-only).
    events = admin_client.get(f"{PREFIX}/consent/events", params={"principal": principal}).json()
    types = [e["event_type"] for e in events]
    assert "GRANTED" in types and "WITHDRAWN" in types


def test_cannot_grant_consent_for_contract_purpose(admin_client):
    pid = _purpose_id(admin_client, "account")  # requires_consent False
    resp = admin_client.post(
        f"{PREFIX}/consent/grant",
        json={"purpose_id": pid, "principal_identifier": "[email protected]"},
    )
    assert resp.status_code == 422


def test_consent_summary(admin_client):
    summary = admin_client.get(f"{PREFIX}/consent/summary").json()
    assert summary["purposes_total"] >= 4
    assert "by_purpose" in summary
    assert summary["current_notice_version"] is not None


def test_records_filter_by_status(admin_client):
    pid = _purpose_id(admin_client, "analytics")
    admin_client.post(
        f"{PREFIX}/consent/grant",
        json={"purpose_id": pid, "principal_identifier": "[email protected]"},
    )
    granted = admin_client.get(f"{PREFIX}/consent/records", params={"status": "GRANTED"}).json()
    assert all(r["status"] == "GRANTED" for r in granted)


# --------------------------------------------------------------------------- #
# RBAC
# --------------------------------------------------------------------------- #
def test_viewer_cannot_manage_consent(client):
    resp = client.post(
        f"{PREFIX}/auth/login",
        json={"email": "viewer@asterlane.demo", "password": "DemoPass123!"},
    )
    me = resp.json()
    client.headers.update({"x-organization-id": me["organization"]["id"]})
    # Can read purposes
    assert client.get(f"{PREFIX}/consent/purposes").status_code == 200
    # Cannot create
    assert (
        client.post(f"{PREFIX}/consent/purposes", json={"code": "x", "name": "y"}).status_code
        == 403
    )


def test_consent_requires_auth(client):
    assert client.get(f"{PREFIX}/consent/purposes").status_code in (401, 403)


# --------------------------------------------------------------------------- #
# Public Privacy Center portal (unauthenticated)
# --------------------------------------------------------------------------- #
def test_portal_info_public(admin_client):
    # Portal uses a fresh unauthenticated client.
    public = TestClient(app)
    resp = public.get(f"{PREFIX}/privacy/asterlane")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["organization"]
    assert body["notice"] is not None
    assert body["notice"]["title"]
    # Only active purposes exposed, no consent state.
    assert len(body["purposes"]) >= 3
    assert "WITHDRAW_CONSENT" in body["request_types"]


def test_portal_unknown_org_404():
    public = TestClient(app)
    resp = public.get(f"{PREFIX}/privacy/does-not-exist")
    assert resp.status_code == 404


def test_portal_submit_consent_public(admin_client):
    # Find a consent purpose id via the authenticated side.
    pid = _purpose_id(admin_client, "marketing")
    public = TestClient(app)
    granted = public.post(
        f"{PREFIX}/privacy/asterlane/consent",
        json={"principal_identifier": "[email protected]", "purpose_id": pid, "action": "grant"},
    )
    assert granted.status_code == 200, granted.text
    assert granted.json()["ok"] is True

    # The staff side sees it recorded as self-asserted (verified False).
    records = admin_client.get(
        f"{PREFIX}/consent/records", params={"purpose_id": pid}
    ).json()
    portal_rec = next(
        (r for r in records if r["principal_identifier"] == "[email protected]"), None
    )
    assert portal_rec is not None
    assert portal_rec["verified"] is False

    # Withdraw via portal.
    withdrawn = public.post(
        f"{PREFIX}/privacy/asterlane/consent",
        json={"principal_identifier": "[email protected]", "purpose_id": pid, "action": "withdraw"},
    )
    assert withdrawn.status_code == 200


def test_portal_consent_invalid_action(admin_client):
    pid = _purpose_id(admin_client, "marketing")
    public = TestClient(app)
    resp = public.post(
        f"{PREFIX}/privacy/asterlane/consent",
        json={"principal_identifier": "[email protected]", "purpose_id": pid, "action": "maybe"},
    )
    assert resp.status_code == 422


def test_portal_submit_dsr_public():
    public = TestClient(app)
    resp = public.post(
        f"{PREFIX}/privacy/asterlane/requests",
        json={"principal_identifier": "[email protected]", "request_type": "ACCESS"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["reference"]


def test_portal_dsr_shows_in_staff_queue_pending(admin_client):
    public = TestClient(app)
    public.post(
        f"{PREFIX}/privacy/asterlane/requests",
        json={"principal_identifier": "[email protected]", "request_type": "ERASURE"},
    )
    reqs = admin_client.get(f"{PREFIX}/data-requests").json()
    portal_req = next(
        (r for r in reqs if r["requester_identifier"] == "[email protected]"), None
    )
    assert portal_req is not None
    # Portal-submitted requests are unverified until staff verify identity.
    assert portal_req["verification_status"] == "PENDING"


def test_portal_bad_request_type():
    public = TestClient(app)
    resp = public.post(
        f"{PREFIX}/privacy/asterlane/requests",
        json={"principal_identifier": "[email protected]", "request_type": "NONSENSE"},
    )
    assert resp.status_code == 422
