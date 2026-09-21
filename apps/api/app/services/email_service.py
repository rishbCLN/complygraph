"""Email delivery (feature #6) - real but dormant until SMTP is configured.

This is a genuine SMTP sender: when ``settings.email_configured`` is true (i.e.
``email_notifications_enabled`` and an ``smtp_host`` are set), it connects and
sends. When SMTP is not configured it is a no-op that returns False - the
platform runs fully on in-app notifications alone, with zero errors and nothing
sent. This mirrors the "config-driven, dormant without credentials" contract
used for the other optional integrations.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("complygraph.email")


def is_enabled() -> bool:
    return settings.email_configured


def send_email(*, to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns True if actually sent, False if dormant.

    Never raises on delivery failure - reminders must not break because email is
    misconfigured; the in-app notification is always the source of truth.
    """
    if not settings.email_configured:
        return False
    if not to:
        return False

    msg = EmailMessage()
    msg["From"] = settings.smtp_from_address
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001 - never let email break reminders
        logger.warning("Email dispatch failed (non-fatal): %s", exc)
        return False
