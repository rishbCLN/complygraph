"""Outbound webhook delivery (feature #10).

Customers register HTTPS endpoints (org-scoped) that receive signed JSON event
payloads when domain events occur (finding created, risk status changed, DSR
fulfilled, assessment regressed, ...). Delivery is:

* **Signed** - every request carries an ``X-ComplyGraph-Signature`` header
  (``sha256=<hmac hex>``) computed over the exact request body using the
  endpoint's secret, so receivers can verify authenticity.
* **Retried** - transient failures (network / 5xx / 429) are retried with a
  short backoff up to ``webhook_max_attempts``.
* **Logged** - each attempt is recorded in ``webhook_deliveries`` with the
  final status code and a truncated detail string (never any secret material).
* **Best-effort** - ``dispatch_event`` never raises into the caller; a broken
  webhook must not fail the business operation that triggered it.

SSRF protection reuses ``scanners.net_safety.assert_safe_host`` so a tenant
cannot point a webhook at internal infrastructure when private targets are
disallowed.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from typing import Any
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import utcnow
from app.core.enums import WebhookDeliveryStatus
from app.core.errors import ValidationError
from app.models.integrations import WebhookDelivery, WebhookEndpoint
from app.scanners.net_safety import assert_safe_host
from app.security.encryption import decrypt_json, encrypt_json

_SIGNATURE_HEADER = "X-ComplyGraph-Signature"
_EVENT_HEADER = "X-ComplyGraph-Event"
_DELIVERY_HEADER = "X-ComplyGraph-Delivery"
_TIMESTAMP_HEADER = "X-ComplyGraph-Timestamp"
_DETAIL_MAX = 500


# --------------------------------------------------------------------------- #
# Secret handling
# --------------------------------------------------------------------------- #
def generate_secret() -> str:
    return "whsec_" + uuid.uuid4().hex + uuid.uuid4().hex


def _store_secret(endpoint: WebhookEndpoint, secret: str) -> None:
    endpoint.secret_encrypted = encrypt_json({"secret": secret})


def _load_secret(endpoint: WebhookEndpoint) -> str | None:
    if not endpoint.secret_encrypted:
        return None
    try:
        return decrypt_json(endpoint.secret_encrypted).get("secret")
    except ValueError:
        return None


def sign_payload(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _validate_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValidationError("Webhook URL must be an http(s) URL.")
    if not parts.hostname:
        raise ValidationError("Webhook URL is missing a host.")
    # In production (private targets disallowed) this blocks SSRF to internal hosts.
    assert_safe_host(parts.hostname)


# --------------------------------------------------------------------------- #
# Endpoint CRUD
# --------------------------------------------------------------------------- #
def list_endpoints(db: Session, org_id: uuid.UUID) -> list[WebhookEndpoint]:
    return list(
        db.scalars(
            select(WebhookEndpoint)
            .where(WebhookEndpoint.organization_id == org_id)
            .order_by(WebhookEndpoint.created_at.desc())
        )
    )


def get_endpoint(db: Session, org_id: uuid.UUID, endpoint_id: uuid.UUID) -> WebhookEndpoint | None:
    ep = db.get(WebhookEndpoint, endpoint_id)
    if ep is None or ep.organization_id != org_id:
        return None
    return ep


def create_endpoint(
    db: Session,
    org_id: uuid.UUID,
    *,
    name: str,
    url: str,
    events: list[str] | None = None,
) -> tuple[WebhookEndpoint, str]:
    """Create an endpoint and return it plus the plaintext secret (shown once)."""
    name = (name or "").strip()
    if not name:
        raise ValidationError("Webhook name is required.")
    _validate_url(url)
    _validate_events(events)
    secret = generate_secret()
    endpoint = WebhookEndpoint(
        organization_id=org_id,
        name=name,
        url=url.strip(),
        events=events or [],
        enabled=True,
    )
    _store_secret(endpoint, secret)
    db.add(endpoint)
    db.flush()
    return endpoint, secret


def update_endpoint(
    db: Session,
    endpoint: WebhookEndpoint,
    *,
    name: str | None = None,
    url: str | None = None,
    events: list[str] | None = None,
    enabled: bool | None = None,
) -> WebhookEndpoint:
    if name is not None:
        name = name.strip()
        if not name:
            raise ValidationError("Webhook name cannot be empty.")
        endpoint.name = name
    if url is not None:
        _validate_url(url)
        endpoint.url = url.strip()
    if events is not None:
        _validate_events(events)
        endpoint.events = events
    if enabled is not None:
        endpoint.enabled = enabled
    db.flush()
    return endpoint


def rotate_secret(db: Session, endpoint: WebhookEndpoint) -> str:
    secret = generate_secret()
    _store_secret(endpoint, secret)
    db.flush()
    return secret


def delete_endpoint(db: Session, endpoint: WebhookEndpoint) -> None:
    db.delete(endpoint)
    db.flush()


def _validate_events(events: list[str] | None) -> None:
    if not events:
        return
    from app.core.enums import WebhookEvent

    valid = {e.value for e in WebhookEvent}
    for ev in events:
        if ev not in valid:
            raise ValidationError(f"Unknown webhook event: {ev}")


# --------------------------------------------------------------------------- #
# Delivery
# --------------------------------------------------------------------------- #
def _subscribed(endpoint: WebhookEndpoint, event: str) -> bool:
    # Empty subscription list => receive all events.
    return not endpoint.events or event in endpoint.events


def _deliver_once(url: str, body: bytes, headers: dict[str, str]) -> httpx.Response:
    return httpx.post(
        url,
        content=body,
        headers=headers,
        timeout=settings.webhook_timeout_seconds,
    )


def deliver_to_endpoint(
    db: Session,
    endpoint: WebhookEndpoint,
    event: str,
    payload: dict[str, Any],
    *,
    _sleep=time.sleep,
) -> WebhookDelivery:
    """Attempt delivery (with retries) and record the result. Never raises."""
    event_id = uuid.uuid4().hex
    body = json.dumps(
        {"id": event_id, "event": event, "created_at": utcnow().isoformat(), "data": payload},
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    secret = _load_secret(endpoint)
    headers = {
        "Content-Type": "application/json",
        _EVENT_HEADER: event,
        _DELIVERY_HEADER: event_id,
        _TIMESTAMP_HEADER: str(int(time.time())),
        "User-Agent": "ComplyGraph-Webhook/1.0",
    }
    if secret:
        headers[_SIGNATURE_HEADER] = sign_payload(secret, body)

    delivery = WebhookDelivery(
        organization_id=endpoint.organization_id,
        endpoint_id=endpoint.id,
        event=event,
        event_id=event_id,
        status=WebhookDeliveryStatus.PENDING.value,
        attempts=0,
        created_at=utcnow(),
    )
    db.add(delivery)

    max_attempts = max(1, settings.webhook_max_attempts)
    last_detail = ""
    last_code: int | None = None
    for attempt in range(1, max_attempts + 1):
        delivery.attempts = attempt
        try:
            resp = _deliver_once(endpoint.url, body, headers)
            last_code = resp.status_code
            if 200 <= resp.status_code < 300:
                delivery.status = WebhookDeliveryStatus.SUCCEEDED.value
                delivery.response_code = resp.status_code
                delivery.detail = f"HTTP {resp.status_code}"
                delivery.completed_at = utcnow()
                _mark_endpoint(endpoint, ok=True, code=resp.status_code)
                db.flush()
                return delivery
            last_detail = f"HTTP {resp.status_code}: {resp.text[:_DETAIL_MAX]}"
            # 4xx (other than 429) are permanent - do not retry.
            if resp.status_code < 500 and resp.status_code != 429:
                break
        except httpx.HTTPError as exc:
            last_detail = f"{type(exc).__name__}: {str(exc)[:_DETAIL_MAX]}"

        if attempt < max_attempts:
            _sleep(settings.webhook_retry_backoff_seconds * attempt)

    delivery.status = WebhookDeliveryStatus.FAILED.value
    delivery.response_code = last_code
    delivery.detail = last_detail[:_DETAIL_MAX] or "delivery failed"
    delivery.completed_at = utcnow()
    _mark_endpoint(endpoint, ok=False, code=last_code)
    db.flush()
    return delivery


def _mark_endpoint(endpoint: WebhookEndpoint, *, ok: bool, code: int | None) -> None:
    endpoint.last_delivery_at = utcnow()
    endpoint.last_status = (
        WebhookDeliveryStatus.SUCCEEDED.value if ok else WebhookDeliveryStatus.FAILED.value
    )
    if ok:
        endpoint.failure_count = 0
    else:
        endpoint.failure_count = (endpoint.failure_count or 0) + 1


def dispatch_event(
    db: Session, org_id: uuid.UUID, event: str, payload: dict[str, Any]
) -> list[WebhookDelivery]:
    """Fan an event out to every enabled, subscribed endpoint. Best-effort.

    Safe to call from within a business transaction: it flushes delivery rows
    but does not commit, and swallows all delivery errors.
    """
    if not settings.webhooks_enabled:
        return []
    deliveries: list[WebhookDelivery] = []
    try:
        endpoints = [
            ep
            for ep in list_endpoints(db, org_id)
            if ep.enabled and _subscribed(ep, event)
        ]
    except Exception:  # noqa: BLE001 - never break the caller
        return []
    for ep in endpoints:
        try:
            deliveries.append(deliver_to_endpoint(db, ep, event, payload))
        except Exception:  # noqa: BLE001 - one bad endpoint must not stop others
            continue
    return deliveries


def list_deliveries(
    db: Session, org_id: uuid.UUID, endpoint_id: uuid.UUID, limit: int = 50
) -> list[WebhookDelivery]:
    return list(
        db.scalars(
            select(WebhookDelivery)
            .where(
                WebhookDelivery.organization_id == org_id,
                WebhookDelivery.endpoint_id == endpoint_id,
            )
            .order_by(WebhookDelivery.created_at.desc())
            .limit(limit)
        )
    )
