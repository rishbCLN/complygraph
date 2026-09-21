"""End-to-end tests for custom regulatory pack authoring (feature #2)."""

from __future__ import annotations

PREFIX = "/api/v1"

_SAMPLE_YAML = """
pack:
  name: "AsterLane Internal Security Standard"
  jurisdiction: "Internal"
  version: "1.0"
  legal_status: "INTERNAL_POLICY"
  source_document: "AsterLane InfoSec Policy v1.0"
obligations:
  - code: "ASL-OBL-1"
    title: "Access governance"
    description: "Least-privilege access to production data."
    legal_status: "INTERNAL_POLICY"
    controls:
      - code: "ASL-AC-001"
        title: "MFA enforced for production access"
        category: "SECURITY"
        severity: "HIGH"
      - code: "ASL-AC-002"
        title: "Quarterly access review"
        category: "SECURITY"
        severity: "MEDIUM"
"""


def test_import_yaml_pack_and_visibility(admin_client):
    resp = admin_client.post(
        f"{PREFIX}/regulations/packs/import",
        json={"format": "yaml", "content": _SAMPLE_YAML},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["is_custom"] is True
    assert body["obligation_count"] == 1
    reg_id = body["id"]

    # It shows in the org's regulation list and in the custom-packs list.
    regs = admin_client.get(f"{PREFIX}/regulations").json()
    assert any(r["id"] == reg_id for r in regs)
    packs = admin_client.get(f"{PREFIX}/regulations/packs").json()
    assert any(p["id"] == reg_id for p in packs)
    assert all(p["is_custom"] for p in packs)

    # Its controls are visible in the controls list.
    controls = admin_client.get(f"{PREFIX}/controls").json()
    codes = {c["code"] for c in controls}
    assert {"ASL-AC-001", "ASL-AC-002"} <= codes

    # Cleanup / delete path.
    deleted = admin_client.delete(f"{PREFIX}/regulations/packs/{reg_id}")
    assert deleted.status_code == 204, deleted.text
    controls_after = admin_client.get(f"{PREFIX}/controls").json()
    assert "ASL-AC-001" not in {c["code"] for c in controls_after}


def test_import_rejects_invalid_pack(admin_client):
    # Missing controls entirely.
    bad = admin_client.post(
        f"{PREFIX}/regulations/packs/import",
        json={
            "format": "yaml",
            "content": "pack:\n  name: Empty\nobligations: []\n",
        },
    )
    assert bad.status_code == 422, bad.text

    # Invalid legal_status.
    bad2 = admin_client.post(
        f"{PREFIX}/regulations/packs/import",
        json={
            "format": "yaml",
            "content": (
                "pack:\n  name: Bad\n  legal_status: NONSENSE\n"
                "obligations:\n  - code: O1\n    title: t\n    controls:\n"
                "      - code: C1\n        title: c\n"
            ),
        },
    )
    assert bad2.status_code == 422, bad2.text


def test_import_rejects_duplicate_control_code(admin_client):
    # DPDP-NOTICE-001 is a shipped control code; reusing it must be rejected.
    dup = admin_client.post(
        f"{PREFIX}/regulations/packs/import",
        json={
            "format": "yaml",
            "content": (
                "pack:\n  name: Collide\nobligations:\n  - code: O1\n"
                "    title: t\n    controls:\n      - code: DPDP-NOTICE-001\n"
                "        title: dup\n"
            ),
        },
    )
    assert dup.status_code == 422, dup.text
    assert "already exist" in dup.json()["error"]["message"].lower()


def test_create_pack_structured(admin_client):
    resp = admin_client.post(
        f"{PREFIX}/regulations/packs",
        json={
            "pack": {"name": "Structured Pack", "legal_status": "BEST_PRACTICE"},
            "obligations": [
                {
                    "code": "SP-O1",
                    "title": "Obligation one",
                    "controls": [
                        {"code": "SP-C-001", "title": "Control one", "severity": "LOW"}
                    ],
                }
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    reg_id = resp.json()["id"]
    obligations = admin_client.get(f"{PREFIX}/regulations/{reg_id}/obligations").json()
    assert obligations[0]["code"] == "SP-O1"
    admin_client.delete(f"{PREFIX}/regulations/packs/{reg_id}")


def test_cannot_delete_system_regulation(admin_client):
    regs = admin_client.get(f"{PREFIX}/regulations").json()
    system = next(r for r in regs if not r["is_custom"])
    resp = admin_client.delete(f"{PREFIX}/regulations/packs/{system['id']}")
    # System regulation is not an org custom pack -> rejected.
    assert resp.status_code in (404, 422), resp.text
