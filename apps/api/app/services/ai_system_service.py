"""AI system inventory service.

CRUD for AI systems and their architecture (components + flows), structured
architecture import, and derivation of the applicability facts the analysis
engine consumes.

Design rules:
  - Only explicitly declared facts become AISystem columns. Derived facts
    (has_vendors, has_external_inference, ...) are computed here from the graph
    so unknown facts are never silently promoted to assumptions.
  - Component vendor references resolve to existing Vendor rows so the vendor /
    cross-border evaluators operate on the same inventory.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import utcnow
from app.core.enums import (
    AISystemReviewStatus,
    AISystemStage,
    AISystemType,
    ArchEdgeRelation,
    ComponentType,
    FactConfidence,
)
from app.core.errors import NotFoundError, ValidationError
from app.models.ai_systems import AISystem, AISystemComponent, AISystemFlow
from app.models.inventory import Vendor

# String fields on AISystem that a create/update payload may set directly.
_STRING_FIELDS = {
    "name",
    "description",
    "business_purpose",
    "owner",
    "risk_domain",
    "sector",
    "deployment_environment",
}
_BOOL_FIELDS = {"processes_personal_data", "makes_automated_decisions", "high_risk"}


def _coerce_enum(value: str | None, enum_cls, default: str | None) -> str | None:
    """Validate an incoming string against an enum, else raise (or use default)."""
    if value is None:
        return default
    candidate = str(value).strip().upper()
    valid = {e.value for e in enum_cls}
    if candidate not in valid:
        raise ValidationError(
            f"Invalid {enum_cls.__name__} '{value}'. Expected one of: {sorted(valid)}."
        )
    return candidate


# --- Queries --------------------------------------------------------------------


def list_systems(db: Session, org_id: uuid.UUID) -> list[AISystem]:
    return list(
        db.scalars(
            select(AISystem)
            .where(AISystem.organization_id == org_id)
            .order_by(AISystem.name)
        )
    )


def get_system(db: Session, org_id: uuid.UUID, system_id: uuid.UUID) -> AISystem:
    system = db.get(AISystem, system_id)
    if system is None or system.organization_id != org_id:
        raise NotFoundError("AI system not found.")
    return system


def list_components(db: Session, system_id: uuid.UUID) -> list[AISystemComponent]:
    return list(
        db.scalars(
            select(AISystemComponent)
            .where(AISystemComponent.ai_system_id == system_id)
            .order_by(AISystemComponent.created_at)
        )
    )


def list_flows(db: Session, system_id: uuid.UUID) -> list[AISystemFlow]:
    return list(
        db.scalars(
            select(AISystemFlow)
            .where(AISystemFlow.ai_system_id == system_id)
            .order_by(AISystemFlow.created_at)
        )
    )


# --- Fact derivation (feeds the applicability engine) ---------------------------


def derive_facts(db: Session, system: AISystem) -> dict:
    """Compute machine-readable applicability facts from the system + its graph.

    Declared facts are taken as-is. Structural facts are derived from components
    and flows. Nothing here infers a legal conclusion; it only reports observable
    architecture facts with explicit reasoning strings.
    """
    return derive_facts_with_provenance(db, system)[0]


def derive_facts_with_provenance(
    db: Session, system: AISystem
) -> tuple[dict, dict]:
    """Like :func:`derive_facts`, but also returns per-fact provenance.

    Returns ``(facts, provenance)`` where ``provenance[key]`` is
    ``{"confidence": FactConfidence, "band": ConfidenceBand, "basis": str}``.

    A structural fact that is True because a component/flow was found is
    ``OBSERVED``; one that is False because nothing was found is ``INFERRED``
    (absence of evidence). When no architecture is recorded at all, structural
    facts drop to ``UNKNOWN`` so a reviewer is not misled into reading "no
    external inference" as a positive assurance when it just means "no data".
    """
    components = list_components(db, system.id)
    flows = list_flows(db, system.id)

    external_components = [c for c in components if c.external]
    inference_components = [
        c for c in components if c.component_type in {ComponentType.MODEL.value, ComponentType.AGENT.value}
    ]
    external_inference = [c for c in inference_components if c.external]
    observability = [
        c
        for c in components
        if c.external
        and c.component_type in {ComponentType.SERVICE.value, ComponentType.API.value}
    ]

    # Regions outside India, gathered from components + declared system regions.
    regions = {(c.region or "").strip().lower() for c in components if c.region}
    for r in system.regions or []:
        regions.add(str(r).strip().lower())
    non_india_regions = sorted(r for r in regions if r and r not in {"india", "in"})

    vendor_ids = {c.vendor_id for c in components if c.vendor_id}

    has_architecture = len(components) > 0
    facts = {
        "system_id": str(system.id),
        "name": system.name,
        "sector": system.sector,
        "system_type": system.system_type,
        "lifecycle_stage": system.lifecycle_stage,
        "deployment_environment": system.deployment_environment,
        # Declared facts
        "processes_personal_data": system.processes_personal_data,
        "makes_automated_decisions": system.makes_automated_decisions,
        "high_risk": system.high_risk,
        # Derived structural facts
        "has_vendors": len(vendor_ids) > 0,
        "vendor_ids": [str(v) for v in vendor_ids],
        "has_external_components": len(external_components) > 0,
        "has_external_inference": len(external_inference) > 0,
        "uses_external_observability": len(observability) > 0,
        "has_cross_border_flow": any(f.cross_border for f in flows),
        "non_india_regions": non_india_regions,
        "component_count": len(components),
        "flow_count": len(flows),
        "is_production": system.lifecycle_stage == AISystemStage.PRODUCTION.value,
        "owner_assigned": bool(system.owner),
        "is_reviewed": system.review_status == AISystemReviewStatus.REVIEWED.value,
    }

    def structural(present: bool, basis_present: str, basis_absent: str) -> dict:
        """Provenance for a boolean derived from the presence/absence of graph data."""
        if present:
            conf = FactConfidence.OBSERVED
            basis = basis_present
        elif not has_architecture:
            conf = FactConfidence.UNKNOWN
            basis = "No architecture recorded for this system."
        else:
            conf = FactConfidence.INFERRED
            basis = basis_absent
        return {"confidence": conf.value, "band": conf.band.value, "basis": basis}

    def declared(basis: str) -> dict:
        return {
            "confidence": FactConfidence.DECLARED.value,
            "band": FactConfidence.DECLARED.band.value,
            "basis": basis,
        }

    provenance = {
        "sector": declared("Declared on the system record."),
        "system_type": declared("Declared on the system record."),
        "lifecycle_stage": declared("Declared on the system record."),
        "deployment_environment": declared("Declared on the system record."),
        "processes_personal_data": declared("Declared on the system record."),
        "makes_automated_decisions": declared("Declared on the system record."),
        "high_risk": declared("Declared on the system record."),
        "owner_assigned": declared(
            "Owner is set on the system record."
            if system.owner
            else "No owner recorded on the system."
        ),
        "is_reviewed": declared(f"Review status is '{system.review_status}'."),
        "is_production": declared(f"Lifecycle stage is '{system.lifecycle_stage}'."),
        "has_vendors": structural(
            len(vendor_ids) > 0,
            f"{len(vendor_ids)} component(s) reference a registered vendor.",
            "No component references a registered vendor.",
        ),
        "has_external_components": structural(
            len(external_components) > 0,
            f"{len(external_components)} component(s) are marked external.",
            "No component is marked external.",
        ),
        "has_external_inference": structural(
            len(external_inference) > 0,
            f"{len(external_inference)} model/agent component(s) run externally.",
            "No external model/agent component found.",
        ),
        "uses_external_observability": structural(
            len(observability) > 0,
            f"{len(observability)} external service/API component(s) present.",
            "No external service/API (observability) component found.",
        ),
        "has_cross_border_flow": structural(
            any(f.cross_border for f in flows),
            "At least one flow is marked cross-border.",
            "No flow is marked cross-border."
            if flows
            else "No data flows recorded for this system.",
        ),
        "non_india_regions": structural(
            len(non_india_regions) > 0,
            f"Regions outside India present: {', '.join(non_india_regions)}.",
            "All recorded regions are India (or none recorded).",
        ),
    }

    return facts, provenance


# --- Mutations ------------------------------------------------------------------


def create_system(
    db: Session, org_id: uuid.UUID, user_id: uuid.UUID, data: dict
) -> AISystem:
    name = (data.get("name") or "").strip()
    if not name:
        raise ValidationError("AI system name is required.")

    system = AISystem(
        organization_id=org_id,
        name=name,
        description=data.get("description"),
        business_purpose=data.get("business_purpose"),
        owner=data.get("owner"),
        system_type=_coerce_enum(data.get("system_type"), AISystemType, AISystemType.OTHER.value),
        risk_domain=data.get("risk_domain"),
        lifecycle_stage=_coerce_enum(
            data.get("lifecycle_stage"), AISystemStage, AISystemStage.DEVELOPMENT.value
        ),
        review_status=_coerce_enum(
            data.get("review_status"), AISystemReviewStatus, AISystemReviewStatus.NOT_REVIEWED.value
        ),
        sector=(data.get("sector") or "general").strip().lower(),
        regions=data.get("regions"),
        deployment_environment=data.get("deployment_environment"),
        processes_personal_data=bool(data.get("processes_personal_data", False)),
        makes_automated_decisions=bool(data.get("makes_automated_decisions", False)),
        high_risk=bool(data.get("high_risk", False)),
        last_changed_at=utcnow(),
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(system)
    db.flush()
    record_audit(
        db,
        action="ai_system.created",
        organization_id=org_id,
        user_id=user_id,
        entity_type="ai_system",
        entity_id=system.id,
        metadata={"name": system.name},
    )
    return system


def update_system(db: Session, system: AISystem, user_id: uuid.UUID, data: dict) -> AISystem:
    for key in _STRING_FIELDS:
        if key in data:
            value = data[key]
            if key == "name" and value is not None and not str(value).strip():
                raise ValidationError("AI system name cannot be empty.")
            if key == "sector" and value is not None:
                value = str(value).strip().lower()
            setattr(system, key, value)
    for key in _BOOL_FIELDS:
        if key in data:
            setattr(system, key, bool(data[key]))

    if "system_type" in data:
        system.system_type = _coerce_enum(data["system_type"], AISystemType, system.system_type)
    if "regions" in data:
        system.regions = data["regions"]
    if "lifecycle_stage" in data:
        system.lifecycle_stage = _coerce_enum(
            data["lifecycle_stage"], AISystemStage, system.lifecycle_stage
        )
    if "review_status" in data:
        new_status = _coerce_enum(data["review_status"], AISystemReviewStatus, system.review_status)
        system.review_status = new_status
        if new_status == AISystemReviewStatus.REVIEWED.value:
            system.last_reviewed_at = utcnow()

    system.last_changed_at = utcnow()
    system.updated_at = utcnow()
    record_audit(
        db,
        action="ai_system.updated",
        organization_id=system.organization_id,
        user_id=user_id,
        entity_type="ai_system",
        entity_id=system.id,
    )
    return system


def _resolve_vendor_id(
    db: Session, org_id: uuid.UUID, vendor_id: str | None, vendor_name: str | None
) -> uuid.UUID | None:
    """Resolve a component's vendor reference (by id or name) to an org vendor."""
    if vendor_id:
        try:
            vid = uuid.UUID(str(vendor_id))
        except ValueError:
            raise ValidationError(f"Invalid vendor_id '{vendor_id}'.") from None
        vendor = db.get(Vendor, vid)
        if vendor is None or vendor.organization_id != org_id:
            raise ValidationError("Referenced vendor not found in this organization.")
        return vendor.id
    if vendor_name:
        vendor = db.scalar(
            select(Vendor).where(
                Vendor.organization_id == org_id, Vendor.name == vendor_name.strip()
            )
        )
        if vendor is not None:
            return vendor.id
    return None


