"""Shared pytest fixtures.

The database URL is pointed at a throwaway SQLite file BEFORE any application
module is imported, so the real ``complygraph.db`` is never touched and every
test run starts from a clean, seeded state.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

import pytest

# --- Redirect the database to a temp file before importing the app -------------
_TEST_DB_DIR = Path(tempfile.gettempdir()) / "complygraph-tests"
_TEST_DB_DIR.mkdir(parents=True, exist_ok=True)
_TEST_DB_PATH = _TEST_DB_DIR / f"test-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH.as_posix()}"
os.environ.setdefault("AI_MODE", "deterministic")
os.environ.setdefault("ANTHROPIC_API_KEY", "")
# Domain-event webhook dispatch is a no-op under test so seeded/created endpoints
# never make real outbound HTTP calls. Delivery is exercised explicitly via the
# ``/test`` endpoint and monkeypatched ``_deliver_once`` in test_integrations.py.
os.environ.setdefault("WEBHOOKS_ENABLED", "false")


@pytest.fixture(scope="session", autouse=True)
def _seeded_database():
    """Create the schema and seed the demo data exactly once per session."""
    from app import seed as seed_module

    seed_module.run()
    yield
    # Best-effort cleanup of the temp database file.
    from app.core.database import engine

    engine.dispose()
    try:
        _TEST_DB_PATH.unlink(missing_ok=True)
    except OSError:
        pass


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _login(client, email: str = "admin@asterlane.demo", password: str = "DemoPass123!"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    # Demo accounts have no MFA, so login returns the user payload directly.
    # (MFA-enabled accounts instead get {"mfa_required": true, "mfa_token": ...}.)
    return resp.json()


@pytest.fixture
def admin_client(client):
    """A TestClient with an authenticated ADMIN session cookie set."""
    me = _login(client)
    client.headers.update({"x-organization-id": me["organization"]["id"]})
    return client


@pytest.fixture
def admin_org_id(admin_client):
    return admin_client.get("/api/v1/auth/me").json()["organization"]["id"]
