"""AI-system inventory endpoint tests (Phase 2).

Covers the AI-system-centric inventory: CRUD, structured architecture import,
the per-system architecture graph, the derived applicability facts the analysis
engine consumes, RBAC on mutations, and tenant isolation.

These exercise the spine the Phase 3 applicability engine builds on, so the
assertions focus on the facts/graph contract rather than any legal conclusion
(the engine never lives here).
"""

from __future__ import annotations

import pytest

PREFIX = "/api/v1"


# --- Helpers --------------------------------------------------------------------


def _viewer_client(client):
    """A TestClient authenticated as the demo VIEWER (no manage_inventory)."""
    login = client.post(
        f"{PREFIX}/auth/login",
        json={"email": "viewer@asterlane.demo", "password": "DemoPass123!"},
    )
    assert login.status_code == 200, login.text
    org_id = login.json()["organization"]["id"]
    client.headers.update({"x-organization-id": org_id})
    return client


def _first_vendor_name(admin_client) -> str | None:
    body = admin_client.get(f"{PREFIX}/vendors").json()
    items = body.get("items", body) if isinstance(body, dict) else body
    return items[0]["name"] if items else None


# --- CRUD -----------------------------------------------------------------------


def test_create_and_get_system(admin_client):
    payload = {
        "name": "Fraud Triage Assistant",
        "description": "Flags suspicious transactions for human review.",
        "system_type": "ML_MODEL",
        "sector": "BFSI",
        "lifecycle_stage": "PRODUCTION",
        "processes_personal_data": True,
        "makes_automated_decisions": True,
        "regions": ["India"],
    }
    resp = admin_client.post(f"{PREFIX}/systems", json=payload)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["name"] == "Fraud Triage Assistant"
    # Enum-backed fields are normalized/echoed back.
    assert created["system_type"] == "ML_MODEL"
    assert created["lifecycle_stage"] == "PRODUCTION"
    assert created["sector"] == "bfsi"  # sector is lowercased
    assert created["processes_personal_data"] is True
    assert created["makes_automated_decisions"] is True
    assert created["component_count"] == 0
    assert created["flow_count"] == 0

    got = admin_client.get(f"{PREFIX}/systems/{created['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == created["id"]


def test_list_systems_includes_created(admin_client):
    resp = admin_client.post(
        f"{PREFIX}/systems", json={"name": "Listed System", "system_type": "LLM"}
    )
    assert resp.status_code == 201, resp.text
    sid = resp.json()["id"]
    listing = admin_client.get(f"{PREFIX}/systems")
    assert listing.status_code == 200
    assert any(s["id"] == sid for s in listing.json())


def test_create_system_requires_name(admin_client):
    resp = admin_client.post(f"{PREFIX}/systems", json={"name": "   "})
    assert resp.status_code == 422, resp.text


def test_invalid_enum_is_rejected(admin_client):
    resp = admin_client.post(
        f"{PREFIX}/systems",
        json={"name": "Bad Enum", "system_type": "NOT_A_TYPE"},
    )
    assert resp.status_code == 422, resp.text


def test_defaults_applied_when_optional_fields_omitted(admin_client):
    resp = admin_client.post(f"{PREFIX}/systems", json={"name": "Minimal System"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["system_type"] == "OTHER"
    assert body["lifecycle_stage"] == "DEVELOPMENT"
    assert body["review_status"] == "NOT_REVIEWED"
    assert body["sector"] == "general"
    assert body["processes_personal_data"] is False
    assert body["makes_automated_decisions"] is False
    assert body["high_risk"] is False


def test_patch_updates_fields(admin_client):
    created = admin_client.post(
        f"{PREFIX}/systems", json={"name": "Patch Target", "system_type": "LLM"}
    ).json()
    resp = admin_client.patch(
        f"{PREFIX}/systems/{created['id']}",
        json={"owner": "privacy@asterlane.demo", "high_risk": True},
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["owner"] == "privacy@asterlane.demo"
    assert updated["high_risk"] is True


def test_review_status_sets_last_reviewed_at(admin_client):
    created = admin_client.post(
        f"{PREFIX}/systems", json={"name": "Review Me", "system_type": "RAG"}
    ).json()
    assert created["last_reviewed_at"] is None
    resp = admin_client.patch(
        f"{PREFIX}/systems/{created['id']}", json={"review_status": "REVIEWED"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["review_status"] == "REVIEWED"
    assert resp.json()["last_reviewed_at"] is not None


def test_get_missing_system_is_404(admin_client):
    import uuid

    resp = admin_client.get(f"{PREFIX}/systems/{uuid.uuid4()}")
    assert resp.status_code == 404, resp.text


# --- Architecture import --------------------------------------------------------


def test_import_architecture_builds_components_and_flows(admin_client):
    vendor_name = _first_vendor_name(admin_client)
    body = {
        "system": {
            "name": "Support Copilot",
            "system_type": "LLM",
            "sector": "general",
            "lifecycle_stage": "PRODUCTION",
            "processes_personal_data": True,
            "regions": ["India"],
        },
        "components": [
            {
                "key": "llm",
                "name": "External LLM",
                "type": "MODEL",
                "external": True,
                "region": "us",
                "provider": "external_llm",
                "vendor": vendor_name,
            },
            {"key": "store", "name": "Vector Store", "type": "DATA_STORE", "region": "India"},
        ],
        "flows": [
            {
                "from": "store",
                "to": "llm",
                "relation": "SENDS_TO",
                "contains_personal_data": True,
                "cross_border": True,
            }
        ],
    }
    resp = admin_client.post(f"{PREFIX}/systems/import", json=body)
    assert resp.status_code == 201, resp.text
    system = resp.json()
    assert system["component_count"] == 2
    assert system["flow_count"] == 1

    sid = system["id"]
    components = admin_client.get(f"{PREFIX}/systems/{sid}/components").json()
    assert len(components) == 2
    llm = next(c for c in components if c["name"] == "External LLM")
    assert llm["external"] is True
    if vendor_name:
        assert llm["vendor_id"] is not None

    flows = admin_client.get(f"{PREFIX}/systems/{sid}/flows").json()
    assert len(flows) == 1
    assert flows[0]["cross_border"] is True
    assert flows[0]["contains_personal_data"] is True


def test_import_rejects_flow_referencing_unknown_component(admin_client):
    body = {
        "system": {"name": "Broken Wiring", "system_type": "LLM"},
        "components": [{"key": "a", "name": "Comp A", "type": "SERVICE"}],
        "flows": [{"from": "a", "to": "ghost", "relation": "SENDS_TO"}],
    }
    resp = admin_client.post(f"{PREFIX}/systems/import", json=body)
    assert resp.status_code == 422, resp.text
    assert "ghost" in resp.text


def test_import_rejects_unknown_vendor_reference(admin_client):
    import uuid

    body = {
        "system": {"name": "Phantom Vendor", "system_type": "LLM"},
        "components": [
            {
                "key": "c",
                "name": "Comp",
                "type": "SERVICE",
                "vendor_id": str(uuid.uuid4()),
            }
        ],
        "flows": [],
    }
    resp = admin_client.post(f"{PREFIX}/systems/import", json=body)
    assert resp.status_code == 422, resp.text


# --- Graph ----------------------------------------------------------------------


def test_system_graph_shape(admin_client):
    body = {
        "system": {"name": "Graphed System", "system_type": "RAG"},
        "components": [
            {"key": "m", "name": "Model", "type": "MODEL", "external": True, "region": "us"},
            {"key": "d", "name": "Docs", "type": "DATA_STORE", "region": "India"},
        ],
        "flows": [
            {"from": "d", "to": "m", "relation": "SENDS_TO", "cross_border": True},
        ],
    }
    sid = admin_client.post(f"{PREFIX}/systems/import", json=body).json()["id"]
    graph = admin_client.get(f"{PREFIX}/systems/{sid}/graph").json()

    assert "nodes" in graph and "edges" in graph and "stats" in graph
    # The system node is present and marked as the center.
    system_nodes = [n for n in graph["nodes"] if n["type"] == "system"]
    assert len(system_nodes) == 1
    assert system_nodes[0]["center"] is True
    # Both components appear as component nodes.
    component_nodes = [n for n in graph["nodes"] if n["type"] == "component"]
    assert len(component_nodes) == 2
    assert graph["stats"]["components"] == 2
    assert graph["stats"]["flows"] == 1
    assert graph["stats"]["cross_border_flows"] == 1
    assert graph["stats"]["external_components"] == 1


# --- Derived facts --------------------------------------------------------------


def test_facts_reflect_declared_and_derived_signals(admin_client):
    vendor_name = _first_vendor_name(admin_client)
    body = {
        "system": {
            "name": "Facts System",
            "system_type": "LLM",
            "sector": "BFSI",
            "lifecycle_stage": "PRODUCTION",
            "processes_personal_data": True,
            "makes_automated_decisions": True,
            "regions": ["India"],
        },
        "components": [
            {
                "key": "llm",
                "name": "Hosted LLM",
                "type": "MODEL",
                "external": True,
                "region": "us",
                "vendor": vendor_name,
            },
            {"key": "store", "name": "Store", "type": "DATA_STORE", "region": "India"},
        ],
        "flows": [
            {"from": "store", "to": "llm", "relation": "SENDS_TO", "cross_border": True},
        ],
    }
    sid = admin_client.post(f"{PREFIX}/systems/import", json=body).json()["id"]
    facts = admin_client.get(f"{PREFIX}/systems/{sid}/facts").json()

    # Declared facts pass through unchanged.
    assert facts["sector"] == "bfsi"
    assert facts["system_type"] == "LLM"
    assert facts["processes_personal_data"] is True
    assert facts["makes_automated_decisions"] is True
    assert facts["is_production"] is True
    # Derived structural facts.
    assert facts["has_external_components"] is True
    assert facts["has_external_inference"] is True  # external MODEL component
    assert facts["has_cross_border_flow"] is True
    assert "us" in facts["non_india_regions"]
    assert facts["component_count"] == 2
    assert facts["flow_count"] == 1
    if vendor_name:
        assert facts["has_vendors"] is True
        assert facts["vendor_ids"]


def test_facts_for_bare_system_have_no_false_positives(admin_client):
    sid = admin_client.post(
        f"{PREFIX}/systems",
        json={"name": "Bare System", "system_type": "OTHER"},
    ).json()["id"]
    facts = admin_client.get(f"{PREFIX}/systems/{sid}/facts").json()
    # Nothing declared or wired -> every derived signal is false/empty.
    assert facts["has_vendors"] is False
    assert facts["has_external_components"] is False
    assert facts["has_external_inference"] is False
    assert facts["has_cross_border_flow"] is False
    assert facts["non_india_regions"] == []
    assert facts["owner_assigned"] is False
    assert facts["is_reviewed"] is False


# --- Per-system analysis --------------------------------------------------------


def test_analyze_system_returns_scoped_control_report(admin_client):
    """POST /systems/{id}/analyze returns per-control statuses + reasons scoped to
    the system, driven by its derived facts."""
    vendor_name = _first_vendor_name(admin_client)
    body = {
        "system": {
            "name": "Analyze Me BFSI",
            "system_type": "LLM",
            "sector": "BFSI",
            "lifecycle_stage": "PRODUCTION",
            "processes_personal_data": True,
            "makes_automated_decisions": True,
            "high_risk": True,
            "regions": ["India"],
        },
        "components": [
            {
                "key": "llm",
                "name": "Hosted LLM",
                "type": "MODEL",
                "external": True,
                "region": "us",
                "vendor": vendor_name,
            },
            {"key": "apm", "name": "APM", "type": "SERVICE", "external": True, "region": "us"},
            {"key": "store", "name": "Store", "type": "DATA_STORE", "region": "India"},
        ],
        "flows": [
            {"from": "store", "to": "llm", "relation": "SENDS_TO", "cross_border": True},
        ],
    }
    sid = admin_client.post(f"{PREFIX}/systems/import", json=body).json()["id"]

    resp = admin_client.post(f"{PREFIX}/systems/{sid}/analyze")
    assert resp.status_code == 200, resp.text
    report = resp.json()

    assert report["system_id"] == sid
    assert report["facts"]["sector"] == "bfsi"
    assert report["summary"]["total"] > 0
    assert isinstance(report["summary"]["by_status"], dict)

    status = {c["code"]: c["status"] for c in report["controls"]}
    assert status["RBI-LOCALIZATION-001"] == "FAIL"
    assert status["RBI-LOGGING-001"] == "NEEDS_REVIEW"
    assert status["RBI-INFERENCE-001"] == "NEEDS_REVIEW"
    assert status["MEITY-BIAS-001"] == "NO_EVIDENCE"

    # Each entry carries a human-readable reason and a scope tag.
    localization = next(c for c in report["controls"] if c["code"] == "RBI-LOCALIZATION-001")
    assert localization["reason"]
    assert localization["scope"] == "system"
    assert localization["applicable"] is True


def test_analyze_general_system_gates_bfsi_controls(admin_client):
    """A general, low-risk system reports BFSI/condition-scoped controls as
    NOT_APPLICABLE rather than as findings."""
    body = {
        "system": {
            "name": "Analyze Me General",
            "system_type": "RAG",
            "sector": "general",
            "lifecycle_stage": "DEVELOPMENT",
            "processes_personal_data": False,
            "makes_automated_decisions": False,
            "high_risk": False,
            "regions": ["India"],
        },
        "components": [{"key": "idx", "name": "Index", "type": "DATA_STORE", "region": "India"}],
        "flows": [],
    }
    sid = admin_client.post(f"{PREFIX}/systems/import", json=body).json()["id"]
    report = admin_client.post(f"{PREFIX}/systems/{sid}/analyze").json()
    status = {c["code"]: c["status"] for c in report["controls"]}

    assert status["RBI-LOCALIZATION-001"] == "NOT_APPLICABLE"
    assert status["RBI-VENDOR-001"] == "NOT_APPLICABLE"
    assert status["MEITY-OVERSIGHT-001"] == "NOT_APPLICABLE"
    # Org-wide controls still evaluate.
    assert status["CERTIN-LOGS-001"] == "NO_EVIDENCE"


def test_analyze_requires_capability(admin_client, client):
    """A viewer (no assess_controls capability) cannot analyze a system."""
    sid = admin_client.post(
        f"{PREFIX}/systems", json={"name": "Perm Check", "system_type": "LLM", "sector": "bfsi"}
    ).json()["id"]
    viewer = _viewer_client(client)
    resp = viewer.post(f"{PREFIX}/systems/{sid}/analyze")
    assert resp.status_code == 403, resp.text


# --- RBAC -----------------------------------------------------------------------


def test_viewer_cannot_create_system(client):
    viewer = _viewer_client(client)
    resp = viewer.post(f"{PREFIX}/systems", json={"name": "Blocked", "system_type": "LLM"})
    assert resp.status_code == 403, resp.text


def test_viewer_can_read_systems(client):
    viewer = _viewer_client(client)
    resp = viewer.get(f"{PREFIX}/systems")
    assert resp.status_code == 200, resp.text


def test_unauthenticated_cannot_list_systems(client):
    assert client.get(f"{PREFIX}/systems").status_code in (401, 403)


# --- Tenant isolation -----------------------------------------------------------


def test_systems_are_tenant_isolated(admin_client):
    """A system created in asterlane is not visible to the second org, and the
    second org cannot read it by id."""
    from app.core.database import SessionLocal, utcnow
    from app.core.enums import Role
    from app.models.identity import Membership, Organization, User
    from app.security.passwords import hash_password
    from sqlalchemy import select

    # Create a system in asterlane.
    sid = admin_client.post(
        f"{PREFIX}/systems", json={"name": "Tenant A System", "system_type": "LLM"}
    ).json()["id"]

    # Ensure an isolated second org + admin exist.
    email = "aisys-isolation@beacon.demo"
    password = "BeaconPass123!"
    db = SessionLocal()
    try:
        org = db.scalar(select(Organization).where(Organization.slug == "beacon"))
        if org is None:
            org = Organization(
                name="Beacon Data Ltd.",
                slug="beacon",
                industry="Fintech",
                country="India",
                plan="STARTER",
                assessment_date=utcnow(),
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(org)
            db.flush()
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                full_name="Beacon AI Admin",
                password_hash=hash_password(password),
                is_active=True,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(user)
            db.flush()
        membership = db.scalar(
            select(Membership).where(
                Membership.user_id == user.id, Membership.organization_id == org.id
            )
        )
        if membership is None:
            db.add(
                Membership(
                    organization_id=org.id,
                    user_id=user.id,
                    role=Role.ADMIN.value,
                    created_at=utcnow(),
                )
            )
        db.commit()
        beacon_org_id = str(org.id)
    finally:
        db.close()

    # Log in as the second org and confirm isolation.
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c2:
        login = c2.post(
            f"{PREFIX}/auth/login", json={"email": email, "password": password}
        )
        assert login.status_code == 200, login.text
        c2.headers.update({"x-organization-id": beacon_org_id})

        listing = c2.get(f"{PREFIX}/systems").json()
        assert all(s["id"] != sid for s in listing)

        # Cross-tenant read by id is a 404 (not found in this org).
        assert c2.get(f"{PREFIX}/systems/{sid}").status_code == 404
