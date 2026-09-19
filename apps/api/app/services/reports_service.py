"""Reporting service: executive, findings, data-inventory, and audit reports.

Reports are derived entirely from persisted platform data. Exports are offered
as JSON, CSV, and (for the executive report) PDF. Language avoids any claim of
legal certification or guaranteed compliance.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.controls.effective_date import control_temporal_status, is_control_active
from app.core.enums import Classification, ControlStatus, FindingStatus
from app.models.findings import Finding
from app.models.identity import AuditEvent
from app.models.inventory import DataAsset, DataFlow, Vendor
from app.models.regulatory import Control, Obligation, Regulation
from app.services import dashboard_service
from app.services.assessment_service import get_assessment_date, latest_assessment

_PERSONAL = {Classification.PERSONAL_DATA.value, Classification.SENSITIVE_PERSONAL_DATA.value}
_OPEN = {FindingStatus.OPEN.value, FindingStatus.ACKNOWLEDGED.value, FindingStatus.IN_PROGRESS.value}

DISCLAIMER = (
    "ComplyGraph is governance, evidence-collection and internal-control assessment "
    "software. This report is an internal governance aid. It is not legal advice and "
    "does not constitute official certification or a guarantee of compliance with the "
    "DPDP Act 2023 or any other law."
)


# --- Executive report -----------------------------------------------------------


def executive_report(db: Session, org) -> dict:
    org_id = org.id
    assessment_date = get_assessment_date(org)
    summary = dashboard_service.summary(db, org)

    # Control posture by regulation.
    controls = list(db.scalars(select(Control)))
    by_regulation: dict[str, dict] = {}
    for c in controls:
        obligation = db.get(Obligation, c.obligation_id)
        regulation = db.get(Regulation, obligation.regulation_id) if obligation else None
        reg_name = regulation.name if regulation else "Uncategorized"
        bucket = by_regulation.setdefault(
            reg_name, {"regulation": reg_name, "active": 0, "upcoming": 0, "passing": 0, "failing": 0}
        )
        if is_control_active(c.effective_from, assessment_date):
            bucket["active"] += 1
            la = latest_assessment(db, org_id, c.id)
            st = la.status if la else ControlStatus.NO_EVIDENCE.value
            if st in {ControlStatus.PASS.value, ControlStatus.PARTIAL.value}:
                bucket["passing"] += 1
            elif st in {ControlStatus.FAIL.value, ControlStatus.NO_EVIDENCE.value}:
                bucket["failing"] += 1
        else:
            bucket["upcoming"] += 1

    top_findings = dashboard_service.top_findings(db, org, limit=10)

    return {
        "organization": org.name,
        "assessment_date": assessment_date.isoformat(),
        "generated_at": datetime.utcnow().isoformat(),
        "summary": summary,
        "control_posture_by_regulation": list(by_regulation.values()),
        "top_findings": top_findings,
        "risk_distribution": dashboard_service.risk_trend(db, org),
        "disclaimer": DISCLAIMER,
    }


def executive_report_pdf(db: Session, org) -> bytes:
    """Render the executive report as a PDF byte string."""
    from reportlab.lib import colors  # noqa: PLC0415
    from reportlab.lib.pagesizes import A4  # noqa: PLC0415
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # noqa: PLC0415
    from reportlab.lib.units import mm  # noqa: PLC0415
    from reportlab.platypus import (  # noqa: PLC0415
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    data = executive_report(db, org)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="ComplyGraph Executive Report")
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    elements: list = []

    elements.append(Paragraph("ComplyGraph Executive Report", styles["Title"]))
    elements.append(Paragraph(f"Organization: {data['organization']}", styles["Normal"]))
    elements.append(Paragraph(f"Assessment date: {data['assessment_date']}", styles["Normal"]))
    elements.append(Paragraph(f"Generated: {data['generated_at']}", styles["Normal"]))
    elements.append(Spacer(1, 6 * mm))

    s = data["summary"]
    elements.append(Paragraph("Posture Summary", styles["Heading2"]))
    summary_rows = [
        ["Metric", "Value"],
        ["Data assets", s["data_assets"]],
        ["Personal-data assets", s["personal_data_assets"]],
        ["Open findings", s["open_findings"]],
        ["Critical findings", s["critical_findings"]],
        ["Control coverage", f"{s['control_coverage']}%"],
        ["Evidence stale/expired", f"{s['evidence_stale_pct']}%"],
        ["Unmapped personal-data flows", s["unmapped_data_flows"]],
        ["Vendors processing personal data", s["vendors_processing_personal_data"]],
        ["Upcoming obligations", s["upcoming_obligations"]],
    ]
    t = Table(summary_rows, colWidths=[90 * mm, 60 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
            ]
        )
    )
    elements.append(t)
    elements.append(Spacer(1, 6 * mm))

    elements.append(Paragraph("Control Posture by Regulation", styles["Heading2"]))
    reg_rows = [["Regulation", "Active", "Passing", "Failing", "Upcoming"]]
    for r in data["control_posture_by_regulation"]:
        reg_rows.append([r["regulation"], r["active"], r["passing"], r["failing"], r["upcoming"]])
    t2 = Table(reg_rows, colWidths=[70 * mm, 20 * mm, 20 * mm, 20 * mm, 20 * mm])
    t2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(t2)
    elements.append(Spacer(1, 6 * mm))

    elements.append(Paragraph("Top Findings by Risk", styles["Heading2"]))
    find_rows = [["Title", "Severity", "Risk", "Status"]]
    for f in data["top_findings"]:
        find_rows.append([f["title"][:60], f["severity"], f["risk_score"], f["status"]])
    if len(find_rows) == 1:
        find_rows.append(["No open findings", "-", "-", "-"])
    t3 = Table(find_rows, colWidths=[90 * mm, 25 * mm, 15 * mm, 25 * mm])
    t3.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(t3)
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph(data["disclaimer"], small))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# --- Tabular reports (JSON rows + CSV) ------------------------------------------


def findings_rows(db: Session, org_id: uuid.UUID) -> list[dict]:
    rows = db.scalars(
        select(Finding)
        .where(Finding.organization_id == org_id)
        .order_by(Finding.risk_score.desc())
    )
    out = []
    for f in rows:
        control = db.get(Control, f.control_id) if f.control_id else None
        out.append(
            {
                "id": str(f.id),
                "title": f.title,
                "severity": f.severity,
                "risk_score": f.risk_score,
                "status": f.status,
                "control_code": control.code if control else "",
                "data_categories": f.data_categories or "",
                "detected_at": f.detected_at.isoformat() if f.detected_at else "",
                "due_at": f.due_at.isoformat() if f.due_at else "",
                "owner": f.owner or "",
            }
        )
    return out


def data_inventory_rows(db: Session, org_id: uuid.UUID) -> list[dict]:
    assets = db.scalars(
        select(DataAsset).where(DataAsset.organization_id == org_id).order_by(DataAsset.name)
    )
    out = []
    for a in assets:
        out.append(
            {
                "id": str(a.id),
                "name": a.display_name or a.name,
                "asset_type": a.asset_type,
                "classification": a.classification,
                "sensitivity_level": a.sensitivity_level,
                "system": a.system_name or "",
                "environment": a.environment or "",
                "owner": a.owner or "",
                "row_count": a.row_count if a.row_count is not None else "",
                "personal_data": a.classification in _PERSONAL,
            }
        )
    return out


def audit_rows(db: Session, org_id: uuid.UUID, limit: int = 1000) -> list[dict]:
    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.organization_id == org_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": str(e.id),
            "action": e.action,
            "entity_type": e.entity_type or "",
            "entity_id": e.entity_id or "",
            "user_id": str(e.user_id) if e.user_id else "",
            "ip_address": e.ip_address or "",
            "created_at": e.created_at.isoformat() if e.created_at else "",
        }
        for e in events
    ]


def rows_to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()
