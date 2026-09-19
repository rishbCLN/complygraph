"""Tests for the control-overlay graph (controls -> evidence -> findings)."""

from __future__ import annotations


def test_control_graph_shape(admin_client):
    resp = admin_client.get("/api/v1/graph/control")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "nodes" in body and "edges" in body and "stats" in body

    kinds = {n["kind"] for n in body["nodes"]}
    # The seeded org has controls; there should be CONTROL nodes at minimum.
    assert "CONTROL" in kinds
    assert body["stats"]["controls"] > 0

    # Every edge references node ids that exist.
    node_ids = {n["id"] for n in body["nodes"]}
    for edge in body["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids


def test_control_graph_links_findings_to_controls(admin_client):
    body = admin_client.get("/api/v1/graph/control").json()
    control_ids = {n["id"] for n in body["nodes"] if n["kind"] == "CONTROL"}
    raised = [e for e in body["edges"] if e["relation"] == "RAISED"]
    # Seeded data includes control-driven findings.
    for e in raised:
        assert e["source"] in control_ids
