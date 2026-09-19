"""Demo connector.

Produces the synthetic AsterLane customer-platform inventory entirely in-memory
so the full discovery → classification → control → findings loop can be
demonstrated locally with zero external services (no live PostgreSQL required).

All values are synthetic and safe. If a real PostgreSQL DSN is configured via
DEMO_DATABASE_URL, the PostgresConnector is used instead (see scan_service).
"""

from __future__ import annotations

from app.core.enums import AssetType
from app.scanners.base import BaseConnector, DiscoveredAsset, DiscoveredField

# Synthetic sample values (fictional). These stay in-memory; only masked
# examples derived from them are ever persisted.
_CUSTOMERS = DiscoveredAsset(
    name="public.customers",
    display_name="customers",
    asset_type=AssetType.TABLE.value,
    system_name="public",
    environment="source",
    row_count=48210,
    fields=[
        DiscoveredField("id", "integer", ["1", "2", "3"]),
        DiscoveredField("first_name", "varchar", ["Aarav", "Diya", "Kabir"]),
        DiscoveredField("last_name", "varchar", ["Sharma", "Patel", "Nair"]),
        DiscoveredField("email", "varchar", ["aarav@example.com", "diya@example.com"]),
        DiscoveredField("phone", "varchar", ["+919876543210", "+919812345678"]),
        DiscoveredField("address", "text", ["12 MG Road", "44 Residency Rd"]),
        DiscoveredField("city", "varchar", ["Bengaluru", "Mumbai"]),
        DiscoveredField("country", "varchar", ["India", "India"]),
        DiscoveredField("created_at", "timestamp", ["2024-01-04", "2024-02-11"]),
        DiscoveredField("marketing_opt_in", "boolean", ["true", "false"]),
    ],
)

_ORDERS = DiscoveredAsset(
    name="public.orders",
    display_name="orders",
    asset_type=AssetType.TABLE.value,
    system_name="public",
    environment="source",
    row_count=192880,
    fields=[
        DiscoveredField("id", "integer", ["1001", "1002"]),
        DiscoveredField("customer_id", "integer", ["1", "2"]),
        DiscoveredField("order_total", "numeric", ["1299.00", "499.50"]),
        DiscoveredField("payment_reference", "varchar", ["4111111111111111", "5500005555555559"]),
        DiscoveredField("created_at", "timestamp", ["2024-03-01", "2024-03-02"]),
    ],
)

_SUPPORT = DiscoveredAsset(
    name="public.support_tickets",
    display_name="support_tickets",
    asset_type=AssetType.TABLE.value,
    system_name="public",
    environment="source",
    row_count=15320,
    fields=[
        DiscoveredField("id", "integer", ["1", "2"]),
        DiscoveredField("customer_id", "integer", ["1", "2"]),
        DiscoveredField("subject", "varchar", ["Login issue", "Refund request"]),
        DiscoveredField("description", "text", ["Cannot access account", "Please refund order"]),
        DiscoveredField("created_at", "timestamp", ["2024-04-01", "2024-04-03"]),
    ],
)

_MARKETING = DiscoveredAsset(
    name="public.marketing_preferences",
    display_name="marketing_preferences",
    asset_type=AssetType.TABLE.value,
    system_name="public",
    environment="source",
    row_count=48210,
    fields=[
        DiscoveredField("customer_id", "integer", ["1", "2"]),
        DiscoveredField("email_marketing", "boolean", ["true", "false"]),
        DiscoveredField("sms_marketing", "boolean", ["false", "true"]),
        DiscoveredField("updated_at", "timestamp", ["2024-05-01", "2024-05-02"]),
    ],
)

_EMPLOYEES = DiscoveredAsset(
    name="public.employees",
    display_name="employees",
    asset_type=AssetType.TABLE.value,
    system_name="public",
    environment="source",
    row_count=412,
    fields=[
        DiscoveredField("id", "integer", ["1", "2"]),
        DiscoveredField("name", "varchar", ["Rohan Mehta", "Isha Gupta"]),
        DiscoveredField("email", "varchar", ["rohan@asterlane.demo", "isha@asterlane.demo"]),
        DiscoveredField("department", "varchar", ["Engineering", "Support"]),
        DiscoveredField("joined_at", "timestamp", ["2021-06-01", "2022-01-15"]),
    ],
)


class DemoConnector(BaseConnector):
    """Synthetic in-memory data source representing the AsterLane platform."""

    def test_connection(self) -> tuple[bool, str]:
        return True, "Demo connector ready (synthetic in-memory data)."

    def discover(self) -> list[DiscoveredAsset]:
        return [_CUSTOMERS, _ORDERS, _SUPPORT, _MARKETING, _EMPLOYEES]