def add_component(
    db: Session, org_id: uuid.UUID, user_id: uuid.UUID, system: AISystem, spec: dict
) -> AISystemComponent:
    """Add a single component to an existing system and mark the system changed.

    Used both by the import path and by incremental architecture edits. Touching
    ``last_changed_at`` keeps the change-impact trail honest: the next analysis
    knows the architecture moved since the last snapshot.
    """
    component = _add_component(db, org_id, system, spec)
    system.last_changed_at = utcnow()
    system.updated_at = utcnow()
    record_audit(
        db,
        action="ai_system.component_added",
        organization_id=org_id,
        user_id=user_id,
        entity_type="ai_system",
        entity_id=system.id,
        metadata={"component": component.name, "type": component.component_type},
    )
    return component


def _add_component(
    db: Session, org_id: uuid.UUID, system: AISystem, spec: dict
) -> AISystemComponent:
    name = (spec.get("name") or "").strip()
    if not name:
        raise ValidationError("Every component requires a name.")
    ctype = _coerce_enum(
        spec.get("component_type") or spec.get("type"), ComponentType, ComponentType.SERVICE.value
    )
    vendor_id = _resolve_vendor_id(db, org_id, spec.get("vendor_id"), spec.get("vendor"))
    component = AISystemComponent(
        ai_system_id=system.id,
        name=name,
        component_type=ctype,
        description=spec.get("description"),
        provider=spec.get("provider"),
        region=spec.get("region"),
        external=bool(spec.get("external", False)),
        vendor_id=vendor_id,
        data_categories=spec.get("data_categories"),
        config=spec.get("config"),
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(component)
    db.flush()
    return component


def import_architecture(
    db: Session, org_id: uuid.UUID, user_id: uuid.UUID, body: dict
) -> AISystem:
    """Create a system plus its components and flows from a structured payload.

    Flows reference components by a local `key` (or `name`). Unknown keys raise a
    validation error rather than silently dropping the edge.
    """
    system_def = body.get("system") or {}
    system = create_system(db, org_id, user_id, system_def)

    key_to_id: dict[str, uuid.UUID] = {}
    for spec in body.get("components", []):
        component = _add_component(db, org_id, system, spec)
        key = spec.get("key") or spec.get("name")
        if key:
            key_to_id[str(key)] = component.id

    def _resolve(ref: str | None) -> uuid.UUID | None:
        if ref is None:
            return None
        if str(ref) not in key_to_id:
            raise ValidationError(
                f"Flow references unknown component '{ref}'. "
                f"Known components: {sorted(key_to_id)}."
            )
        return key_to_id[str(ref)]

    for spec in body.get("flows", []):
        source_ref = spec.get("from") or spec.get("source")
        target_ref = spec.get("to") or spec.get("target")
        source_id = _resolve(source_ref)
        target_id = _resolve(target_ref)
        relation = _coerce_enum(
            spec.get("relation"), ArchEdgeRelation, ArchEdgeRelation.SENDS_TO.value
        )
        db.add(
            AISystemFlow(
                ai_system_id=system.id,
                source_component_id=source_id,
                target_component_id=target_id,
                relation=relation,
                purpose=spec.get("purpose"),
                data_categories=spec.get("data_categories"),
                contains_personal_data=bool(spec.get("contains_personal_data", False)),
                cross_border=bool(spec.get("cross_border", False)),
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
    db.flush()
    record_audit(
        db,
        action="ai_system.imported",
        organization_id=org_id,
        user_id=user_id,
        entity_type="ai_system",
        entity_id=system.id,
        metadata={
            "components": len(body.get("components", [])),
            "flows": len(body.get("flows", [])),
        },
    )
    return system
