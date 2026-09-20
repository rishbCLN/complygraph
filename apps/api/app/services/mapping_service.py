"""Cross-framework control mapping service.

Builds and queries the control-equivalence graph across regulatory packs and
computes evidence-reuse candidates: when a source control (in framework A) is
mapped to a target control (in framework B) with a coverage relation, evidence
already collected for the source can be surfaced as a reuse candidate for the
target — always flagged for human review, never auto-applied.
"""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.enums import MappingRelation
from app.core.errors import NotFoundError, ValidationError
from app.models.evidence import ControlEvidence, Evidence
from app.models.regulatory import (
    Control,
    ControlMapping,
    Obligation,
    Regulation,
)
from app.services.evidence_service import compute_freshness


def _visible_mappings_stmt(org_id: uuid.UUID):
    """Mappings visible to an org: system (NULL org) + that org's own."""
    return select(ControlMapping).where(
        or_(
            ControlMapping.organization_id.is_(None),
            ControlMapping.organization_id == org_id,
        )
    )


def control_framework(db: Session, control: Control) -> Regulation | None:
    obligation = db.get(Obligation, control.obligation_id)
    if obligation is None:
        return None
    return db.get(Regulation, obligation.regulation_id)


def list_mappings(
    db: Session,
    org_id: uuid.UUID,
    control_id: uuid.UUID | None = None,
) -> list[ControlMapping]:
    stmt = _visible_mappings_stmt(org_id)
    if control_id is not None:
        stmt = stmt.where(
            or_(
                ControlMapping.source_control_id == control_id,
                ControlMapping.target_control_id == control_id,
            )
        )
    return list(db.scalars(stmt.order_by(ControlMapping.created_at)))


