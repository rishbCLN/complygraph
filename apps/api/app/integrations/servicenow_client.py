"""ServiceNow client: create incidents from ComplyGraph entities (feature #10).

Uses the ServiceNow Table API (``POST /api/now/table/incident``) with HTTP Basic
auth. Dormant until SERVICENOW_* settings are configured.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.integrations import IntegrationError, IntegrationNotConfigured, TicketRef


def create_incident(*, summary: str, description: str) -> TicketRef:
    if not settings.servicenow_configured:
        raise IntegrationNotConfigured("ServiceNow is not configured for this deployment.")

    base = settings.servicenow_instance_url.rstrip("/")
    url = f"{base}/api/now/table/incident"
    try:
        resp = httpx.post(
            url,
            json={"short_description": summary[:160], "description": description or ""},
            auth=(settings.servicenow_username, settings.servicenow_password),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=settings.servicenow_timeout_seconds,
        )
    except httpx.HTTPError as exc:
        raise IntegrationError(f"Could not reach ServiceNow: {exc}") from exc

    if resp.status_code not in (200, 201):
        raise IntegrationError(
            f"ServiceNow returned HTTP {resp.status_code}: {resp.text[:300]}"
        )

    result = (resp.json() or {}).get("result") or {}
    sys_id = result.get("sys_id")
    number = result.get("number")
    if not sys_id or not number:
        raise IntegrationError("ServiceNow response did not include sys_id/number.")
    return TicketRef(
        external_id=str(sys_id),
        external_key=str(number),
        url=f"{base}/nav_to.do?uri=incident.do?sys_id={sys_id}",
    )
