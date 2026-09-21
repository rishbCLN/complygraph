"""External integration clients (feature #10).

Each client is a thin, real REST wrapper around a third-party API. They are
DORMANT until the corresponding environment configuration is present: calling a
client while unconfigured raises ``IntegrationNotConfigured`` (surfaced as a 400
by the API layer) rather than attempting a call with empty credentials.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import AppError


class IntegrationNotConfigured(AppError):
    """Raised when an integration is used before its credentials are configured."""

    status_code = 400


class IntegrationError(AppError):
    """Raised when a configured integration call fails (network / API error)."""

    status_code = 502


@dataclass
class TicketRef:
    """Normalised reference to a created external issue/incident."""

    external_id: str
    external_key: str
    url: str
