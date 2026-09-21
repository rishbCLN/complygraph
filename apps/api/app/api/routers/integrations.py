"""Integration management endpoints (feature #10).

Covers:
* ``GET  /integrations/status`` - which integrations are configured/dormant.
* Outbound webhook CRUD, secret rotation, test-ping, and delivery history.
* External ticketing (Jira / ServiceNow) create + list (see ticket_service).

All webhook/ticket routes require the ``manage_integrations`` capability except
ticket creation, which uses the broader ``create_ticket`` capability so analysts
can push a finding without holding full integration-admin rights.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.core.audit import record_audit
from app.core.config import settings
from app.core.database import get_db
from app.core.enums import TicketProvider, WebhookEvent
from app.core.errors import NotFoundError, ValidationError
from app.core.rbac import CREATE_TICKET, MANAGE_INTEGRATIONS
from app.models.integrations import ExternalTicket, WebhookDelivery, WebhookEndpoint
from app.services import ticket_service, webhook_service

router = APIRouter(prefix="/integrations", tags=["integrations"])


# --------------------------------------------------------------------------- #
# Status
# --------------------------------------------------------------------------- #
class IntegrationState(BaseModel):
    name: str
    configured: bool
    detail: str


class StatusResponse(BaseModel):
    integrations: list[IntegrationState]
    webhook_events: list[str]


@router.get("/status", response_model=StatusResponse)
def integration_status(
    ctx: AuthContext = Depends(get_current_context),
) -> StatusResponse:
    """Report which integrations are live vs dormant (no secrets are returned)."""
    states = [
        IntegrationState(
            name="jira",
            configured=settings.jira_configured,
            detail=(
                f"Project {settings.jira_project_key} on {settings.jira_base_url}"
                if settings.jira_configured
                else "Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY to enable."
            ),
        ),
        IntegrationState(
            name="servicenow",
            configured=settings.servicenow_configured,
            detail=(
                f"Instance {settings.servicenow_instance_url}"
                if settings.servicenow_configured
                else "Set SERVICENOW_INSTANCE_URL, SERVICENOW_USERNAME, SERVICENOW_PASSWORD to enable."
            ),
        ),
        IntegrationState(
            name="oidc",
            configured=settings.oidc_configured,
            detail=(
                f"{settings.oidc_provider_name} ({settings.oidc_issuer})"
                if settings.oidc_configured
                else "Set OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_REDIRECT_URL to enable."
            ),
        ),
        IntegrationState(
            name="saml",
            configured=settings.saml_configured,
            detail=(
                f"{settings.saml_provider_name} (IdP {settings.saml_idp_entity_id or 'configured'})"
                if settings.saml_configured
                else "Set SAML_SP_ENTITY_ID, SAML_SP_ACS_URL, SAML_IDP_SSO_URL, SAML_IDP_X509_CERT to enable."
            ),
        ),
        IntegrationState(
            name="email",
            configured=settings.email_configured,
            detail=(
                f"SMTP {settings.smtp_host}"
                if settings.email_configured
                else "Set SMTP_HOST and EMAIL_NOTIFICATIONS_ENABLED to enable."
            ),
        ),
    ]
    return StatusResponse(
        integrations=states,
        webhook_events=[e.value for e in WebhookEvent],
    )


# --------------------------------------------------------------------------- #
# Webhooks
# --------------------------------------------------------------------------- #
class WebhookOut(BaseModel):
    id: str
    name: str
    url: str
    events: list[str]
    enabled: bool
    last_status: str | None
    last_delivery_at: datetime | None
    failure_count: int
    created_at: datetime | None


class WebhookCreateResponse(WebhookOut):
    # The signing secret is returned exactly once, at creation / rotation.
    secret: str


class WebhookCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    url: str = Field(min_length=1, max_length=1024)
    events: list[str] = Field(default_factory=list)


class WebhookUpdateRequest(BaseModel):
    name: str | None = None
    url: str | None = None
    events: list[str] | None = None
    enabled: bool | None = None


class DeliveryOut(BaseModel):
    id: str
    event: str
    event_id: str
    status: str
    attempts: int
    response_code: int | None
    detail: str | None
    created_at: datetime | None
    completed_at: datetime | None


def _webhook_out(ep: WebhookEndpoint) -> WebhookOut:
    return WebhookOut(
        id=str(ep.id),
        name=ep.name,
        url=ep.url,
        events=list(ep.events or []),
        enabled=ep.enabled,
        last_status=ep.last_status,
        last_delivery_at=ep.last_delivery_at,
        failure_count=ep.failure_count or 0,
        created_at=ep.created_at,
    )


def _delivery_out(d: WebhookDelivery) -> DeliveryOut:
    return DeliveryOut(
        id=str(d.id),
        event=d.event,
        event_id=d.event_id,
        status=d.status,
        attempts=d.attempts,
        response_code=d.response_code,
        detail=d.detail,
        created_at=d.created_at,
        completed_at=d.completed_at,
    )


def _require_endpoint(db: Session, ctx: AuthContext, endpoint_id: uuid.UUID) -> WebhookEndpoint:
    ep = webhook_service.get_endpoint(db, ctx.organization_id, endpoint_id)
    if ep is None:
        raise NotFoundError("Webhook endpoint not found.")
    return ep


@router.get("/webhooks", response_model=list[WebhookOut])
def list_webhooks(
    ctx: AuthContext = Depends(require_capability(MANAGE_INTEGRATIONS)),
    db: Session = Depends(get_db),
) -> list[WebhookOut]:
    return [_webhook_out(ep) for ep in webhook_service.list_endpoints(db, ctx.organization_id)]


@router.post("/webhooks", response_model=WebhookCreateResponse, status_code=201)
def create_webhook(
    payload: WebhookCreateRequest,
    ctx: AuthContext = Depends(require_capability(MANAGE_INTEGRATIONS)),
    db: Session = Depends(get_db),
) -> WebhookCreateResponse:
    ep, secret = webhook_service.create_endpoint(
        db, ctx.organization_id, name=payload.name, url=payload.url, events=payload.events
    )
    record_audit(
        db,
        action="integrations.webhook_created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="webhook_endpoint",
        entity_id=ep.id,
        metadata={"url": ep.url, "events": ep.events},
    )
    db.commit()
    db.refresh(ep)
    out = _webhook_out(ep)
    return WebhookCreateResponse(**out.model_dump(), secret=secret)


@router.patch("/webhooks/{endpoint_id}", response_model=WebhookOut)
def update_webhook(
    endpoint_id: uuid.UUID,
    payload: WebhookUpdateRequest,
    ctx: AuthContext = Depends(require_capability(MANAGE_INTEGRATIONS)),
    db: Session = Depends(get_db),
) -> WebhookOut:
    ep = _require_endpoint(db, ctx, endpoint_id)
    webhook_service.update_endpoint(
        db,
        ep,
        name=payload.name,
        url=payload.url,
        events=payload.events,
        enabled=payload.enabled,
    )
    db.commit()
    db.refresh(ep)
    return _webhook_out(ep)


@router.delete("/webhooks/{endpoint_id}", status_code=204)
def delete_webhook(
    endpoint_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_INTEGRATIONS)),
    db: Session = Depends(get_db),
) -> None:
    ep = _require_endpoint(db, ctx, endpoint_id)
    webhook_service.delete_endpoint(db, ep)
    record_audit(
        db,
        action="integrations.webhook_deleted",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="webhook_endpoint",
        entity_id=endpoint_id,
    )
    db.commit()


@router.post("/webhooks/{endpoint_id}/rotate-secret", response_model=WebhookCreateResponse)
def rotate_webhook_secret(
    endpoint_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_INTEGRATIONS)),
    db: Session = Depends(get_db),
) -> WebhookCreateResponse:
    ep = _require_endpoint(db, ctx, endpoint_id)
    secret = webhook_service.rotate_secret(db, ep)
    db.commit()
    db.refresh(ep)
    out = _webhook_out(ep)
    return WebhookCreateResponse(**out.model_dump(), secret=secret)


@router.post("/webhooks/{endpoint_id}/test", response_model=DeliveryOut)
def test_webhook(
    endpoint_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_INTEGRATIONS)),
    db: Session = Depends(get_db),
) -> DeliveryOut:
    """Send a signed ``ping`` event to the endpoint and record the attempt."""
    ep = _require_endpoint(db, ctx, endpoint_id)
    delivery = webhook_service.deliver_to_endpoint(
        db, ep, "ping", {"message": "ComplyGraph test event", "endpoint_id": str(ep.id)}
    )
    db.commit()
    db.refresh(delivery)
    return _delivery_out(delivery)


@router.get("/webhooks/{endpoint_id}/deliveries", response_model=list[DeliveryOut])
def list_webhook_deliveries(
    endpoint_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_INTEGRATIONS)),
    db: Session = Depends(get_db),
) -> list[DeliveryOut]:
    _require_endpoint(db, ctx, endpoint_id)
    return [
        _delivery_out(d)
        for d in webhook_service.list_deliveries(db, ctx.organization_id, endpoint_id)
    ]


# --------------------------------------------------------------------------- #
# External tickets (Jira / ServiceNow)
# --------------------------------------------------------------------------- #
class TicketOut(BaseModel):
    id: str
    provider: str
    entity_type: str
    entity_id: str
    external_key: str | None
    external_url: str | None
    status: str
    summary: str | None
    created_at: datetime | None


class TicketCreateRequest(BaseModel):
    provider: str = Field(description="JIRA or SERVICENOW")
    entity_type: str = Field(description="finding | risk | task")
    entity_id: str
    summary: str | None = None
    description: str | None = None


def _ticket_out(t: ExternalTicket) -> TicketOut:
    return TicketOut(
        id=str(t.id),
        provider=t.provider,
        entity_type=t.entity_type,
        entity_id=t.entity_id,
        external_key=t.external_key,
        external_url=t.external_url,
        status=t.status,
        summary=t.summary,
        created_at=t.created_at,
    )


@router.get("/tickets", response_model=list[TicketOut])
def list_tickets(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
) -> list[TicketOut]:
    return [
        _ticket_out(t)
        for t in ticket_service.list_tickets(
            db, ctx.organization_id, entity_type=entity_type, entity_id=entity_id
        )
    ]


@router.post("/tickets", response_model=TicketOut, status_code=201)
def create_ticket(
    payload: TicketCreateRequest,
    ctx: AuthContext = Depends(require_capability(CREATE_TICKET)),
    db: Session = Depends(get_db),
) -> TicketOut:
    try:
        provider = TicketProvider(payload.provider.upper())
    except ValueError:
        raise ValidationError("provider must be JIRA or SERVICENOW.") from None
    ticket = ticket_service.create_ticket(
        db,
        ctx,
        provider=provider,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        summary=payload.summary,
        description=payload.description,
    )
    record_audit(
        db,
        action="integrations.ticket_created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        metadata={"provider": provider.value, "external_key": ticket.external_key},
    )
    db.commit()
    db.refresh(ticket)
    return _ticket_out(ticket)
