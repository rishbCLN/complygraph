"""End-to-end tests for the risk register (feature #3)."""

from __future__ import annotations

import pytest

PREFIX = "/api/v1"


@pytest.fixture
def viewer_client(client):
    """A read-only VIEWER session (lacks the manage_risk capability)."""
    resp = client.post(
        f"{PREFIX}/auth/login",
        json={"email": "viewer@asterlane.demo", "password": "DemoPass123!"},
    )
    assert resp.status_code == 200, resp.text
    me = resp.json()
    client.headers.update({"x-organization-id": me["organization"]["id"]})
    return client


def _create(admin_client, **overrides):
    payload = {
        "title": "Unencrypted backups",
        "category": "SECURITY",
        "inherent_likelihood": 4,
        "inherent_impact": 5,
        "residual_likelihood": 2,
        "residual_impact": 4,
        "single_loss_expectancy": 50000,
        "annual_rate_of_occurrence": 0.5,
    }
    payload.update(overrides)
    resp = admin_client.post(f"{PREFIX}/risks", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_computes_scores_and_ale(admin_client):
    risk = _create(admin_client)
    # inherent 4*5=20 -> CRITICAL, residual 2*4=8 -> MEDIUM
    assert risk["inherent_score"] == 20
    assert risk["inherent_severity"] == "CRITICAL"
    assert risk["residual_score"] == 8
    assert risk["residual_severity"] == "MEDIUM"
    # ALE = 50000 * 0.5
    assert risk["ale"] == 25000.0
    assert risk["status"] == "IDENTIFIED"


def test_scores_clamped_to_1_5(admin_client):
    risk = _create(admin_client, inherent_likelihood=99, inherent_impact=0)
    assert risk["inherent_likelihood"] == 5
    assert risk["inherent_impact"] == 1


def test_title_required(admin_client):
    resp = admin_client.post(f"{PREFIX}/risks", json={"title": "   "})
    assert resp.status_code == 422


def test_bad_enum_rejected(admin_client):
    resp = admin_client.post(f"{PREFIX}/risks", json={"title": "X", "category": "NONSENSE"})
    assert resp.status_code == 422


def test_get_and_list_and_filter(admin_client):
    created = _create(admin_client, title="Vendor lock-in", category="VENDOR")
    got = admin_client.get(f"{PREFIX}/risks/{created['id']}")
    assert got.status_code == 200
    assert got.json()["title"] == "Vendor lock-in"

    listed = admin_client.get(f"{PREFIX}/risks", params={"category": "VENDOR"}).json()
    assert any(r["id"] == created["id"] for r in listed)
    assert all(r["category"] == "VENDOR" for r in listed)


def test_update_recomputes(admin_client):
    risk = _create(admin_client)
    resp = admin_client.patch(
        f"{PREFIX}/risks/{risk['id']}",
        json={"residual_likelihood": 1, "residual_impact": 1, "treatment_plan": "Encrypt at rest"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["residual_score"] == 1
    assert body["residual_severity"] == "LOW"
    assert body["treatment_plan"] == "Encrypt at rest"


def test_accept_workflow(admin_client):
    risk = _create(admin_client)
    resp = admin_client.post(
        f"{PREFIX}/risks/{risk['id']}/accept",
        json={"rationale": "Residual is within appetite for this quarter.",
              "expires_at": "2027-01-01T00:00:00Z"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ACCEPTED"
    assert body["treatment_strategy"] == "ACCEPT"
    assert body["accepted_by"]
    assert body["accepted_at"]
    assert body["acceptance_rationale"].startswith("Residual")
    assert body["review_due_at"] is not None


def test_accept_requires_rationale(admin_client):
    risk = _create(admin_client)
    resp = admin_client.post(f"{PREFIX}/risks/{risk['id']}/accept", json={"rationale": "  "})
    assert resp.status_code == 422


def test_close_and_delete(admin_client):
    risk = _create(admin_client)
    closed = admin_client.post(f"{PREFIX}/risks/{risk['id']}/close")
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"

    deleted = admin_client.delete(f"{PREFIX}/risks/{risk['id']}")
    assert deleted.status_code == 204
    assert admin_client.get(f"{PREFIX}/risks/{risk['id']}").status_code == 404


def test_summary_heatmap_and_totals(admin_client):
    _create(admin_client, residual_likelihood=5, residual_impact=5)  # CRITICAL corner
    summary = admin_client.get(f"{PREFIX}/risks/summary").json()
    assert summary["total"] >= 1
    assert len(summary["heatmap"]) == 5
    assert all(len(row) == 5 for row in summary["heatmap"])
    # The 5x5 residual (impact idx 4, likelihood idx 4) cell must be populated.
    assert summary["heatmap"][4][4] >= 1
    assert summary["by_severity"]["CRITICAL"] >= 1
    assert summary["total_ale"] >= 0


def test_viewer_cannot_mutate(viewer_client):
    resp = viewer_client.post(f"{PREFIX}/risks", json={"title": "X"})
    assert resp.status_code == 403


def test_requires_auth(client):
    assert client.get(f"{PREFIX}/risks").status_code in (401, 403)


def test_not_found_scoped(admin_client):
    import uuid

    assert admin_client.get(f"{PREFIX}/risks/{uuid.uuid4()}").status_code == 404
