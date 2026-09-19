"""Shared Pydantic schema helpers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class MessageResponse(BaseModel):
    message: str


class IdResponse(BaseModel):
    id: uuid.UUID
