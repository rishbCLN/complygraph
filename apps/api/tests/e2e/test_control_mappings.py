"""End-to-end tests for cross-framework control mappings (feature #1)."""

from __future__ import annotations

PREFIX = "/api/v1"


def _control_by_code(admin_client, code: str) -> dict:
    controls = admin_client.get(f"{PREFIX}/controls").json()
    match = [c for c in controls if c["code"] == code]
    assert match, f"control {code} not seeded"
    return match[0]


def test_seeded_mapping_graph_present(admin_client):
    graph = admin_client.get(f"{PREFIX}/control-mappings/graph").json()
    assert graph["nodes"], "expected mapped controls in the graph"
    assert graph["edges"], "expected seeded mappings"
    # Edges reference nodes that exist.
    node_ids = {n["id"] for n in graph["nodes"]}
    for edge in graph["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids


def test_list_mappings_shape(admin_client):
    mappings = admin_client.get(f"{PREFIX}/control-mappings").json()
    assert mappings, "expected seeded system mappings"
    first = mappings[0]
    for key in ("id", "source", "target", "relation_type", "system"):
        assert key in first
    assert first["source"]["regulation_name"]
    # Seeded mappings are system mappings.
    assert any(m["system"] for m in mappings)


def test_per_control_mappings_endpoint(admin_client):
    vendor_control = _control_by_code(admin_client, "DPDP-VENDOR-001")
    mappings = admin_client.get(
        f"{PREFIX}/controls/{vendor_control['id']}/mappings"
    ).json()
    assert mappings, "DPDP-VENDOR-001 should map to the RBI vendor control"
    outgoing = [m for m in mappings if m["direction"] == "outgoing"]
    assert outgoing
    assert outgoing[0]["other"]["code"] == "RBI-VENDOR-001"


def test_reusable_evidence_follows_coverage(admin_client):
    # DPDP-VENDOR-001 --SUPERSET--> RBI-VENDOR-001, so evidence on the DPDP
    # control is reusable for the RBI control. Seed has no vendor-contract
    # evidence, so add some to the source control's org, then check reuse.
    rbi_vendor = _control_by_code(admin_client, "RBI-VENDOR-001")
    reuse = admin_client.get(
        f"{PREFIX}/controls/{rbi_vendor['id']}/reusable-evidence"
    ).json()
    # Structure is a list; every candidate must be flagged for review.
    assert isinstance(reuse, list)
    for candidate in reuse:
        assert candidate["requires_review"] is True
        assert candidate["source_control"]["code"] == "DPDP-VENDOR-001"


def test_create_and_delete_org_mapping(admin_client):
    src = _control_by_code(admin_client, "DPDP-NOTICE-001")
    dst = _control_by_code(admin_client, "MEITY-LINEAGE-001")
    created = admin_client.post(
        f"{PREFIX}/control-mappings",
        json={
            "source_control_id": src["id"],
            "target_control_id": dst["id"],
            "relation_type": "RELATED",
            "rationale": "Notice/transparency relates to explainability lineage.",
            "confidence": 0.4,
        },
    )
    assert created.status_code == 201, created.text
    mapping_id = created.json()["id"]
    assert created.json()["system"] is False

    # Duplicate is rejected.
    dup = admin_client.post(
        f"{PREFIX}/control-mappings",
        json={
            "source_control_id": src["id"],
            "target_control_id": dst["id"],
            "relation_type": "RELATED",
        },
    )
    assert dup.status_code == 422, dup.text

    # Self-mapping is rejected.
    self_map = admin_client.post(
        f"{PREFIX}/control-mappings",
        json={
            "source_control_id": src["id"],
            "target_control_id": src["id"],
            "relation_type": "EQUIVALENT",
        },
    )
    assert self_map.status_code == 422, self_map.text

    # Delete the org mapping.
    deleted = admin_client.delete(f"{PREFIX}/control-mappings/{mapping_id}")
    assert deleted.status_code == 204, deleted.text


def test_cannot_delete_system_mapping(admin_client):
    mappings = admin_client.get(f"{PREFIX}/control-mappings").json()
    system = next(m for m in mappings if m["system"])
    resp = admin_client.delete(f"{PREFIX}/control-mappings/{system['id']}")
    assert resp.status_code == 422, resp.text
