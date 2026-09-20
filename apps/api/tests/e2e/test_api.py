"""End-to-end API tests against a freshly seeded database.

Exercises the primary read paths a UI depends on plus the AI investigation and
report generation flows, using the demo ADMIN session.
"""

from __future__ import annotations

PREFIX = "/api/v1"


def test_health_and_ready(client):
    assert client.get("/health").json()["status"] == "ok"
    ready = client.get("/ready").json()
    # Postgres/Redis are absent in tests; readiness is degraded but reports AI mode.
    assert ready["ai_mode"] == "deterministic"
    assert "checks" in ready


def test_login_and_me(admin_client):
    me = admin_client.get(f"{PREFIX}/auth/me").json()
    assert me["email"] == "admin@asterlane.demo"
    assert me["role"] == "ADMIN"
    assert me["organization"]["slug"] == "asterlane"


def test_unauthenticated_request_is_rejected(client):
    assert client.get(f"{PREFIX}/findings").status_code in (401, 403)


def test_findings_list_has_expected_shape(admin_client):
    resp = admin_client.get(f"{PREFIX}/findings")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    assert body["items"], "expected at least one seeded finding"
    first = body["items"][0]
    for key in ("id", "title", "severity", "risk_score", "status"):
        assert key in first
    # Findings are ordered by descending risk score.
    scores = [f["risk_score"] for f in body["items"]]
    assert scores == sorted(scores, reverse=True)


def test_finding_detail_roundtrip(admin_client):
    listing = admin_client.get(f"{PREFIX}/findings").json()
    fid = listing["items"][0]["id"]
    detail = admin_client.get(f"{PREFIX}/findings/{fid}")
    assert detail.status_code == 200
    assert detail.json()["id"] == fid


def test_core_inventory_endpoints(admin_client):
    for path in ("assets", "controls", "vendors", "regulations"):
        resp = admin_client.get(f"{PREFIX}/{path}")
        assert resp.status_code == 200, f"{path}: {resp.text}"


def test_dashboard_summary(admin_client):
    resp = admin_client.get(f"{PREFIX}/dashboard/summary")
    assert resp.status_code == 200, resp.text


def test_graph_data_returns_nodes_and_edges(admin_client):
    resp = admin_client.get(f"{PREFIX}/graph/data")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "nodes" in body and "edges" in body
    assert len(body["nodes"]) >= 1


def test_ai_mode_is_deterministic(admin_client):
    assert admin_client.get(f"{PREFIX}/ai/mode").json()["ai_mode"] == "deterministic"


def test_ai_investigation_flow(admin_client):
    fid = admin_client.get(f"{PREFIX}/findings").json()["items"][0]["id"]
    run = admin_client.post(f"{PREFIX}/findings/{fid}/investigate")
    assert run.status_code == 200, run.text
    payload = run.json()
    assert payload["status"] == "COMPLETED"
    inv_id = payload["investigation_id"]

    detail = admin_client.get(f"{PREFIX}/ai/investigations/{inv_id}").json()
    assert detail["input_sanitized"] is True
    assert detail["legal_review_required"] is True
    assert detail["summary"]

    listing = admin_client.get(f"{PREFIX}/ai/investigations", params={"finding_id": fid}).json()
    assert any(i["id"] == inv_id for i in listing)


def test_investigation_is_cached_by_input_hash():
    """At the service layer, an identical sanitized input reuses the cached
    investigation instead of creating a new one.

    (The HTTP endpoint records an audit event on each call, which is part of the
    sanitized input, so cache reuse is exercised here against a stable payload.)
    """
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models.findings import Finding
    from app.models.identity import Organization
    from app.services.ai_service import investigate

    db = SessionLocal()
    try:
        org = db.scalar(select(Organization).where(Organization.slug == "asterlane"))
        finding = db.scalar(select(Finding).where(Finding.organization_id == org.id))
        first = investigate(db, org, finding)
        second = investigate(db, org, finding)
        assert first.id == second.id
        assert second.status == "COMPLETED"
    finally:
        db.close()


def test_executive_report_json_and_pdf(admin_client):
    execu = admin_client.get(f"{PREFIX}/reports/executive")
    assert execu.status_code == 200, execu.text

    pdf = admin_client.get(f"{PREFIX}/reports/executive/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF"


def test_findings_csv_report(admin_client):
    resp = admin_client.get(f"{PREFIX}/reports/findings", params={"fmt": "csv"})
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert resp.text.strip(), "CSV body should not be empty"


def test_system_report_json_carries_citations_and_provenance(admin_client):
    """The per-system regulator report enriches every control with its legal
    citation + honest legal-status label, and every fact with its provenance."""
    systems = admin_client.get(f"{PREFIX}/systems").json()
    # Pick the BFSI credit-scoring system (has the richest control set).
    target = next(
        (s for s in systems if s["sector"] == "bfsi"), systems[0]
    )
    resp = admin_client.get(f"{PREFIX}/reports/system/{target['id']}")
    assert resp.status_code == 200, resp.text
    report = resp.json()

    assert report["system"]["id"] == target["id"]
    assert report["controls"], "expected AI-scoped controls in the report"
    assert report["regulations"], "expected regulations-in-scope rollup"
    assert "disclaimer" in report

    for c in report["controls"]:
        cite = c["citation"]
        assert cite["regulation"]
        assert cite["legal_status"]
        assert cite["legal_status_label"]
        assert "citation_verified" in cite

    # Provenance is attached for the derived facts.
    assert report["fact_provenance"]["sector"]["confidence"] == "DECLARED"

    # Honest legal labelling: RBI direction is not collapsed into "law".
    labels = {r["regulation"]: r["legal_status_label"] for r in report["regulations"]}
    assert any("direction" in v.lower() or "framework" in v.lower() or "guidance" in v.lower()
               for v in labels.values())


def test_system_report_pdf(admin_client):
    systems = admin_client.get(f"{PREFIX}/systems").json()
    target = next((s for s in systems if s["sector"] == "bfsi"), systems[0])
    resp = admin_client.get(f"{PREFIX}/reports/system/{target['id']}/pdf")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_system_report_requires_capability(admin_client, client):
    """A viewer without generate_reports cannot pull a system report."""
    systems = admin_client.get(f"{PREFIX}/systems").json()
    sid = systems[0]["id"]
    login = client.post(
        f"{PREFIX}/auth/login",
        json={"email": "viewer@asterlane.demo", "password": "DemoPass123!"},
    )
    assert login.status_code == 200, login.text
    client.headers.update({"x-organization-id": login.json()["organization"]["id"]})
    resp = client.get(f"{PREFIX}/reports/system/{sid}")
    assert resp.status_code == 403, resp.text
