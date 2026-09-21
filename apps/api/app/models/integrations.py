"""Integration models (feature #10): outbound webhooks and external tickets.

All integrations are org-scoped and DORMANT until configured:

* ``WebhookEndpoint`` - a customer-registered HTTPS URL that receives signed
  event payloads. The signing secret is stored encrypted (never in plaintext),
  mirroring the connector-credential pattern.
* ``WebhookDelivery`` - an append-only audit log of every delivery attempt
  (status code, response snippet, attempt count). No secret material is stored.
* ``ExternalTicket`` - a local mirror linking a ComplyGraph entity (finding,
  risk, task) to an issue/incident created in Jira or ServiceNow. Only the
  external key and URL are stored; credentials live in env config, not here.

SSO (OIDC/SAML) and MFA challenge state are NOT modelled here: SSO identity
comes entirely from env-configured providers, and MFA secrets live on the
``users`` table (see the 0015 migration).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._common import TimestampMixin, uuid_pk
from app.models.types import GUID, JSONB


class WebhookEndpoint(Base, TimestampMixin):
    """A registered outbound webhook target for one organization."""

    __tablename__ = "webhook_endpoints"
    __table_args__ = (Index("ix_webhook_endpoints_org", "organization_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    # HMAC-SHA256 signing secret, Fernet-encrypted at rest. Never returned by the API.
    secret_encrypted: Mapped[str | None] = mapped_column(Text)
    # Subscribed event names (WebhookEvent values). Empty list => all events.
    events: Mapped[list] = mapped_column(JSONB, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Denormalised health for quick display; authoritative log is WebhookDelivery.
    last_status: Mapped[str | None] = mapped_column(String(20))
    last_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        back_populates="endpoint", cascade="all, delete-orphan"
    )


class WebhookDelivery(Base):
    """One delivery attempt of one event to one endpoint (append-only audit)."""

    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        Index("ix_webhook_deliveries_endpoint", "endpoint_id", "created_at"),
        Index("ix_webhook_deliveries_org", "organization_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("webhook_endpoints.id", ondelete="CASCADE"), nullable=False
    )
    event: Mapped[str] = mapped_column(String(60), nullable=False)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)  # idempotency id sent to receiver
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    response_code: Mapped[int | None] = mapped_column(Integer)
    # Truncated response body / error string for debugging (no secret material).
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    endpoint: Mapped[WebhookEndpoint] = relationship(back_populates="deliveries")


class ExternalTicket(Base, TimestampMixin):
    """Local mirror of an issue/incident created in an external tracker."""

    __tablename__ = "external_tickets"
    __table_args__ = (
        Index("ix_external_tickets_org", "organization_id"),
        Index("ix_external_tickets_entity", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # TicketProvider
    # Source entity in ComplyGraph (e.g. entity_type="finding").
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # External identifiers (e.g. Jira key "SEC-123" / ServiceNow number "INC0012345").
    external_key: Mapped[str | None] = mapped_column(String(120))
    external_id: Mapped[str | None] = mapped_column(String(120))
    external_url: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(20), default="CREATED", nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
