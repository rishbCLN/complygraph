"""API router aggregator.

Wires every feature router under a single APIRouter that main.py mounts at
settings.api_v1_prefix. Each router declares its own prefix (or full paths for
the flat resources like assets/connectors/search/audit-events).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routers import (
    ai,
    ai_systems,
    approvals,
    assets,
    audit,
    auth,
    campaigns,
    connectors,
    consent,
    control_mappings,
    controls,
    dashboard,
    data_requests,
    documents,
    privacy_center,
    evidence,
    findings,
    graph,
    incidents,
    integrations,
    notifications,
    organization,
    overrides,
    processing_activities,
    reassessment,
    regulations,
    reports,
    risks,
    search,
    self_audit,
    sso,
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
    ai_systems,
    processing_activities,
    regulations,
    controls,
    control_mappings,
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
    overrides,
    documents,
    self_audit,
    risks,
    approvals,
    campaigns,
    consent,
    privacy_center,
    notifications,
    reassessment,
    integrations,
    sso,
):
    api_router.include_router(module.router)
