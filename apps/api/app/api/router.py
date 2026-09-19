"""API router aggregator.

Wires every feature router under a single APIRouter that main.py mounts at
settings.api_v1_prefix. Each router declares its own prefix (or full paths for
the flat resources like assets/connectors/search/audit-events).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routers import (
    ai,
    assets,
    audit,
    auth,
    connectors,
    controls,
    dashboard,
    data_requests,
    evidence,
    findings,
    graph,
    incidents,
    organization,
    processing_activities,
    regulations,
    reports,
    search,
    tasks,
    vendors,
)

api_router = APIRouter()

for module in (
    auth,
    organization,
    connectors,
    assets,
    vendors,
    processing_activities,
    regulations,
    controls,
    findings,
    evidence,
    tasks,
    data_requests,
    incidents,
    dashboard,
    graph,
    audit,
    reports,
    ai,
    search,
):
    api_router.include_router(module.router)
