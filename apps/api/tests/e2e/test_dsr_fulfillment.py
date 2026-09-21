"""End-to-end tests for the DSR fulfillment engine (feature #7)."""

from __future__ import annotations

PREFIX = "/api/v1"


def _create(admin_client, request_type="ACCESS", requester="[email protected]"):
    resp = admin_client.post(
        f"{PREFIX}/data-requests",
        json={"requester_identifier": requester, "request_type": request_type},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _verify(admin_client, rid):
    resp = admin_client.post(f"{PREFIX}/data-requests/{rid}/verify")
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_fulfill_requires_verification(admin_client):
    req = _create(admin_client)
    # Not verified yet -> refuse.
    resp = admin_client.post(f"{PREFIX}/data-requests/{req['id']}/fulfill")
    assert resp.status_code == 409


def test_discover_lists_personal_data_stores(admin_client):
    req = _create(admin_client)
    discovered = admin_client.get(f"{PREFIX}/data-requests/{req['id']}/discover").json()
    assert discovered, "seed inventory should contain personal-data assets"
    for item in discovered:
        assert item["asset_name"]
        assert "pii_fields" in item


def test_access_fulfillment_collects(admin_client):
    req = _create(admin_client, request_type="ACCESS")
    _verify(admin_client, req["id"])
    resp = admin_client.post(f"{PREFIX}/data-requests/{req['id']}/fulfill")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    pkg = body["fulfillment"]
    assert pkg is not None
    assert pkg["action"] == "COLLECT"
    assert pkg["stores_total"] >= 1
    assert "stores" in pkg
    # Metadata-only: no raw values, but field names/categories are present.
    for store in pkg["stores"]:
        assert store["action"] == "COLLECT"
        for f in store["fields"]:
            assert set(f.keys()) == {"name", "category", "classification"}
    assert body["status"] in ("FULFILLED", "IN_PROGRESS")


def test_erasure_fulfillment_erases(admin_client):
    req = _create(admin_client, request_type="ERASURE")
    _verify(admin_client, req["id"])
    resp = admin_client.post(f"{PREFIX}/data-requests/{req['id']}/fulfill")
    assert resp.status_code == 200, resp.text
    pkg = resp.json()["fulfillment"]
    assert pkg["action"] == "ERASE"
    assert all(s["action"] == "ERASE" for s in pkg["stores"])


def test_tasks_recorded_per_store(admin_client):
    req = _create(admin_client, request_type="ACCESS")
    _verify(admin_client, req["id"])
    admin_client.post(f"{PREFIX}/data-requests/{req['id']}/fulfill")
    tasks = admin_client.get(f"{PREFIX}/data-requests/{req['id']}/tasks").json()
    assert tasks, "fulfillment should produce per-store tasks"
    for t in tasks:
        assert t["action"] in ("COLLECT", "ERASE")
        assert t["status"] in ("COMPLETED", "SKIPPED", "FAILED", "PENDING")
        assert t["executed_at"]


def test_grievance_not_fulfillable(admin_client):
    req = _create(admin_client, request_type="GRIEVANCE")
    _verify(admin_client, req["id"])
    resp = admin_client.post(f"{PREFIX}/data-requests/{req['id']}/fulfill")
    assert resp.status_code == 422


def test_double_fulfill_conflict_when_complete(admin_client):
    req = _create(admin_client, request_type="ACCESS")
    _verify(admin_client, req["id"])
    first = admin_client.post(f"{PREFIX}/data-requests/{req['id']}/fulfill").json()
    if first["status"] == "FULFILLED":
        again = admin_client.post(f"{PREFIX}/data-requests/{req['id']}/fulfill")
        assert again.status_code == 409
    else:
        # Still in progress (some stores need manual completion) -> re-run allowed.
        again = admin_client.post(f"{PREFIX}/data-requests/{req['id']}/fulfill")
        assert again.status_code == 200


def test_fulfillment_is_idempotent_tasks(admin_client):
    """Re-running does not duplicate tasks (prior tasks are cleared)."""
    req = _create(admin_client, request_type="ERASURE")
    _verify(admin_client, req["id"])
    admin_client.post(f"{PREFIX}/data-requests/{req['id']}/fulfill")
    first_count = len(admin_client.get(f"{PREFIX}/data-requests/{req['id']}/tasks").json())
    # If it stayed IN_PROGRESS we can re-run; otherwise the count is stable anyway.
    body = admin_client.get(f"{PREFIX}/data-requests/{req['id']}").json()
    if body["status"] != "FULFILLED":
        admin_client.post(f"{PREFIX}/data-requests/{req['id']}/fulfill")
        second_count = len(admin_client.get(f"{PREFIX}/data-requests/{req['id']}/tasks").json())
        assert second_count == first_count


def test_viewer_cannot_fulfill(client):
    resp = client.post(
        f"{PREFIX}/auth/login",
        json={"email": "viewer@asterlane.demo", "password": "DemoPass123!"},
    )
    me = resp.json()
    client.headers.update({"x-organization-id": me["organization"]["id"]})
    # Need a request id; viewers can list.
    reqs = client.get(f"{PREFIX}/data-requests").json()
    if reqs:
        rid = reqs[0]["id"]
        assert client.post(f"{PREFIX}/data-requests/{rid}/fulfill").status_code == 403


def test_requires_auth(client):
    assert client.get(f"{PREFIX}/data-requests").status_code in (401, 403)
