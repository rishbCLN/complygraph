"""Remediation task endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_capability
from app.api.query import get_org_scoped
from app.core.audit import record_audit
from app.core.database import get_db, utcnow
from app.core.enums import TaskStatus
from app.core.rbac import MANAGE_TASKS
from app.models.findings import RemediationTask

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskIn(BaseModel):
    title: str
    description: str | None = None
    finding_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None = None
    priority: str | None = "MEDIUM"
    due_at: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee_id: uuid.UUID | None = None
    priority: str | None = None
    status: str | None = None
    due_at: datetime | None = None


class TaskOut(BaseModel):
    id: str
    title: str
    description: str | None
    finding_id: str | None
    assignee_id: str | None
    priority: str
    status: str
    due_at: datetime | None
    completed_at: datetime | None


def _out(t: RemediationTask) -> TaskOut:
    return TaskOut(
        id=str(t.id),
        title=t.title,
        description=t.description,
        finding_id=str(t.finding_id) if t.finding_id else None,
        assignee_id=str(t.assignee_id) if t.assignee_id else None,
        priority=t.priority,
        status=t.status,
        due_at=t.due_at,
        completed_at=t.completed_at,
    )


@router.get("", response_model=list[TaskOut])
def list_tasks(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
    finding_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[TaskOut]:
    stmt = select(RemediationTask).where(RemediationTask.organization_id == ctx.organization_id)
    if finding_id:
        stmt = stmt.where(RemediationTask.finding_id == finding_id)
    if status:
        stmt = stmt.where(RemediationTask.status == status)
    stmt = stmt.order_by(RemediationTask.created_at.desc())
    return [_out(t) for t in db.scalars(stmt)]


@router.post("", response_model=TaskOut, status_code=201)
def create_task(
    payload: TaskIn,
    ctx: AuthContext = Depends(require_capability(MANAGE_TASKS)),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = RemediationTask(
        organization_id=ctx.organization_id,
        status=TaskStatus.TODO.value,
        **payload.model_dump(exclude_none=True),
    )
    db.add(task)
    db.flush()
    record_audit(
        db,
        action="task.created",
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        entity_type="task",
        entity_id=task.id,
        metadata={"finding_id": str(payload.finding_id) if payload.finding_id else None},
    )
    db.commit()
    return _out(task)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    ctx: AuthContext = Depends(require_capability(MANAGE_TASKS)),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = get_org_scoped(db, RemediationTask, task_id, ctx.organization_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(task, key, value)
    if data.get("status") == TaskStatus.DONE.value and task.completed_at is None:
        task.completed_at = utcnow()
        record_audit(
            db,
            action="task.completed",
            organization_id=ctx.organization_id,
            user_id=ctx.user.id,
            entity_type="task",
            entity_id=task.id,
        )
    db.commit()
    return _out(task)
