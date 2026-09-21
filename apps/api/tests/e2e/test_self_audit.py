"""End-to-end tests for the self-audit / data-quality engine (feature #9)."""

from __future__ import annotations

PREFIX = "/api/v1"


def test_self_audit_shape_and_scoring(admin_client):
    resp = admin_client.get(f"{PREFIX}/self-audit")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert 0 <= body["overall_score"] <= 100
    assert body["check_count"] == len(body["checks"])
    assert body["checks"], "expected quality checks"
    for check in body["checks"]:
        assert 0 <= check["score"] <= 100
        assert check["complete"] + check["incomplete"] == check["total"]
        for key in ("key", "title", "category", "severity", "recommendation"):
            assert key in check


def test_self_audit_detects_seeded_gaps(admin_client):
    body = admin_client.get(f"{PREFIX}/self-audit").json()
    by_key = {c["key"]: c for c in body["checks"]}

    # The seed intentionally has a vendor (PulseMetrics / NovaModel) with a
    # MISSING contract handling personal data -> vendor_contracts must flag it.
    assert "vendor_contracts" in by_key
    assert by_key["vendor_contracts"]["incomplete"] >= 1

    # The seed has a marketing activity with no retention period defined.
    assert by_key["retention_defined"]["incomplete"] >= 1

    # The seed has a production AI system left NOT_REVIEWED.
    assert by_key["ai_system_review"]["incomplete"] >= 1


def test_self_audit_items_capped_and_typed(admin_client):
    body = admin_client.get(f"{PREFIX}/self-audit").json()
    for check in body["checks"]:
        assert len(check["items"]) <= 25
        for item in check["items"]:
            assert set(item.keys()) == {"type", "id", "label", "detail"}


def test_self_audit_requires_auth(client):
    assert client.get(f"{PREFIX}/self-audit").status_code in (401, 403)
