"""Connector interfaces and implementations.

BaseConnector defines the pluggable interface so future connectors (SaaS, cloud
buckets, etc.) can be added later. Only Postgres/CSV/JSON/Demo are implemented.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.scanners.classifier import FieldSample


@dataclass
class DiscoveredField:
    name: str
    data_type: str | None
    samples: list[str] = field(default_factory=list)
    field_path: str | None = None


@dataclass
class DiscoveredAsset:
    name: str  # stable logical name, e.g. schema.table or filename
    display_name: str
    asset_type: str
    system_name: str | None
    environment: str | None = None
    row_count: int | None = None
    fields: list[DiscoveredField] = field(default_factory=list)


class BaseConnector(ABC):
    """Pluggable connector interface. Implementations must be safe and read-only."""

    max_sample_rows = 100

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Return (ok, message). Never include secrets in the message."""

    @abstractmethod
    def discover(self) -> list[DiscoveredAsset]:
        """Enumerate assets, fields, and bounded samples. Never returns full datasets."""

    def to_field_sample(self, field_: DiscoveredField) -> FieldSample:
        return FieldSample(
            name=field_.name,
            data_type=field_.data_type,
            field_path=field_.field_path,
            values=field_.samples[: self.max_sample_rows],
        )
