"""End-to-end + unit tests for integrations (feature #10): webhooks and tickets."""

from __future__ import annotations

import httpx
import pytest

from app.services import webhook_service

PREFIX = "/api/v1"


# --------------------------------------------------------------------------- #
# Signing (pure)
# --------------------------------------------------------------------------- #
def test_sign_payload_is_stable_hmac_sha256():
    body = b'{"hello":"world"}'
    sig = webhook_service.sign_payload("whsec_test", body)
    assert sig.startswith("sha256=")
    # Deterministic for the same secret + body.
    assert sig == webhook_service.sign_payload("whsec_test", body)
    # Changes with the secret.
    assert sig != webhook_service.sign_payload("whsec_other", body)


# --------------------------------------------------------------------------- #
# Status
# --------------------------------------------------------------------------- #
def test_status_reports_all_dormant_by_default(admin_client):
    resp = admin_client.get(f"{PREFIX}/integrations/status")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    names = {i["name"]: i["configured"] for i in body["integrations"]}
    assert names == {
        "jira": False,
        "servicenow": False,
        "oidc": False,
        "saml": False,
        "email": False,
    }
    assert "finding.created" in body["webhook_events"]


# --------------------------------------------------------------------------- #
# Webhook CRUD + RBAC
# --------------------------------------------------------------------------- #
def test_webhook_crud_lifecycle(admin_client):
    create = admin_client.post(
        f"{PREFIX}/integrations/webhooks",
        json={
            "name": "Ops channel",
            "url": "https://example.test/hook",
            "events": ["finding.created", "risk.created"],
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["secret"].startswith("whsec_")  # returned once
    wid = body["id"]

    # Listing never exposes the secret.
    listing = admin_client.get(f"{PREFIX}/integrations/webhooks").json()
    assert any(w["id"] == wid for w in listing)
    assert all("secret" not in w for w in listing)

    # Update (disable + change events).
    upd = admin_client.patch(
        f"{PREFIX}/integrations/webhooks/{wid}",
        json={"enabled": False, "events": ["dsr.created"]},
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["enabled"] is False
    assert upd.json()["events"] == ["dsr.created"]

    # Rotate secret returns a new one.
    rot = admin_client.post(f"{PREFIX}/integrations/webhooks/{wid}/rotate-secret")
    assert rot.status_code == 200
    assert rot.json()["secret"] != body["secret"]

    # Delete.
    assert admin_client.delete(f"{PREFIX}/integrations/webhooks/{wid}").status_code == 204
    assert all(w["id"] != wid for w in admin_client.get(f"{PREFIX}/integrations/webhooks").json())


def test_webhook_rejects_invalid_event(admin_client):
    resp = admin_client.post(
        f"{PREFIX}/integrations/webhooks",
        json={"name": "x", "url": "https://example.test/h", "events": ["not.an.event"]},
    )
    assert resp.status_code == 422


def test_webhook_rejects_non_http_url(admin_client):
    resp = admin_client.post(
        f"{PREFIX}/integrations/webhooks",
        json={"name": "x", "url": "ftp://example.test/h"},
    )
    assert resp.status_code == 422


def test_viewer_cannot_manage_webhooks(client):
    login = client.post(
        f"{PREFIX}/auth/login",
        json={"email": "viewer@asterlane.demo", "password": "DemoPass123!"},
    )
    client.headers.update({"x-organization-id": login.json()["organization"]["id"]})
    assert client.get(f"{PREFIX}/integrations/webhooks").status_code == 403
    assert (
        client.post(
            f"{PREFIX}/integrations/webhooks",
            json={"name": "x", "url": "https://example.test/h"},
        ).status_code
        == 403
    )


# --------------------------------------------------------------------------- #
# Delivery (success / retry / failure) via monkeypatched transport
# --------------------------------------------------------------------------- #
def _ok(url, body, headers):
    return httpx.Response(200, text="ok", request=httpx.Request("POST", url))


def test_test_ping_success(admin_client, monkeypatch):
    monkeypatch.setattr(webhook_service, "_deliver_once", _ok)
    wid = admin_client.post(
        f"{PREFIX}/integrations/webhooks",
        json={"name": "Ping", "url": "https://example.test/hook"},
    ).json()["id"]

    resp = admin_client.post(f"{PREFIX}/integrations/webhooks/{wid}/test")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "SUCCEEDED"
    assert resp.json()["response_code"] == 200

    deliveries = admin_client.get(f"{PREFIX}/integrations/webhooks/{wid}/deliveries").json()
    assert deliveries and deliveries[0]["status"] == "SUCCEEDED"


def test_delivery_retries_then_fails(admin_client, monkeypatch):
    calls = {"n": 0}

    def _always_500(url, body, headers):
        calls["n"] += 1
        return httpx.Response(500, text="boom", request=httpx.Request("POST", url))

    monkeypatch.setattr(webhook_service, "_deliver_once", _always_500)
    monkeypatch.setattr(webhook_service.settings, "webhook_max_attempts", 3)
    monkeypatch.setattr(webhook_service.settings, "webhook_retry_backoff_seconds", 0)

    wid = admin_client.post(
        f"{PREFIX}/integrations/webhooks",
        json={"name": "Flaky", "url": "https://example.test/hook"},
    ).json()["id"]

    resp = admin_client.post(f"{PREFIX}/integrations/webhooks/{wid}/test")
    assert resp.status_code == 200
    assert resp.json()["status"] == "FAILED"
    assert resp.json()["attempts"] == 3
    assert calls["n"] == 3  # retried up to the configured maximum


def test_4xx_is_not_retried(admin_client, monkeypatch):
    calls = {"n": 0}

    def _400(url, body, headers):
        calls["n"] += 1
        return httpx.Response(400, text="bad", request=httpx.Request("POST", url))

    monkeypatch.setattr(webhook_service, "_deliver_once", _400)
    monkeypatch.setattr(webhook_service.settings, "webhook_max_attempts", 4)
    monkeypatch.setattr(webhook_service.settings, "webhook_retry_backoff_seconds", 0)

    wid = admin_client.post(
        f"{PREFIX}/integrations/webhooks",
        json={"name": "Perm", "url": "https://example.test/hook"},
    ).json()["id"]

    admin_client.post(f"{PREFIX}/integrations/webhooks/{wid}/test")
    assert calls["n"] == 1  # 4xx (non-429) is a permanent failure, no retry


# --------------------------------------------------------------------------- #
# Tickets (dormant + configured-via-monkeypatch)
# --------------------------------------------------------------------------- #
def _first_finding_id(admin_client) -> str:
    findings = admin_client.get(f"{PREFIX}/findings").json()
    items = findings["items"] if isinstance(findings, dict) else findings
    assert items, "expected seeded findings"
    return items[0]["id"]


def test_ticket_creation_dormant_returns_400(admin_client):
    fid = _first_finding_id(admin_client)
    resp = admin_client.post(
        f"{PREFIX}/integrations/tickets",
        json={"provider": "JIRA", "entity_type": "finding", "entity_id": fid},
    )
    # Jira not configured => IntegrationNotConfigured (400).
    assert resp.status_code == 400, resp.text


def test_ticket_creation_when_configured(admin_client, monkeypatch):
    from app.integrations import TicketRef, jira_client

    monkeypatch.setattr(
        jira_client,
        "create_issue",
        lambda **kw: TicketRef(
            external_id="10001", external_key="SEC-1", url="https://acme.atlassian.net/browse/SEC-1"
        ),
    )
    fid = _first_finding_id(admin_client)
    resp = admin_client.post(
        f"{PREFIX}/integrations/tickets",
        json={"provider": "JIRA", "entity_type": "finding", "entity_id": fid},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["external_key"] == "SEC-1"
    assert body["external_url"].endswith("/browse/SEC-1")

    # It appears in the entity's ticket list.
    listing = admin_client.get(
        f"{PREFIX}/integrations/tickets",
        params={"entity_type": "finding", "entity_id": fid},
    ).json()
    assert any(t["external_key"] == "SEC-1" for t in listing)


def test_ticket_rejects_unknown_provider(admin_client):
    fid = _first_finding_id(admin_client)
    resp = admin_client.post(
        f"{PREFIX}/integrations/tickets",
        json={"provider": "TRELLO", "entity_type": "finding", "entity_id": fid},
    )
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# Domain-event dispatch wiring (finding/risk/dsr/breach/assessment -> webhooks)
# --------------------------------------------------------------------------- #
def test_domain_event_dispatches_to_subscribed_endpoint(monkeypatch):
    """A real domain event (risk.created) fans out to a subscribed endpoint.

    Proves the ``dispatch_event`` calls wired into the services actually fire:
    we enable webhooks, register an endpoint for ``risk.created``, create a risk
    through the service, and assert the signed payload reached the transport.
    """
    import json as _json

    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models.identity import Organization
    from app.services import risk_service

    monkeypatch.setattr(webhook_service.settings, "webhooks_enabled", True)
    captured: list[dict] = []

    def _capture(url, body, headers):
        captured.append(_json.loads(body))
        assert headers.get("X-ComplyGraph-Signature", "").startswith("sha256=")
        return httpx.Response(200, text="ok", request=httpx.Request("POST", url))

    monkeypatch.setattr(webhook_service, "_deliver_once", _capture)

    db = SessionLocal()
    try:
        org = db.scalar(select(Organization).where(Organization.slug == "asterlane"))
        assert org is not None
        webhook_service.create_endpoint(
            db,
            org.id,
            name="wiring-test",
            url="https://example.test/hook",
            events=["risk.created"],
        )
        db.flush()
        risk_service.create_risk(db, org.id, None, {"title": "Wiring test risk"})
        events = [c["event"] for c in captured]
        assert "risk.created" in events
        payload = next(c["data"] for c in captured if c["event"] == "risk.created")
        assert payload["title"] == "Wiring test risk"
        assert payload["status"]  # a status is always present
    finally:
        # Roll back so the seeded session-scoped DB is left untouched.
        db.rollback()
        db.close()
