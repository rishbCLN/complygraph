"""Shared helpers for org-scoped queries and pagination."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError


def paginate(db: Session, stmt: Select, page: int, page_size: int) -> tuple[list, int]:
    page = max(1, page)
    page_size = max(1, min(200, page_size))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(db.scalars(stmt.limit(page_size).offset((page - 1) * page_size)))
    return rows, total


def get_org_scoped(db: Session, model, entity_id: uuid.UUID, organization_id: uuid.UUID):
    """Fetch a row by id ensuring it belongs to the caller's organization."""
    obj = db.get(model, entity_id)
    if obj is None or getattr(obj, "organization_id", None) != organization_id:
        raise NotFoundError(f"{model.__name__} not found.")
    return obj
