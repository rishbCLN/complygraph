"""AI system inventory endpoints.

Exposes the AI-system-centric inventory: systems, their architecture components
and flows, structured architecture import, the per-system architecture graph, and
the derived applicability facts the analysis engine consumes.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.rbac import ASSESS_CONTROLS, MANAGE_INVENTORY
from app.services import ai_system_service, assessment_service, graph_service

router = APIRouter(prefix="/systems", tags=["ai-systems"])


# --- Schemas --------------------------------------------------------------------


class AISystemIn(BaseModel):
    name: str
    description: str | None = None
    business_purpose: str | None = None
    owner: str | None = None
    system_type: str | None = None
    risk_domain: str | None = None
    lifecycle_stage: str | None = None
    review_status: str | None = None
    sector: str | None = None
    regions: list[str] | None = None
    deployment_environment: str | None = None
    processes_personal_data: bool | None = None
    makes_automated_decisions: bool | None = None
    high_risk: bool | None = None


class AISystemPatch(BaseModel):
    """Partial update: every field is optional (name, if given, must be non-empty)."""

    name: str | None = None
    description: str | None = None
    business_purpose: str | None = None
    owner: str | None = None
    system_type: str | None = None
    risk_domain: str | None = None
    lifecycle_stage: str | None = None
    review_status: str | None = None
    sector: str | None = None
    regions: list[str] | None = None
    deployment_environment: str | None = None
    processes_personal_data: bool | None = None
    makes_automated_decisions: bool | None = None
    high_risk: bool | None = None


class AISystemOut(BaseModel):
    id: str
    name: str
    description: str | None
    business_purpose: str | None
    owner: str | None
    system_type: str
    risk_domain: str | None
    lifecycle_stage: str
    review_status: str
    sector: str
    regions: list[str] | None
    deployment_environment: str | None
    processes_personal_data: bool
    makes_automated_decisions: bool
    high_risk: bool
    last_reviewed_at: datetime | None
    last_changed_at: datetime | None
    component_count: int
    flow_count: int


class ComponentOut(BaseModel):
    id: str
    name: str
    component_type: str
    description: str | None
    provider: str | None
    region: str | None
    external: bool
    vendor_id: str | None
    data_asset_id: str | None
    data_categories: list | None
    config: dict | None


class FlowOut(BaseModel):
    id: str
    source_component_id: str | None
    target_component_id: str | None
    relation: str
    purpose: str | None
    data_categories: list | None
    contains_personal_data: bool
    cross_border: bool


class ComponentIn(BaseModel):
    key: str | None = None
    name: str
    type: str | None = None
    component_type: str | None = None
    description: str | None = None
    provider: str | None = None
    region: str | None = None
    external: bool | None = None
    vendor_id: str | None = None
    vendor: str | None = None
    data_categories: list[str] | None = None
    config: dict | None = None


class FlowIn(BaseModel):
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    source: str | None = None
    target: str | None = None
    relation: str | None = None
    purpose: str | None = None
    data_categories: list[str] | None = None
    contains_personal_data: bool | None = None
    cross_border: bool | None = None

    model_config = {"populate_by_name": True}


class ArchitectureImportIn(BaseModel):
    system: AISystemIn
    components: list[ComponentIn] = Field(default_factory=list)
    flows: list[FlowIn] = Field(default_factory=list)


# --- Serialization --------------------------------------------------------------


def _system_out(db: Session, system) -> AISystemOut:
    components = ai_system_service.list_components(db, system.id)
    flows = ai_system_service.list_flows(db, system.id)
    return AISystemOut(
        id=str(system.id),
        name=system.name,
        description=system.description,
        business_purpose=system.business_purpose,
        owner=system.owner,
        system_type=system.system_type,
        risk_domain=system.risk_domain,
        lifecycle_stage=system.lifecycle_stage,
        review_status=system.review_status,
        sector=system.sector,
        regions=system.regions,
        deployment_environment=system.deployment_environment,
        processes_personal_data=system.processes_personal_data,
        makes_automated_decisions=system.makes_automated_decisions,
        high_risk=system.high_risk,
        last_reviewed_at=system.last_reviewed_at,
        last_changed_at=system.last_changed_at,
        component_count=len(components),
        flow_count=len(flows),
    )


def _component_out(c) -> ComponentOut:
    return ComponentOut(
        id=str(c.id),
        name=c.name,
        component_type=c.component_type,
        description=c.description,
        provider=c.provider,
        region=c.region,
        external=c.external,
        vendor_id=str(c.vendor_id) if c.vendor_id else None,
        data_asset_id=str(c.data_asset_id) if c.data_asset_id else None,
        data_categories=c.data_categories,
        config=c.config,
    )


def _flow_out(f) -> FlowOut:
    return FlowOut(
        id=str(f.id),
        source_component_id=str(f.source_component_id) if f.source_component_id else None,
        target_component_id=str(f.target_component_id) if f.target_component_id else None,
        relation=f.relation,
        purpose=f.purpose,
        data_categories=f.data_categories,
        contains_personal_data=f.contains_personal_data,
        cross_border=f.cross_border,
    )


# --- Endpoints ------------------------------------------------------------------


@router.get("", response_model=list[AISystemOut])
def list_systems(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[AISystemOut]:
    return [_system_out(db, s) for s in ai_system_service.list_systems(db, ctx.organization_id)]


@router.post("", response_model=AISystemOut, status_code=201)
def create_system(
    payload: AISystemIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_INVENTORY)),
    db: Session = Depends(get_db),
) -> AISystemOut:
    system = ai_system_service.create_system(
        db, ctx.organization_id, ctx.user.id, payload.model_dump(exclude_none=True)
    )
    db.commit()
    return _system_out(db, system)


@router.post("/import", response_model=AISystemOut, status_code=201)
def import_architecture(
    payload: ArchitectureImportIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_INVENTORY)),
    db: Session = Depends(get_db),
) -> AISystemOut:
    body = {
        "system": payload.system.model_dump(exclude_none=True),
        "components": [c.model_dump(exclude_none=True, by_alias=True) for c in payload.components],
        "flows": [f.model_dump(exclude_none=True, by_alias=True) for f in payload.flows],
    }
    system = ai_system_service.import_architecture(db, ctx.organization_id, ctx.user.id, body)
    db.commit()
    return _system_out(db, system)


@router.get("/{system_id}", response_model=AISystemOut)
def get_system(
    system_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> AISystemOut:
    return _system_out(db, ai_system_service.get_system(db, ctx.organization_id, system_id))


@router.patch("/{system_id}", response_model=AISystemOut)
def update_system(
    system_id: uuid.UUID,
    payload: AISystemPatch,
    ctx: AuthContext = Depends(require_capability(MANAGE_INVENTORY)),
    db: Session = Depends(get_db),
) -> AISystemOut:
    system = ai_system_service.get_system(db, ctx.organization_id, system_id)
    ai_system_service.update_system(db, system, ctx.user.id, payload.model_dump(exclude_unset=True))
    db.commit()
    return _system_out(db, system)


@router.get("/{system_id}/components", response_model=list[ComponentOut])
def get_components(
    system_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[ComponentOut]:
    ai_system_service.get_system(db, ctx.organization_id, system_id)
    return [_component_out(c) for c in ai_system_service.list_components(db, system_id)]


@router.get("/{system_id}/flows", response_model=list[FlowOut])
def get_flows(
    system_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[FlowOut]:
    ai_system_service.get_system(db, ctx.organization_id, system_id)
    return [_flow_out(f) for f in ai_system_service.list_flows(db, system_id)]


@router.get("/{system_id}/graph")
def get_system_graph(
    system_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    ai_system_service.get_system(db, ctx.organization_id, system_id)
    return graph_service.ai_system_graph(db, ctx.organization_id, system_id)


@router.get("/{system_id}/facts")
def get_system_facts(
    system_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    """Derived applicability facts (consumed by the Phase 3 analysis engine)."""
    system = ai_system_service.get_system(db, ctx.organization_id, system_id)
    return ai_system_service.derive_facts(db, system)


@router.post("/{system_id}/analyze")
def analyze_system(
    system_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(ASSESS_CONTROLS)),
    db: Session = Depends(get_db),
) -> dict:
    """Run the deterministic analysis engine scoped to a single AI system.

    Returns each AI-scoped control's status, a plain-language reason and
    recommended actions for this system, plus the derived facts that drove the
    result. Read-only: no assessments or findings are persisted.
    """
    system = ai_system_service.get_system(db, ctx.organization_id, system_id)
    report = assessment_service.analyze_system(db, ctx.organization, system)
    record_audit(
        db,
        action="ai_system.analyzed",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="ai_system",
        entity_id=system.id,
        metadata={
            "applicable": report["summary"]["applicable"],
            "by_status": report["summary"]["by_status"],
        },
    )
    db.commit()
    return report