def create_mapping(
    db: Session,
    org_id: uuid.UUID,
    user_id: uuid.UUID | None,
    *,
    source_control_id: uuid.UUID,
    target_control_id: uuid.UUID,
    relation_type: str,
    rationale: str | None,
    confidence: float | None,
) -> ControlMapping:
    if source_control_id == target_control_id:
        raise ValidationError("A control cannot be mapped to itself.")
    if relation_type not in {r.value for r in MappingRelation}:
        raise ValidationError(f"Unsupported relation type: {relation_type}")
    source = db.get(Control, source_control_id)
    target = db.get(Control, target_control_id)
    if source is None or target is None:
        raise NotFoundError("Source or target control not found.")

    # Prevent duplicate org-authored mappings for the same directed pair.
    existing = db.scalar(
        select(ControlMapping).where(
            ControlMapping.source_control_id == source_control_id,
            ControlMapping.target_control_id == target_control_id,
            ControlMapping.organization_id == org_id,
        )
    )
    if existing is not None:
        raise ValidationError("A mapping for this control pair already exists.")

    if confidence is None:
        confidence = 1.0
    confidence = max(0.0, min(1.0, float(confidence)))

    mapping = ControlMapping(
        source_control_id=source_control_id,
        target_control_id=target_control_id,
        relation_type=relation_type,
        rationale=rationale,
        confidence=confidence,
        organization_id=org_id,
        created_by=user_id,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(mapping)
    db.flush()
    return mapping


def delete_mapping(db: Session, org_id: uuid.UUID, mapping_id: uuid.UUID) -> ControlMapping:
    mapping = db.get(ControlMapping, mapping_id)
    if mapping is None:
        raise NotFoundError("Mapping not found.")
    # System mappings (NULL org) are part of shared knowledge and cannot be
    # deleted by a tenant; only the org's own mappings are mutable.
    if mapping.organization_id != org_id:
        raise ValidationError("Only organization-authored mappings can be deleted.")
    db.delete(mapping)
    db.flush()
    return mapping


def _control_brief(db: Session, control: Control) -> dict:
    reg = control_framework(db, control)
    return {
        "id": str(control.id),
        "code": control.code,
        "title": control.title,
        "category": control.category,
        "regulation_id": str(reg.id) if reg else None,
        "regulation_name": reg.name if reg else None,
    }


def mappings_for_control(db: Session, org_id: uuid.UUID, control_id: uuid.UUID) -> list[dict]:
    """Return mappings touching a control, normalised to an outward view.

    For each mapping the `direction` tells whether the queried control is the
    source ("outgoing") or the target ("incoming"), and `other` describes the
    control on the far side.
    """
    control = db.get(Control, control_id)
    if control is None:
        raise NotFoundError("Control not found.")
    out: list[dict] = []
    for m in list_mappings(db, org_id, control_id):
        if m.source_control_id == control_id:
            direction = "outgoing"
            other = db.get(Control, m.target_control_id)
        else:
            direction = "incoming"
            other = db.get(Control, m.source_control_id)
        if other is None:
            continue
        out.append(
            {
                "id": str(m.id),
                "relation_type": m.relation_type,
                "rationale": m.rationale,
                "confidence": m.confidence,
                "system": m.organization_id is None,
                "direction": direction,
                "other": _control_brief(db, other),
            }
        )
    return out


def reusable_evidence(db: Session, org_id: uuid.UUID, target_control_id: uuid.UUID, now=None) -> list[dict]:
    """Evidence collected for controls that cover this target control.

    A source control "covers" the target when a visible mapping from source ->
    target has an EQUIVALENT or SUPERSET relation. Returned candidates are always
    advisory: reuse requires human review before the evidence is linked here.
    """
    target = db.get(Control, target_control_id)
    if target is None:
        raise NotFoundError("Control not found.")

    now = now or utcnow()
    # Source controls that cover this target.
    covering: list[tuple[ControlMapping, uuid.UUID]] = []
    for m in list_mappings(db, org_id, target_control_id):
        if m.target_control_id != target_control_id:
            continue
        relation = MappingRelation(m.relation_type)
        if relation.source_covers_target:
            covering.append((m, m.source_control_id))

    if not covering:
        return []

    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for mapping, source_control_id in covering:
        source = db.get(Control, source_control_id)
        if source is None:
            continue
        rows = db.execute(
            select(Evidence, ControlEvidence)
            .join(ControlEvidence, ControlEvidence.evidence_id == Evidence.id)
            .where(
                ControlEvidence.control_id == source_control_id,
                Evidence.organization_id == org_id,
            )
        ).all()
        for ev, ce in rows:
            key = (str(source_control_id), str(ev.id))
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "evidence_id": str(ev.id),
                    "evidence_name": ev.name,
                    "evidence_type": ev.type,
                    "status": compute_freshness(ev.collected_at, ev.expires_at, now),
                    "relation_type_on_source": ce.relation_type,
                    "via_mapping_id": str(mapping.id),
                    "mapping_relation": mapping.relation_type,
                    "mapping_confidence": mapping.confidence,
                    "source_control": _control_brief(db, source),
                    "requires_review": True,
                }
            )
    return out


def mapping_graph(db: Session, org_id: uuid.UUID) -> dict:
    """Nodes (controls that participate in a mapping, grouped by framework) and
    edges (the mappings) for the mapping-explorer view."""
    mappings = list_mappings(db, org_id)
    node_ids: set[uuid.UUID] = set()
    for m in mappings:
        node_ids.add(m.source_control_id)
        node_ids.add(m.target_control_id)

    nodes = []
    for cid in node_ids:
        control = db.get(Control, cid)
        if control is None:
            continue
        nodes.append(_control_brief(db, control))
    nodes.sort(key=lambda n: (n["regulation_name"] or "", n["code"]))

    edges = [
        {
            "id": str(m.id),
            "source": str(m.source_control_id),
            "target": str(m.target_control_id),
            "relation_type": m.relation_type,
            "confidence": m.confidence,
            "system": m.organization_id is None,
        }
        for m in mappings
    ]
    return {"nodes": nodes, "edges": edges}
