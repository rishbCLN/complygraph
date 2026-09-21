"""End-to-end tests for the maker-checker approval workflow (feature #4)."""

from __future__ import annotations

import uuid

import pytest

PREFIX = "/api/v1"


@pytest.fixture
def maker_client():
    """SECURITY_ANALYST: can manage findings/risks (maker) but cannot approve.

    Uses its own TestClient (separate cookie jar) so it stays a distinct session
    from admin_client within the same test.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        resp = c.post(
            f"{PREFIX}/auth/login",
            json={"email": "security@asterlane.demo", "password": "DemoPass123!"},
        )
        assert resp.status_code == 200, resp.text
        me = resp.json()
        c.headers.update({"x-organization-id": me["organization"]["id"]})
        yield c


def _a_finding_id(admin_client) -> str:
    findings = admin_client.get(f"{PREFIX}/findings?page=1").json()["items"]
    assert findings, "seed should contain findings"
    for f in findings:
        if f["status"] in ("OPEN", "ACKNOWLEDGED", "IN_PROGRESS"):
            return f["id"]
    return findings[0]["id"]


def _new_risk_id(admin_client) -> str:
    resp = admin_client.post(
        f"{PREFIX}/risks",
        json={"title": f"Risk {uuid.uuid4().hex[:6]}", "residual_likelihood": 3, "residual_impact": 3},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _submit_risk_accept(cli, rid, rationale="Residual within appetite."):
    return cli.post(
        f"{PREFIX}/approvals",
        json={"entity_type": "risk", "entity_id": rid, "action": "accept",
              "payload": {"rationale": rationale}},
    )


def test_submit_creates_pending(maker_client, admin_client):
    rid = _new_risk_id(admin_client)
    resp = _submit_risk_accept(maker_client, rid)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "PENDING"
    assert body["submitted_by"]
    assert body["reviewed_by"] is None


def test_maker_cannot_approve(maker_client, admin_client):
    """The maker lacks the approve capability entirely -> 403."""
    rid = _new_risk_id(admin_client)
    req = _submit_risk_accept(maker_client, rid).json()
    resp = maker_client.post(f"{PREFIX}/approvals/{req['id']}/approve", json={})
    assert resp.status_code == 403


def test_segregation_of_duties_blocks_self_approval(admin_client):
    """Admin can both submit and approve, but must not approve their OWN request."""
    rid = _new_risk_id(admin_client)
    req = _submit_risk_accept(admin_client, rid).json()
    resp = admin_client.post(f"{PREFIX}/approvals/{req['id']}/approve", json={})
    assert resp.status_code == 422
    assert "segregation" in resp.json()["error"]["message"].lower()


def test_full_approve_applies_change(maker_client, admin_client):
    fid = _a_finding_id(admin_client)
    req = maker_client.post(
        f"{PREFIX}/approvals",
        json={
            "entity_type": "finding",
            "entity_id": fid,
            "action": "accept_risk",
            "payload": {"note": "Compensating controls in place; accepted for this cycle."},
        },
    ).json()
    resp = admin_client.post(f"{PREFIX}/approvals/{req['id']}/approve", json={"note": "Reviewed."})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "APPROVED"
    assert resp.json()["reviewed_by"]
    finding = admin_client.get(f"{PREFIX}/findings/{fid}").json()
    assert finding["status"] == "ACCEPTED_RISK"


def test_risk_acceptance_via_approval(maker_client, admin_client):
    rid = _new_risk_id(admin_client)
    req = _submit_risk_accept(maker_client, rid, "Residual within appetite.").json()
    approved = admin_client.post(f"{PREFIX}/approvals/{req['id']}/approve", json={})
    assert approved.status_code == 200, approved.text
    risk = admin_client.get(f"{PREFIX}/risks/{rid}").json()
    assert risk["status"] == "ACCEPTED"
    assert risk["acceptance_rationale"] == "Residual within appetite."


def test_reject_does_not_apply(maker_client, admin_client):
    rid = _new_risk_id(admin_client)
    req = _submit_risk_accept(maker_client, rid, "Please accept.").json()
    rejected = admin_client.post(f"{PREFIX}/approvals/{req['id']}/reject", json={"note": "Mitigate instead."})
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    risk = admin_client.get(f"{PREFIX}/risks/{rid}").json()
    assert risk["status"] != "ACCEPTED"


def test_duplicate_pending_conflict(maker_client, admin_client):
    rid = _new_risk_id(admin_client)
    assert _submit_risk_accept(maker_client, rid).status_code == 201
    assert _submit_risk_accept(maker_client, rid).status_code == 409


def test_missing_rationale_rejected(maker_client, admin_client):
    rid = _new_risk_id(admin_client)
    resp = maker_client.post(
        f"{PREFIX}/approvals",
        json={"entity_type": "risk", "entity_id": rid, "action": "accept", "payload": {}},
    )
    assert resp.status_code == 422


def test_cancel_by_submitter(maker_client, admin_client):
    rid = _new_risk_id(admin_client)
    req = _submit_risk_accept(maker_client, rid).json()
    resp = maker_client.post(f"{PREFIX}/approvals/{req['id']}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


def test_cannot_approve_twice(maker_client, admin_client):
    rid = _new_risk_id(admin_client)
    req = _submit_risk_accept(maker_client, rid, "ok").json()
    assert admin_client.post(f"{PREFIX}/approvals/{req['id']}/approve", json={}).status_code == 200
    again = admin_client.post(f"{PREFIX}/approvals/{req['id']}/approve", json={})
    assert again.status_code == 409


def test_unknown_entity_type_rejected(maker_client):
    resp = maker_client.post(
        f"{PREFIX}/approvals",
        json={"entity_type": "banana", "entity_id": str(uuid.uuid4()), "action": "resolve"},
    )
    # maker lacks a submit capability for an unknown type -> forbidden
    assert resp.status_code == 403


def test_list_and_filter(maker_client, admin_client):
    rid = _new_risk_id(admin_client)
    _submit_risk_accept(maker_client, rid)
    listed = admin_client.get(f"{PREFIX}/approvals?status=PENDING").json()
    assert listed
    assert all(r["status"] == "PENDING" for r in listed)


def test_requires_auth(client):
    assert client.get(f"{PREFIX}/approvals").status_code in (401, 403)
