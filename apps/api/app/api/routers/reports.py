"""Reporting endpoints: executive, findings, data-inventory, audit, and PDF."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

import uuid

from app.api.deps import AuthContext, require_capability
from app.core.database import get_db
from app.core.rbac import GENERATE_REPORTS
from app.services import ai_system_service, reports_service

router = APIRouter(prefix="/reports", tags=["reports"])


def _tabular_response(rows: list[dict], fmt: str, filename: str) -> Response | dict:
    if fmt == "csv":
        return Response(
            content=reports_service.rows_to_csv(rows),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
        )
    return {"items": rows, "count": len(rows)}


@router.get("/executive")
def executive_report(
    ctx: AuthContext = Depends(require_capability(GENERATE_REPORTS)),
    db: Session = Depends(get_db),
) -> dict:
    return reports_service.executive_report(db, ctx.organization)


@router.get("/executive/pdf")
def executive_report_pdf(
    ctx: AuthContext = Depends(require_capability(GENERATE_REPORTS)),
    db: Session = Depends(get_db),
) -> Response:
    pdf = reports_service.executive_report_pdf(db, ctx.organization)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="complygraph-executive-report.pdf"'},
    )


@router.get("/findings")
def findings_report(
    fmt: str = Query("json", pattern="^(json|csv)$"),
    ctx: AuthContext = Depends(require_capability(GENERATE_REPORTS)),
    db: Session = Depends(get_db),
):
    rows = reports_service.findings_rows(db, ctx.organization_id)
    return _tabular_response(rows, fmt, "complygraph-findings")


@router.get("/data-inventory")
def data_inventory_report(
    fmt: str = Query("json", pattern="^(json|csv)$"),
    ctx: AuthContext = Depends(require_capability(GENERATE_REPORTS)),
    db: Session = Depends(get_db),
):
    rows = reports_service.data_inventory_rows(db, ctx.organization_id)
    return _tabular_response(rows, fmt, "complygraph-data-inventory")


@router.get("/audit")
def audit_report(
    fmt: str = Query("json", pattern="^(json|csv)$"),
    ctx: AuthContext = Depends(require_capability(GENERATE_REPORTS)),
    db: Session = Depends(get_db),
):
    rows = reports_service.audit_rows(db, ctx.organization_id)
    return _tabular_response(rows, fmt, "complygraph-audit")


@router.get("/system/{system_id}")
def system_report(
    system_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(GENERATE_REPORTS)),
    db: Session = Depends(get_db),
) -> dict:
    """Regulator-ready per-system compliance report (JSON).

    Every control carries its legal citation and honest legal-status label, and
    every derived fact carries its provenance, so the report is auditable end to
    end. Read-only.
    """
    system = ai_system_service.get_system(db, ctx.organization_id, system_id)
    return reports_service.system_report(db, ctx.organization, system)


@router.get("/system/{system_id}/pdf")
def system_report_pdf(
    system_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(GENERATE_REPORTS)),
    db: Session = Depends(get_db),
) -> Response:
    """Regulator-ready per-system compliance report rendered as PDF."""
    system = ai_system_service.get_system(db, ctx.organization_id, system_id)
    pdf = reports_service.system_report_pdf(db, ctx.organization, system)
    safe = "".join(ch for ch in system.name if ch.isalnum() or ch in "-_") or "system"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="complygraph-{safe}-report.pdf"'
        },
    )
