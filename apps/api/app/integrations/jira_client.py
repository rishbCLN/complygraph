"""Jira Cloud client: create issues from ComplyGraph entities (feature #10).

Uses the Jira Cloud REST API v3 (``POST /rest/api/3/issue``) with HTTP Basic
auth (account email + API token). Dormant until JIRA_* settings are configured.
The description is sent in Atlassian Document Format (ADF), which the v3 API
requires.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.integrations import IntegrationError, IntegrationNotConfigured, TicketRef


def _adf(text: str) -> dict:
    """Wrap plain text in a minimal Atlassian Document Format document."""
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": text or ""}]}
        ],
    }


def create_issue(
    *,
    summary: str,
    description: str,
    issue_type: str | None = None,
    labels: list[str] | None = None,
) -> TicketRef:
    if not settings.jira_configured:
        raise IntegrationNotConfigured("Jira is not configured for this deployment.")

    base = settings.jira_base_url.rstrip("/")
    url = f"{base}/rest/api/3/issue"
    fields = {
        "project": {"key": settings.jira_project_key},
        "summary": summary[:250],
        "description": _adf(description),
        "issuetype": {"name": issue_type or settings.jira_default_issue_type},
    }
    if labels:
        fields["labels"] = labels
    try:
        resp = httpx.post(
            url,
            json={"fields": fields},
            auth=(settings.jira_email, settings.jira_api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=settings.jira_timeout_seconds,
        )
    except httpx.HTTPError as exc:
        raise IntegrationError(f"Could not reach Jira: {exc}") from exc

    if resp.status_code not in (200, 201):
        raise IntegrationError(f"Jira returned HTTP {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    key = data.get("key")
    if not key:
        raise IntegrationError("Jira response did not include an issue key.")
    return TicketRef(
        external_id=str(data.get("id") or key),
        external_key=key,
        url=f"{base}/browse/{key}",
    )
