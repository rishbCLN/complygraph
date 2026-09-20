"""Cross-framework control mapping endpoints.

Exposes the control-equivalence graph, org-authored mapping CRUD, and the
mapping-explorer graph. Per-control mapping and evidence-reuse views live on the
controls router (see controls.py).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.rbac import MANAGE_REGULATORY
from app.services import mapping_service

router = APIRouter(prefix="/control-mappings", tags=["control-mappings"])


class ControlBrief(BaseModel):
    id: str
    code: str
    title: str
    category: str
    regulation_id: str | None
    regulation_name: str | None


class MappingOut(BaseModel):
    id: str
    source: ControlBrief
    target: ControlBrief
    relation_type: str
    rationale: str | None
    confidence: float
    system: bool


class MappingIn(BaseModel):
    source_control_id: uuid.UUID
    target_control_id: uuid.UUID
    relation_type: str
    rationale: str | None = None
    confidence: float | None = None


class MappingGraphOut(BaseModel):
    nodes: list[ControlBrief]
    edges: list[dict]


def _out(db: Session, mapping) -> MappingOut:
    from app.models.regulatory import Control

    source = db.get(Control, mapping.source_control_id)
    target = db.get(Control, mapping.target_control_id)
    return MappingOut(
        id=str(mapping.id),
        source=ControlBrief(**mapping_service._control_brief(db, source)),
        target=ControlBrief(**mapping_service._control_brief(db, target)),
        relation_type=mapping.relation_type,
        rationale=mapping.rationale,
        confidence=mapping.confidence,
        system=mapping.organization_id is None,
    )


@router.get("", response_model=list[MappingOut])
def list_mappings(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> list[MappingOut]:
    return [_out(db, m) for m in mapping_service.list_mappings(db, ctx.organization_id)]


@router.get("/graph", response_model=MappingGraphOut)
def mapping_graph(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> MappingGraphOut:
    graph = mapping_service.mapping_graph(db, ctx.organization_id)
    return MappingGraphOut(
        nodes=[ControlBrief(**n) for n in graph["nodes"]],
        edges=graph["edges"],
    )


@router.post("", response_model=MappingOut, status_code=201)
def create_mapping(
    payload: MappingIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_REGULATORY)),
    db: Session = Depends(get_db),
) -> MappingOut:
    mapping = mapping_service.create_mapping(
        db,
        ctx.organization_id,
        ctx.user.id,
        source_control_id=payload.source_control_id,
        target_control_id=payload.target_control_id,
        relation_type=payload.relation_type,
        rationale=payload.rationale,
        confidence=payload.confidence,
    )
    record_audit(
        db,
        action="control_mapping.created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="control_mapping",
        entity_id=mapping.id,
        metadata={"relation_type": mapping.relation_type},
    )
    db.commit()
    db.refresh(mapping)
    return _out(db, mapping)


@router.delete("/{mapping_id}", status_code=204)
def delete_mapping(
    mapping_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_REGULATORY)),
    db: Session = Depends(get_db),
) -> None:
    mapping_service.delete_mapping(db, ctx.organization_id, mapping_id)
    record_audit(
        db,
        action="control_mapping.deleted",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="control_mapping",
        entity_id=mapping_id,
    )
    db.commit()
