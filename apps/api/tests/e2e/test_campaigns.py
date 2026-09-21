"""End-to-end tests for audit campaigns (feature #5)."""

from __future__ import annotations

import uuid

PREFIX = "/api/v1"


def _create(admin_client, **overrides):
    payload = {"name": f"Q3 audit {uuid.uuid4().hex[:6]}"}
    payload.update(overrides)
    resp = admin_client.post(f"{PREFIX}/campaigns", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _run(admin_client, campaign_id):
    resp = admin_client.post(f"{PREFIX}/campaigns/{campaign_id}/run")
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_create_campaign_draft(admin_client):
    c = _create(admin_client, description="Quarterly control review")
    assert c["status"] == "DRAFT"
    assert c["summary"] is None
    assert c["completed_at"] is None


def test_run_campaign_produces_results_and_summary(admin_client):
    c = _create(admin_client)
    ran = _run(admin_client, c["id"])
    assert ran["status"] == "COMPLETED"
    assert ran["completed_at"]
    assert ran["assessment_date"]
    summary = ran["summary"]
    assert summary["total"] > 0
    assert summary["applicable"] >= 0
    assert 0 <= summary["coverage"] <= 100
    assert isinstance(summary["by_status"], dict)

    results = admin_client.get(f"{PREFIX}/campaigns/{c['id']}/results").json()
    assert len(results) == summary["total"]
    for r in results:
        assert r["control_code"]
        assert r["status"]


def test_results_filter_by_status(admin_client):
    c = _create(admin_client)
    _run(admin_client, c["id"])
    all_results = admin_client.get(f"{PREFIX}/campaigns/{c['id']}/results").json()
    statuses = {r["status"] for r in all_results}
    if statuses:
        one = next(iter(statuses))
        filtered = admin_client.get(
            f"{PREFIX}/campaigns/{c['id']}/results", params={"status": one}
        ).json()
        assert all(r["status"] == one for r in filtered)
        assert filtered


def test_scoped_campaign_only_assesses_scope(admin_client):
    regs = admin_client.get(f"{PREFIX}/regulations").json()
    assert regs, "seed should have regulations"
    target = regs[0]
    c = _create(admin_client, scope_regulation_ids=[target["id"]])
    _run(admin_client, c["id"])
    results = admin_client.get(f"{PREFIX}/campaigns/{c['id']}/results").json()
    assert results, "scoped run should still produce results"
    # Every result must belong to the scoped regulation.
    names = {r["regulation_name"] for r in results}
    assert names == {target["name"]}


def test_invalid_scope_rejected(admin_client):
    resp = admin_client.post(
        f"{PREFIX}/campaigns",
        json={"name": "bad", "scope_regulation_ids": [str(uuid.uuid4())]},
    )
    assert resp.status_code == 422


def test_name_required(admin_client):
    resp = admin_client.post(f"{PREFIX}/campaigns", json={"name": "  "})
    assert resp.status_code == 422


def test_completed_campaign_is_immutable(admin_client):
    c = _create(admin_client)
    _run(admin_client, c["id"])
    # Re-running a completed campaign must be refused.
    resp = admin_client.post(f"{PREFIX}/campaigns/{c['id']}/run")
    assert resp.status_code == 409


def test_compare_campaigns(admin_client):
    baseline = _create(admin_client)
    _run(admin_client, baseline["id"])
    current = _create(admin_client)
    _run(admin_client, current["id"])
    cmp = admin_client.get(
        f"{PREFIX}/campaigns/{current['id']}/compare/{baseline['id']}"
    ).json()
    for key in ("regressed", "improved", "added", "removed"):
        assert key in cmp
        assert isinstance(cmp[key], list)


def test_compare_requires_completed(admin_client):
    baseline = _create(admin_client)
    _run(admin_client, baseline["id"])
    draft = _create(admin_client)  # not run
    resp = admin_client.get(f"{PREFIX}/campaigns/{draft['id']}/compare/{baseline['id']}")
    assert resp.status_code == 422


def test_list_and_filter(admin_client):
    c = _create(admin_client)
    _run(admin_client, c["id"])
    completed = admin_client.get(f"{PREFIX}/campaigns", params={"status": "COMPLETED"}).json()
    assert any(x["id"] == c["id"] for x in completed)
    assert all(x["status"] == "COMPLETED" for x in completed)


def test_archive_and_delete(admin_client):
    c = _create(admin_client)
    archived = admin_client.post(f"{PREFIX}/campaigns/{c['id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"
    # Cannot run an archived campaign.
    assert admin_client.post(f"{PREFIX}/campaigns/{c['id']}/run").status_code == 409

    deleted = admin_client.delete(f"{PREFIX}/campaigns/{c['id']}")
    assert deleted.status_code == 204
    assert admin_client.get(f"{PREFIX}/campaigns/{c['id']}").status_code == 404


def test_viewer_cannot_create(client):
    resp = client.post(
        f"{PREFIX}/auth/login",
        json={"email": "viewer@asterlane.demo", "password": "DemoPass123!"},
    )
    me = resp.json()
    client.headers.update({"x-organization-id": me["organization"]["id"]})
    assert client.post(f"{PREFIX}/campaigns", json={"name": "x"}).status_code == 403


def test_requires_auth(client):
    assert client.get(f"{PREFIX}/campaigns").status_code in (401, 403)
