"""Connector management + scan trigger endpoints."""

from __future__ import annotations

import base64
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.api.query import get_org_scoped
from app.core.audit import record_audit
from app.core.config import settings
from app.core.database import get_db, utcnow
from app.core.enums import ConnectorStatus, ConnectorType, ScanStatus
from app.core.errors import ValidationError
from app.core.rbac import MANAGE_CONNECTORS, RUN_SCAN
from app.models.findings import Scan
from app.models.inventory import Connector
from app.security.encryption import encrypt_json

router = APIRouter(tags=["connectors"])


class ConnectorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str
    dsn: str | None = None  # for POSTGRES/DEMO


class ConnectorUpdate(BaseModel):
    name: str | None = None
    status: str | None = None


class ConnectorOut(BaseModel):
    id: str
    name: str
    type: str
    status: str
    last_scan_at: datetime | None
    created_at: datetime


def _to_out(c: Connector) -> ConnectorOut:
    return ConnectorOut(
        id=str(c.id),
        name=c.name,
        type=c.type,
        status=c.status,
        last_scan_at=c.last_scan_at,
        created_at=c.created_at,
    )


@router.get("/connectors", response_model=list[ConnectorOut])
def list_connectors(
    ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)
) -> list[ConnectorOut]:
    rows = db.scalars(
        select(Connector)
        .where(Connector.organization_id == ctx.organization_id)
        .order_by(Connector.created_at.desc())
    )
    return [_to_out(c) for c in rows]


@router.post("/connectors", response_model=ConnectorOut, status_code=201)
def create_connector(
    payload: ConnectorCreate,
    ctx: AuthContext = Depends(require_capability(MANAGE_CONNECTORS)),
    db: Session = Depends(get_db),
) -> ConnectorOut:
    if payload.type not in {t.value for t in ConnectorType}:
        raise ValidationError(f"Unsupported connector type: {payload.type}")
    config: dict = {}
    if payload.dsn:
        config["dsn"] = payload.dsn
    connector = Connector(
        organization_id=ctx.organization_id,
        name=payload.name,
        type=payload.type,
        status=ConnectorStatus.CONFIGURED.value,
        configuration_encrypted=encrypt_json(config) if config else None,
    )
    db.add(connector)
    db.flush()
    record_audit(
        db,
        action="connector.created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="connector",
        entity_id=connector.id,
        metadata={"type": connector.type},
    )
    db.commit()
    db.refresh(connector)
    return _to_out(connector)


@router.post("/connectors/upload", response_model=ConnectorOut, status_code=201)
async def upload_file_connector(
    file: UploadFile = File(...),
    ctx: AuthContext = Depends(require_capability(MANAGE_CONNECTORS)),
    db: Session = Depends(get_db),
) -> ConnectorOut:
    """Create a CSV/JSON connector from an uploaded file (validated + size-limited)."""
    filename = (file.filename or "upload").strip()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {"csv", "json"}:
        raise ValidationError("Only .csv and .json uploads are supported for scanning.")
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise ValidationError("File exceeds the 25 MB upload limit.")
    conn_type = ConnectorType.CSV.value if ext == "csv" else ConnectorType.JSON.value
    config = {"filename": filename, "content_b64": base64.b64encode(content).decode("ascii")}
    connector = Connector(
        organization_id=ctx.organization_id,
        name=filename,
        type=conn_type,
        status=ConnectorStatus.CONFIGURED.value,
        configuration_encrypted=encrypt_json(config),
    )
    db.add(connector)
    db.flush()
    record_audit(
        db,
        action="connector.created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="connector",
        entity_id=connector.id,
        metadata={"type": conn_type, "size_bytes": len(content)},
    )
    db.commit()
    db.refresh(connector)
    return _to_out(connector)


