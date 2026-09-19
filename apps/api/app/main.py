"""ComplyGraph FastAPI application entrypoint."""

from __future__ import annotations

import logging

import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.errors import register_error_handlers
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="ComplyGraph API",
    version="1.0.0",
    description=(
        "Continuous Data Governance & Compliance Infrastructure. "
        "ComplyGraph is software for governance, evidence collection and internal "
        "control assessment. It is not a law firm and does not provide legal "
        "certification of compliance."
    ),
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["system"])
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
def ready() -> dict:
    """Readiness probe: verifies PostgreSQL and Redis are reachable."""
    checks = {"postgres": False, "redis": False}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = True
    except Exception:  # noqa: BLE001
        pass
    try:
        redis.Redis.from_url(settings.redis_url).ping()
        checks["redis"] = True
    except Exception:  # noqa: BLE001
        pass
    status = "ok" if all(checks.values()) else "degraded"
    return {"status": status, "checks": checks, "ai_mode": settings.effective_ai_mode}
