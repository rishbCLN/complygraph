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
