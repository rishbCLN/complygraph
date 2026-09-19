"""Tenant-isolation security tests.

Every data-bearing request is scoped to the caller's organization. A user may
only act within an organization they are a member of; supplying another
organization's id via the ``x-organization-id`` header must be rejected, and one
tenant's data must never appear in another tenant's responses.
"""

from __future__ import annotations

import uuid

import pytest

PREFIX = "/api/v1"
SECOND_ORG_EMAIL = "isolation-admin@beacon.demo"
SECOND_ORG_PASSWORD = "BeaconPass123!"


@pytest.fixture(scope="module")
def second_org():
    """Create an independent second organization with its own admin user."""
    from app.core.database import SessionLocal, utcnow
    from app.core.enums import Role
    from app.models.identity import Membership, Organization, User
    from app.security.passwords import hash_password

    db = SessionLocal()
    try:
        from sqlalchemy import select

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
        user = db.scalar(select(User).where(User.email == SECOND_ORG_EMAIL))
        if user is None:
            user = User(
                email=SECOND_ORG_EMAIL,
                full_name="Beacon Admin",
                password_hash=hash_password(SECOND_ORG_PASSWORD),
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
        return {"org_id": str(org.id), "email": SECOND_ORG_EMAIL}
    finally:
        db.close()


def test_cross_org_header_is_rejected(admin_client, second_org):
    """The asterlane admin cannot scope requests to an org they don't belong to."""
    resp = admin_client.get(
        f"{PREFIX}/findings",
        headers={"x-organization-id": second_org["org_id"]},
    )
    assert resp.status_code == 403


def test_invalid_org_header_is_rejected(admin_client):
    resp = admin_client.get(
        f"{PREFIX}/findings",
        headers={"x-organization-id": "not-a-uuid"},
    )
    assert resp.status_code == 403


def test_unknown_org_header_is_rejected(admin_client):
    resp = admin_client.get(
        f"{PREFIX}/findings",
        headers={"x-organization-id": str(uuid.uuid4())},
    )
    assert resp.status_code == 403


def test_tenant_data_is_isolated(client, second_org):
    """The second org, with no seeded findings, sees an empty findings list even
    though the first org has several."""
    login = client.post(
        f"{PREFIX}/auth/login",
        json={"email": second_org["email"], "password": SECOND_ORG_PASSWORD},
    )
    assert login.status_code == 200, login.text
    client.headers.update({"x-organization-id": second_org["org_id"]})

    me = client.get(f"{PREFIX}/auth/me").json()
    assert me["organization"]["slug"] == "beacon"

    findings = client.get(f"{PREFIX}/findings").json()
    assert findings["total"] == 0
    assert findings["items"] == []
