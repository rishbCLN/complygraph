"""CSV and JSON file scanner connectors.

Both parse safely with bounded sampling. JSON supports arrays of objects and
nested objects; nested paths are flattened (e.g. customer.contact.email).
"""

from __future__ import annotations

import csv
import io
import json

from app.core.enums import AssetType
from app.scanners.base import BaseConnector, DiscoveredAsset, DiscoveredField

_MAX_SAMPLE_ROWS = 100
_MAX_ROWS_READ = 10_000  # bound total rows read for row_count/sampling


class CSVConnector(BaseConnector):
    def __init__(self, content: bytes, filename: str):
        self._content = content
        self._filename = filename
        self.max_sample_rows = _MAX_SAMPLE_ROWS

    def test_connection(self) -> tuple[bool, str]:
        try:
            self._parse()
            return True, "CSV parsed successfully."
        except Exception as exc:  # noqa: BLE001
            return False, f"CSV parse failed: {type(exc).__name__}"

    def _parse(self) -> tuple[list[str], list[list[str]]]:
        text_data = self._content.decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text_data))
        rows = []
        headers: list[str] = []
        for i, row in enumerate(reader):
            if i == 0:
                headers = [h.strip() for h in row]
                continue
            if i > _MAX_ROWS_READ:
                break
            rows.append(row)
        if not headers:
            raise ValueError("CSV has no header row")
        return headers, rows

    def discover(self) -> list[DiscoveredAsset]:
        headers, rows = self._parse()
        fields: list[DiscoveredField] = []
        for idx, header in enumerate(headers):
            samples = [
                row[idx] for row in rows[: self.max_sample_rows] if idx < len(row) and row[idx]
            ]
            fields.append(DiscoveredField(name=header, data_type="text", samples=samples))
        return [
            DiscoveredAsset(
                name=self._filename,
                display_name=self._filename,
                asset_type=AssetType.FILE.value,
                system_name="file-upload",
                environment="upload",
                row_count=len(rows),
                fields=fields,
            )
        ]


class JSONConnector(BaseConnector):
    def __init__(self, content: bytes, filename: str):
        self._content = content
        self._filename = filename
        self.max_sample_rows = _MAX_SAMPLE_ROWS

    def test_connection(self) -> tuple[bool, str]:
        try:
            json.loads(self._content.decode("utf-8", errors="replace"))
            return True, "JSON parsed successfully."
        except Exception as exc:  # noqa: BLE001
            return False, f"JSON parse failed: {type(exc).__name__}"

    @staticmethod
    def _flatten(obj: dict, prefix: str = "") -> dict[str, str]:
        flat: dict[str, str] = {}
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                flat.update(JSONConnector._flatten(value, path))
            elif isinstance(value, list):
                # Only scalar-list leaves are sampled; nested object lists are summarized.
                if value and isinstance(value[0], dict):
                    flat.update(JSONConnector._flatten(value[0], path))
                else:
                    flat[path] = ",".join(str(v) for v in value[:3])
            else:
                flat[path] = "" if value is None else str(value)
        return flat

    def discover(self) -> list[DiscoveredAsset]:
        data = json.loads(self._content.decode("utf-8", errors="replace"))
        records: list[dict]
        if isinstance(data, list):
            records = [r for r in data if isinstance(r, dict)]
        elif isinstance(data, dict):
            # object with a list of records under some key, or a single record
            list_values = [v for v in data.values() if isinstance(v, list)]
            if list_values and all(isinstance(x, dict) for x in list_values[0][:1]):
                records = [r for r in list_values[0] if isinstance(r, dict)]
            else:
                records = [data]
        else:
            records = []

        samples_by_path: dict[str, list[str]] = {}
        for record in records[:_MAX_ROWS_READ]:
            for path, value in self._flatten(record).items():
                if value:
                    samples_by_path.setdefault(path, [])
                    if len(samples_by_path[path]) < self.max_sample_rows:
                        samples_by_path[path].append(value)

        fields = [
            DiscoveredField(
                name=path.split(".")[-1], data_type="json", samples=samples, field_path=path
            )
            for path, samples in samples_by_path.items()
        ]
        return [
            DiscoveredAsset(
                name=self._filename,
                display_name=self._filename,
                asset_type=AssetType.DATASET.value,
                system_name="file-upload",
                environment="upload",
                row_count=len(records),
                fields=fields,
            )
        ]
