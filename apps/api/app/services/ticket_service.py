"""External ticketing service (feature #10).

Turns a ComplyGraph entity (finding, risk, or remediation task) into a Jira
issue or ServiceNow incident, then records an ``ExternalTicket`` mirror so the
link is visible in the UI and audit trail. Ticket creation is dormant until the
target provider is configured (the client raises ``IntegrationNotConfigured``).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext
from app.core.config import settings
from app.core.enums import TicketProvider, TicketStatus
from app.core.errors import NotFoundError, ValidationError
from app.integrations import jira_client, servicenow_client
from app.models.findings import Finding, RemediationTask
from app.models.integrations import ExternalTicket
from app.models.risk import Risk

_SUPPORTED_ENTITIES = {"finding", "risk", "task"}


def _resolve_entity(db: Session, org_id: uuid.UUID, entity_type: str, entity_id: str):
    try:
        eid = uuid.UUID(entity_id)
    except ValueError:
        raise ValidationError("entity_id must be a UUID.") from None

    model = {"finding": Finding, "risk": Risk, "task": RemediationTask}[entity_type]
    obj = db.get(model, eid)
    if obj is None or obj.organization_id != org_id:
        raise NotFoundError(f"{entity_type} not found.")
    return obj


def _describe(entity_type: str, obj) -> tuple[str, str]:
    """Build a (summary, description) pair for the external tracker."""
    title = getattr(obj, "title", None) or f"{entity_type} {obj.id}"
    parts = [f"ComplyGraph {entity_type}: {title}", ""]
    if getattr(obj, "severity", None):
        parts.append(f"Severity: {obj.severity}")
    if getattr(obj, "category", None):
        parts.append(f"Category: {obj.category}")
    if getattr(obj, "status", None):
        parts.append(f"Status: {obj.status}")
    if getattr(obj, "description", None):
        parts.extend(["", obj.description])
    parts.extend(["", f"Source: ComplyGraph {entity_type} {obj.id}"])
    summary = f"[ComplyGraph] {title}"
    return summary, "\n".join(parts)


def list_tickets(
    db: Session,
    org_id: uuid.UUID,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> list[ExternalTicket]:
    stmt = select(ExternalTicket).where(ExternalTicket.organization_id == org_id)
    if entity_type:
        stmt = stmt.where(ExternalTicket.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(ExternalTicket.entity_id == entity_id)
    stmt = stmt.order_by(ExternalTicket.created_at.desc())
    return list(db.scalars(stmt))


def create_ticket(
    db: Session,
    ctx: AuthContext,
    *,
    provider: TicketProvider,
    entity_type: str,
    entity_id: str,
    summary: str | None = None,
    description: str | None = None,
) -> ExternalTicket:
    entity_type = (entity_type or "").strip().lower()
    if entity_type not in _SUPPORTED_ENTITIES:
        raise ValidationError(
            f"entity_type must be one of: {', '.join(sorted(_SUPPORTED_ENTITIES))}."
        )
    obj = _resolve_entity(db, ctx.organization_id, entity_type, entity_id)

    auto_summary, auto_description = _describe(entity_type, obj)
    final_summary = (summary or auto_summary).strip()
    final_description = (description or auto_description).strip()

    if provider == TicketProvider.JIRA:
        ref = jira_client.create_issue(
            summary=final_summary,
            description=final_description,
            labels=["complygraph", entity_type],
        )
    elif provider == TicketProvider.SERVICENOW:
        ref = servicenow_client.create_incident(
            summary=final_summary, description=final_description
        )
    else:  # pragma: no cover - guarded by enum
        raise ValidationError("Unsupported ticket provider.")

    ticket = ExternalTicket(
        organization_id=ctx.organization_id,
        provider=provider.value,
        entity_type=entity_type,
        entity_id=str(obj.id),
        external_id=ref.external_id,
        external_key=ref.external_key,
        external_url=ref.url,
        status=TicketStatus.CREATED.value,
        summary=final_summary,
        created_by=ctx.user.id,
    )
    db.add(ticket)
    db.flush()
    return ticket


def provider_available(provider: TicketProvider) -> bool:
    if provider == TicketProvider.JIRA:
        return settings.jira_configured
    if provider == TicketProvider.SERVICENOW:
        return settings.servicenow_configured
    return False
