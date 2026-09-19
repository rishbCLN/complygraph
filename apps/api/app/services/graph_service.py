"""Graph service: builds the data-flow map and per-asset neighborhood graphs.

Nodes represent assets/applications/vendors; edges represent data flows between
them. The control graph overlay links controls, evidence, and findings. Output
is a plain {"nodes": [...], "edges": [...]} structure the frontend renders.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AssetType, Classification
from app.models.evidence import ControlEvidence, Evidence
from app.models.findings import Finding
from app.models.inventory import DataAsset, DataFlow, Vendor
from app.models.regulatory import Control, ControlAssessment

_PERSONAL = {Classification.PERSONAL_DATA.value, Classification.SENSITIVE_PERSONAL_DATA.value}

# Map asset_type -> graph node kind per the graph data model.
_NODE_KIND = {
    AssetType.DATABASE.value: "DATABASE",
    AssetType.TABLE.value: "DATASET",
    AssetType.FILE.value: "FILE",
    AssetType.DATASET.value: "DATASET",
    AssetType.APPLICATION.value: "APPLICATION",
    AssetType.API.value: "APPLICATION",
    AssetType.SAAS.value: "APPLICATION",
    AssetType.BUCKET.value: "FILE",
}


def _asset_node(a: DataAsset) -> dict:
    return {
        "id": str(a.id),
        "kind": _NODE_KIND.get(a.asset_type, "ASSET"),
        "type": "asset",
        "label": a.display_name or a.name,
        "asset_type": a.asset_type,
        "classification": a.classification,
        "sensitivity_level": a.sensitivity_level,
        "personal_data": a.classification in _PERSONAL,
        "system": a.system_name,
        "environment": a.environment,
    }


def _vendor_node(v: Vendor) -> dict:
    return {
        "id": f"vendor:{v.id}",
        "kind": "VENDOR",
        "type": "vendor",
        "label": v.name,
        "country": v.country,
        "contract_status": v.contract_status,
        "risk_level": v.risk_level,
    }


def _edge(flow: DataFlow, source: str, target: str) -> dict:
    if flow.cross_border:
        relation = "EXPORTS"
    elif flow.flow_type in {"PROCESSOR", "THIRD_PARTY"}:
        relation = "SHARES_WITH"
    elif flow.flow_type in {"BACKUP", "ARCHIVE"}:
        relation = "BACKS_UP"
    else:
        relation = "PROCESSES"
    return {
        "id": str(flow.id),
        "source": source,
        "target": target,
        "relation": relation,
        "flow_type": flow.flow_type,
        "personal_data": flow.contains_personal_data,
        "sensitive": flow.contains_sensitive_category,
        "cross_border": flow.cross_border,
        "purpose": flow.purpose,
        "discovered": flow.discovered,
        "confidence": flow.confidence,
    }


def data_graph(db: Session, org_id: uuid.UUID) -> dict:
    """Full data map for the organization."""
    assets = list(db.scalars(select(DataAsset).where(DataAsset.organization_id == org_id)))
    vendors = {v.id: v for v in db.scalars(select(Vendor).where(Vendor.organization_id == org_id))}
    flows = list(db.scalars(select(DataFlow).where(DataFlow.organization_id == org_id)))

    nodes: list[dict] = [_asset_node(a) for a in assets]
    asset_ids = {a.id for a in assets}

    edges: list[dict] = []
    referenced_vendor_ids: set[uuid.UUID] = set()
    for f in flows:
        if f.vendor_id and f.vendor_id in vendors:
            source = str(f.source_asset_id) if f.source_asset_id in asset_ids else None
            target = f"vendor:{f.vendor_id}"
            referenced_vendor_ids.add(f.vendor_id)
            if source:
                edges.append(_edge(f, source, target))
            continue
        if f.source_asset_id in asset_ids and f.destination_asset_id in asset_ids:
            edges.append(_edge(f, str(f.source_asset_id), str(f.destination_asset_id)))

    for vid in referenced_vendor_ids:
        nodes.append(_vendor_node(vendors[vid]))

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "assets": len(assets),
            "vendors": len(referenced_vendor_ids),
            "flows": len(edges),
            "cross_border_flows": sum(1 for e in edges if e["cross_border"]),
        },
    }


def control_graph(db: Session, org_id: uuid.UUID) -> dict:
    """Control-overlay graph: controls linked to their evidence and findings.

    Answers "why is this control in this state?" visually by connecting each
    control to the evidence that supports it and the findings it raised.
    """
    controls = list(db.scalars(select(Control)))

    # Latest assessment status per control for this org.
    status_by_control: dict[uuid.UUID, tuple[str, float]] = {}
    for a in db.scalars(
        select(ControlAssessment)
        .where(ControlAssessment.organization_id == org_id)
        .order_by(ControlAssessment.created_at.desc())
    ):
        status_by_control.setdefault(a.control_id, (a.status, a.score))

    nodes: list[dict] = []
    edges: list[dict] = []

    for c in controls:
        status, score = status_by_control.get(c.id, ("NO_EVIDENCE", 0.0))
        nodes.append(
            {
                "id": f"control:{c.id}",
                "kind": "CONTROL",
                "type": "control",
                "label": c.code,
                "title": c.title,
                "category": c.category,
                "status": status,
                "score": score,
            }
        )

    # Control -> Evidence edges (+ evidence nodes).
    ev_rows = db.execute(
        select(Control.id, Evidence, ControlEvidence.relation_type)
        .join(ControlEvidence, ControlEvidence.control_id == Control.id)
        .join(Evidence, Evidence.id == ControlEvidence.evidence_id)
        .where(Evidence.organization_id == org_id)
    ).all()
    seen_evidence: set[uuid.UUID] = set()
    for control_id, ev, relation in ev_rows:
        if ev.id not in seen_evidence:
            seen_evidence.add(ev.id)
            nodes.append(
                {
                    "id": f"evidence:{ev.id}",
                    "kind": "EVIDENCE",
                    "type": "evidence",
                    "label": ev.name,
                    "evidence_type": ev.type,
                    "status": ev.status,
                }
            )
        edges.append(
            {
                "id": f"ce:{control_id}:{ev.id}",
                "source": f"control:{control_id}",
                "target": f"evidence:{ev.id}",
                "relation": relation or "SUPPORTS",
            }
        )

    # Control -> Finding edges (+ finding nodes).
    findings = list(
        db.scalars(
            select(Finding).where(
                Finding.organization_id == org_id, Finding.control_id.is_not(None)
            )
        )
    )
    for f in findings:
        nodes.append(
            {
                "id": f"finding:{f.id}",
                "kind": "FINDING",
                "type": "finding",
                "label": f.title,
                "severity": f.severity,
                "risk_score": f.risk_score,
                "status": f.status,
            }
        )
        edges.append(
            {
                "id": f"cf:{f.control_id}:{f.id}",
                "source": f"control:{f.control_id}",
                "target": f"finding:{f.id}",
                "relation": "RAISED",
            }
        )

    status_counts: dict[str, int] = {}
    for status, _ in status_by_control.values():
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "controls": len(controls),
            "evidence": len(seen_evidence),
            "findings": len(findings),
            "status_counts": status_counts,
        },
    }


def asset_graph(db: Session, org_id: uuid.UUID, asset_id: uuid.UUID) -> dict:
    """Neighborhood graph for a single asset: direct upstream/downstream flows."""
    center = db.get(DataAsset, asset_id)
    if center is None or center.organization_id != org_id:
        return {"nodes": [], "edges": []}

    flows = list(
        db.scalars(
            select(DataFlow).where(
                DataFlow.organization_id == org_id,
                (DataFlow.source_asset_id == asset_id)
                | (DataFlow.destination_asset_id == asset_id),
            )
        )
    )

    node_ids: set[uuid.UUID] = {asset_id}
    vendor_ids: set[uuid.UUID] = set()
    edges: list[dict] = []
    for f in flows:
        if f.source_asset_id:
            node_ids.add(f.source_asset_id)
        if f.destination_asset_id:
            node_ids.add(f.destination_asset_id)
        if f.vendor_id:
            vendor_ids.add(f.vendor_id)
            src = str(f.source_asset_id) if f.source_asset_id else str(asset_id)
            edges.append(_edge(f, src, f"vendor:{f.vendor_id}"))
        elif f.source_asset_id and f.destination_asset_id:
            edges.append(_edge(f, str(f.source_asset_id), str(f.destination_asset_id)))

    nodes: list[dict] = []
    for aid in node_ids:
        a = db.get(DataAsset, aid)
        if a and a.organization_id == org_id:
            node = _asset_node(a)
            if aid == asset_id:
                node["center"] = True
            nodes.append(node)
    for vid in vendor_ids:
        v = db.get(Vendor, vid)
        if v and v.organization_id == org_id:
            nodes.append(_vendor_node(v))

    return {"nodes": nodes, "edges": edges}
