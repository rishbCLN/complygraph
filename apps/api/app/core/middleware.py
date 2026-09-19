"""Request logging + security-header middleware.

Logs one structured line per request (never personal data). Attaches a request
id used in error responses. Applies a baseline set of security headers.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

logger = logging.getLogger("complygraph.request")

# Secrets we must never allow into logs.
_SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "authorization", "database_url"}


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # noqa: ANN001, ANN201
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()

        response: Response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        user_id = getattr(request.state, "user_id", None)
        org_id = getattr(request.state, "organization_id", None)
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%s user=%s org=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            user_id,
            org_id,
        )
        response.headers["x-request-id"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # noqa: ANN001, ANN201
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        # CSP scoped for API responses (docs still work as they are served self-host).
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'",
        )
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
