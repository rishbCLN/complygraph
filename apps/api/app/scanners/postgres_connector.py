"""PostgreSQL scanner connector.

Safely connects to a PostgreSQL source, enumerates schemas/tables/columns,
counts rows, and samples a bounded number of values per column. Only metadata
and redacted detection evidence are ever returned; raw sampled rows are never
persisted.
"""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from app.core.enums import AssetType
from app.scanners.base import BaseConnector, DiscoveredAsset, DiscoveredField

# Schemas we never inspect.
_SYSTEM_SCHEMAS = {"pg_catalog", "information_schema", "pg_toast"}


class PostgresConnector(BaseConnector):
    def __init__(self, dsn: str, sample_rows: int = 100):
        self._dsn = dsn
        self.max_sample_rows = min(sample_rows, 100)

    def _engine(self):
        # Read-only intent; short timeouts to avoid hanging the worker.
        return create_engine(
            self._dsn,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )

    def test_connection(self) -> tuple[bool, str]:
        try:
            engine = self._engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, "Connection successful."
        except Exception as exc:  # noqa: BLE001
            # Message intentionally omits DSN/credentials.
            return False, f"Connection failed: {type(exc).__name__}"

    def discover(self) -> list[DiscoveredAsset]:
        engine = self._engine()
        assets: list[DiscoveredAsset] = []
        with engine.connect() as conn:
            inspector = inspect(conn)
            for schema in inspector.get_schema_names():
                if schema in _SYSTEM_SCHEMAS:
                    continue
                for table in inspector.get_table_names(schema=schema):
                    asset = self._discover_table(conn, inspector, schema, table)
                    if asset:
                        assets.append(asset)
        return assets

    def _discover_table(self, conn, inspector, schema: str, table: str) -> DiscoveredAsset | None:
        columns = inspector.get_columns(table, schema=schema)
        if not columns:
            return None
        qualified = f'"{schema}"."{table}"'
        try:
            row_count = conn.execute(text(f"SELECT count(*) FROM {qualified}")).scalar_one()
        except Exception:  # noqa: BLE001
            row_count = None

        fields: list[DiscoveredField] = []
        for col in columns:
            col_name = col["name"]
            data_type = str(col.get("type"))
            samples = self._sample_column(conn, qualified, col_name)
            fields.append(
                DiscoveredField(name=col_name, data_type=data_type, samples=samples)
            )

        return DiscoveredAsset(
            name=f"{schema}.{table}",
            display_name=table,
            asset_type=AssetType.TABLE.value,
            system_name=schema,
            environment="source",
            row_count=int(row_count) if row_count is not None else None,
            fields=fields,
        )

    def _sample_column(self, conn, qualified: str, column: str) -> list[str]:
        """Sample a bounded number of non-null values. Values stay in-memory only."""
        safe_col = '"' + column.replace('"', '""') + '"'
        try:
            rows = conn.execute(
                text(
                    f"SELECT {safe_col} FROM {qualified} "
                    f"WHERE {safe_col} IS NOT NULL LIMIT :lim"
                ),
                {"lim": self.max_sample_rows},
            ).fetchall()
            return [str(r[0]) for r in rows]
        except Exception:  # noqa: BLE001
            return []
