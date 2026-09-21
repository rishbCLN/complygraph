"""End-to-end tests for scheduled re-assessment + reminders/notifications (feature #6)."""

from __future__ import annotations

PREFIX = "/api/v1"


# --------------------------------------------------------------------------- #
# Reminders / notifications
# --------------------------------------------------------------------------- #
def test_seed_generates_notifications(admin_client):
    notifs = admin_client.get(f"{PREFIX}/notifications").json()
    # Seed runs the reminder engine, so there should be at least the expired-evidence one.
    assert isinstance(notifs, list)
    kinds = {n["kind"] for n in notifs}
    assert "EVIDENCE_EXPIRED" in kinds or "EVIDENCE_EXPIRING" in kinds


def test_generate_is_idempotent(admin_client):
    first = admin_client.post(f"{PREFIX}/notifications/generate").json()
    before = len(admin_client.get(f"{PREFIX}/notifications").json())
    second = admin_client.post(f"{PREFIX}/notifications/generate").json()
    after = len(admin_client.get(f"{PREFIX}/notifications").json())
    # Same underlying state -> dedupe means no growth in active notifications.
    assert after == before
    assert first["total"] == second["total"]


def test_generate_reports_by_kind(admin_client):
    result = admin_client.post(f"{PREFIX}/notifications/generate").json()
    assert "total" in result
    assert "by_kind" in result
    assert isinstance(result["by_kind"], dict)


def test_unread_count_and_mark_read(admin_client):
    admin_client.post(f"{PREFIX}/notifications/generate")
    notifs = admin_client.get(f"{PREFIX}/notifications").json()
    assert notifs, "expected at least one notification"
    count_before = admin_client.get(f"{PREFIX}/notifications/unread-count").json()["unread"]
    assert count_before >= 1

    target = next((n for n in notifs if n["state"] == "UNREAD"), None)
    assert target is not None
    read = admin_client.post(f"{PREFIX}/notifications/{target['id']}/read").json()
    assert read["state"] == "READ"
    assert read["read_at"] is not None

    count_after = admin_client.get(f"{PREFIX}/notifications/unread-count").json()["unread"]
    assert count_after == count_before - 1


def test_dismiss_hides_from_default_list(admin_client):
    admin_client.post(f"{PREFIX}/notifications/generate")
    notifs = admin_client.get(f"{PREFIX}/notifications").json()
    target = notifs[0]
    admin_client.post(f"{PREFIX}/notifications/{target['id']}/dismiss")
    after = admin_client.get(f"{PREFIX}/notifications").json()
    assert target["id"] not in {n["id"] for n in after}
    # But visible when explicitly filtering by DISMISSED.
    dismissed = admin_client.get(f"{PREFIX}/notifications", params={"state": "DISMISSED"}).json()
    assert target["id"] in {n["id"] for n in dismissed}


def test_read_all(admin_client):
    admin_client.post(f"{PREFIX}/notifications/generate")
    admin_client.post(f"{PREFIX}/notifications/read-all")
    assert admin_client.get(f"{PREFIX}/notifications/unread-count").json()["unread"] == 0


def test_notification_deep_link_fields(admin_client):
    admin_client.post(f"{PREFIX}/notifications/generate")
    notifs = admin_client.get(f"{PREFIX}/notifications").json()
    ev = next((n for n in notifs if n["kind"] in ("EVIDENCE_EXPIRED", "EVIDENCE_EXPIRING")), None)
    assert ev is not None
    assert ev["entity_type"] == "evidence"
    assert ev["entity_id"]


def test_generate_requires_capability(client):
    resp = client.post(
        f"{PREFIX}/auth/login",
        json={"email": "viewer@asterlane.demo", "password": "DemoPass123!"},
    )
    me = resp.json()
    client.headers.update({"x-organization-id": me["organization"]["id"]})
    # Viewer can list but not generate.
    assert client.get(f"{PREFIX}/notifications").status_code == 200
    assert client.post(f"{PREFIX}/notifications/generate").status_code == 403


def test_notifications_require_auth(client):
    assert client.get(f"{PREFIX}/notifications").status_code in (401, 403)


# --------------------------------------------------------------------------- #
# Scheduled re-assessment
# --------------------------------------------------------------------------- #
def test_reassessment_run(admin_client):
    result = admin_client.post(f"{PREFIX}/reassessment/run").json()
    assert result["controls_assessed"] >= 1
    assert "status_counts" in result
    assert "regressions" in result
    assert isinstance(result["regressed_controls"], list)


def test_reassessment_records_history(admin_client):
    # Two runs should both succeed and each append history (assessment stays stable).
    first = admin_client.post(f"{PREFIX}/reassessment/run").json()
    second = admin_client.post(f"{PREFIX}/reassessment/run").json()
    assert first["controls_assessed"] == second["controls_assessed"]
    # Deterministic: no regressions between two identical-state runs.
    assert second["regressions"] == 0


def test_reassessment_requires_capability(client):
    resp = client.post(
        f"{PREFIX}/auth/login",
        json={"email": "viewer@asterlane.demo", "password": "DemoPass123!"},
    )
    me = resp.json()
    client.headers.update({"x-organization-id": me["organization"]["id"]})
    assert client.post(f"{PREFIX}/reassessment/run").status_code == 403


def test_reassessment_completion_notification(admin_client):
    admin_client.post(f"{PREFIX}/reassessment/run")
    notifs = admin_client.get(f"{PREFIX}/notifications", params={"state": "UNREAD"}).json()
    # A completion notification should exist (INFO or WARNING).
    completions = [n for n in notifs if n["kind"] == "REASSESSMENT_COMPLETE"]
    assert completions, "expected a re-assessment completion notification"


# --------------------------------------------------------------------------- #
# Worker tasks (eager, in-process)
# --------------------------------------------------------------------------- #
def test_reminder_task_runs_eager():
    from app.workers.tasks import generate_reminders_task

    result = generate_reminders_task()
    assert result["orgs"] >= 1
    assert "reminders" in result


def test_reassessment_task_runs_eager():
    from app.workers.tasks import scheduled_reassessment_task

    result = scheduled_reassessment_task()
    assert result["orgs"] >= 1


def test_email_dormant_by_default():
    from app.services import email_service

    # No SMTP configured in tests -> dormant, returns False, never raises.
    assert email_service.is_enabled() is False
    assert email_service.send_email(to="[email protected]", subject="x", body="y") is False