@router.get("/connectors/{connector_id}", response_model=ConnectorOut)
def get_connector(
    connector_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> ConnectorOut:
    return _to_out(get_org_scoped(db, Connector, connector_id, ctx.organization_id))


@router.patch("/connectors/{connector_id}", response_model=ConnectorOut)
def update_connector(
    connector_id: uuid.UUID,
    payload: ConnectorUpdate,
    ctx: AuthContext = Depends(require_capability(MANAGE_CONNECTORS)),
    db: Session = Depends(get_db),
) -> ConnectorOut:
    connector = get_org_scoped(db, Connector, connector_id, ctx.organization_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(connector, key, value)
    db.commit()
    db.refresh(connector)
    return _to_out(connector)


@router.delete("/connectors/{connector_id}", status_code=204, response_model=None)
def delete_connector(
    connector_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_CONNECTORS)),
    db: Session = Depends(get_db),
) -> None:
    connector = get_org_scoped(db, Connector, connector_id, ctx.organization_id)
    db.delete(connector)
    record_audit(
        db,
        action="connector.deleted",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="connector",
        entity_id=connector_id,
    )
    db.commit()


@router.post("/connectors/{connector_id}/test")
def test_connector(
    connector_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(MANAGE_CONNECTORS)),
    db: Session = Depends(get_db),
) -> dict:
    from app.services.scan_service import build_connector

    connector = get_org_scoped(db, Connector, connector_id, ctx.organization_id)
    impl = build_connector(connector)
    ok, message = impl.test_connection()
    connector.status = ConnectorStatus.CONNECTED.value if ok else ConnectorStatus.ERROR.value
    db.commit()
    return {"ok": ok, "message": message}


@router.post("/connectors/{connector_id}/scan")
def scan_connector(
    connector_id: uuid.UUID,
    ctx: AuthContext = Depends(require_capability(RUN_SCAN)),
    db: Session = Depends(get_db),
) -> dict:
    """Queue a scan. Runs on the worker when Redis is available, else in-process."""
    connector = get_org_scoped(db, Connector, connector_id, ctx.organization_id)
    scan = Scan(
        organization_id=ctx.organization_id,
        connector_id=connector.id,
        status=ScanStatus.QUEUED.value,
        stage="Queued",
        progress=0,
        created_at=utcnow(),
    )
    db.add(scan)
    db.flush()
    scan_id = str(scan.id)
    record_audit(
        db,
        action="scan.queued",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="scan",
        entity_id=scan.id,
    )
    db.commit()

    from app.workers.tasks import run_scan_task

    run_scan_task.delay(scan_id)
    return {"scan_id": scan_id, "status": "QUEUED"}


class ScanOut(BaseModel):
    id: str
    connector_id: str | None
    status: str
    stage: str | None
    progress: int
    items_scanned: int
    findings_created: int
    changes: dict | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


@router.get("/scans/{scan_id}", response_model=ScanOut, tags=["scans"])
def get_scan(
    scan_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> ScanOut:
    scan = get_org_scoped(db, Scan, scan_id, ctx.organization_id)
    return ScanOut(
        id=str(scan.id),
        connector_id=str(scan.connector_id) if scan.connector_id else None,
        status=scan.status,
        stage=scan.stage,
        progress=scan.progress,
        items_scanned=scan.items_scanned,
        findings_created=scan.findings_created,
        changes=scan.changes,
        error_message=scan.error_message,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
    )


@router.get("/scans", response_model=list[ScanOut], tags=["scans"])
def list_scans(
    ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)
) -> list[ScanOut]:
    rows = db.scalars(
        select(Scan)
        .where(Scan.organization_id == ctx.organization_id)
        .order_by(Scan.created_at.desc())
        .limit(50)
    )
    return [
        ScanOut(
            id=str(s.id),
            connector_id=str(s.connector_id) if s.connector_id else None,
            status=s.status,
            stage=s.stage,
            progress=s.progress,
            items_scanned=s.items_scanned,
            findings_created=s.findings_created,
            changes=s.changes,
            error_message=s.error_message,
            created_at=s.created_at,
            completed_at=s.completed_at,
        )
        for s in rows
    ]
