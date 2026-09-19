"""Unit tests for AI-input sanitization.

Raw personal data and secrets must never be sent to the model. ``sanitize_text``
redacts emails, phone numbers, long tokens, and secret key/value pairs from any
free text before it enters an investigation payload.
"""

from __future__ import annotations

from app.services.ai_service import sanitize_text


def test_email_is_redacted():
    out = sanitize_text("Contact aarav@example.com for details")
    assert "aarav@example.com" not in out
    assert "[REDACTED_EMAIL]" in out


def test_phone_number_is_redacted():
    out = sanitize_text("Call +91 9876543210 now")
    assert "9876543210" not in out
    assert "[REDACTED_NUMBER]" in out


def test_secret_key_value_is_redacted():
    out = sanitize_text("api_key=sk_live_abcdef123456 should not leak")
    assert "sk_live_abcdef123456" not in out
    assert "[REDACTED]" in out


def test_long_token_is_redacted():
    token = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4"  # 28 chars
    out = sanitize_text(f"bearer {token}")
    assert token not in out
    assert "[REDACTED_TOKEN]" in out


def test_password_assignment_is_redacted():
    out = sanitize_text("password: hunter2secretvalue")
    assert "hunter2secretvalue" not in out
    assert "[REDACTED]" in out


def test_none_and_empty_pass_through():
    assert sanitize_text(None) is None
    assert sanitize_text("") == ""


def test_plain_text_without_pii_is_unchanged():
    text = "The control assessment reported a missing retention policy."
    assert sanitize_text(text) == text


def test_investigation_input_never_leaks_raw_pii():
    """End-to-end trust-boundary test: the assembled AI payload must contain no
    raw PII even when the finding text and field data carry it."""
    import json
    import uuid as _uuid

    from app.controls.risk import RiskInputs
    from app.core.database import SessionLocal
    from app.models.identity import Organization
    from app.models.inventory import AssetField, DataAsset
    from app.services.ai_service import build_investigation_input
    from app.services.findings_service import upsert_finding

    raw_email = "aarav.sharma@example.com"
    raw_phone = "+919876543210"

    db = SessionLocal()
    try:
        org = Organization(name="LeakTest", slug=f"leak-{_uuid.uuid4().hex[:8]}")
        db.add(org)
        db.flush()

        asset = DataAsset(
            organization_id=org.id,
            name="public.customers",
            display_name="customers",
            asset_type="TABLE",
            classification="PERSONAL_DATA",
            sensitivity_level=4,
        )
        db.add(asset)
        db.flush()
        # Even if masked_examples accidentally still carries a raw value, the
        # sanitizer must scrub it before it reaches the model.
        db.add(
            AssetField(
                asset_id=asset.id,
                name="email",
                classification="PERSONAL_DATA",
                category="CONTACT",
                confidence_band="HIGH",
                masked_examples=raw_email,
            )
        )
        db.flush()

        finding = upsert_finding(
            db,
            organization_id=org.id,
            finding_type="test:leak",
            title=f"Customer {raw_email} flagged",
            description=f"Contact at {raw_phone} regarding data.",
            risk_inputs=RiskInputs(4, 3, 5, 2),
            asset_id=asset.id,
            source="test",
        )
        db.flush()

        payload = build_investigation_input(db, org, finding)
        blob = json.dumps(payload, default=str)

        assert raw_email not in blob
        assert raw_phone not in blob
        assert "REDACTED" in blob
    finally:
        db.rollback()
        db.close()
