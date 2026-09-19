"""Unit tests for the static codebase scanner connector.

Covers the per-language data-model extractors (SQL DDL, Python ORM/dataclass,
Prisma, TypeScript), the zip discovery walk, safety skips, and the end-to-end
handoff into the existing PII classifier (code-derived fields still classify as
personal data by name signal even with no sample values).
"""

from __future__ import annotations

import io
import zipfile

from app.core.enums import AssetType, Classification
from app.scanners.classifier import classify_field
from app.scanners.codebase_connector import CodebaseConnector, extract_models


def _zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_extract_sql_ddl_columns_and_skips_constraints():
    sql = """
    CREATE TABLE IF NOT EXISTS public.customers (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) NOT NULL,
        first_name TEXT,
        phone VARCHAR(20),
        PRIMARY KEY (id),
        CONSTRAINT uq_email UNIQUE (email)
    );
    """
    models = extract_models(sql, "sql")
    assert len(models) == 1
    model = models[0]
    assert model.name == "customers"
    names = [f[0] for f in model.fields]
    assert names == ["id", "email", "first_name", "phone"]
    # constraint lines were not treated as columns
    assert "PRIMARY" not in names and "CONSTRAINT" not in names


def test_extract_python_sqlalchemy_and_tablename():
    py = """
class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    email = Column(String(255))
    objects = models.Manager()

    def helper(self):
        return self.email
"""
    models = extract_models(py, "python")
    assert len(models) == 1
    assert models[0].name == "customers"  # __tablename__ wins
    names = [f[0] for f in models[0].fields]
    assert "email" in names and "id" in names
    # manager assignment and method are not fields
    assert "objects" not in names and "helper" not in names


def test_extract_python_django_model_fields():
    py = """
class Profile(models.Model):
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
"""
    models = extract_models(py, "python")
    assert len(models) == 1
    assert models[0].name == "Profile"
    fields = dict(models[0].fields)
    assert fields["email"] == "EmailField"
    assert fields["full_name"] == "CharField"


def test_extract_python_dataclass_is_detected():
    py = """
@dataclass
class Applicant:
    aadhaar: str
    age: int
"""
    models = extract_models(py, "python")
    assert len(models) == 1
    assert models[0].name == "Applicant"
    assert [f[0] for f in models[0].fields] == ["aadhaar", "age"]


def test_plain_python_class_without_model_base_is_ignored():
    py = """
class Helper:
    something = compute()
    def run(self):
        pass
"""
    assert extract_models(py, "python") == []


def test_extract_prisma_model():
    schema = """
model User {
  id    Int     @id @default(autoincrement())
  email String  @unique
  phone String?
  @@index([email])
}
"""
    models = extract_models(schema, "prisma")
    assert len(models) == 1
    assert models[0].name == "User"
    fields = dict(models[0].fields)
    assert fields["email"] == "String"
    assert "id" in fields and "phone" in fields
    # directive line skipped
    assert all(not n.startswith("@") for n in fields)


def test_extract_typescript_interface_and_type():
    ts = """
export interface User {
  id: number;
  email: string;
  address?: string;
  greet(): void;
}

type Account = {
  balance: number;
  ownerName: string;
};
"""
    models = extract_models(ts, "typescript")
    by_name = {m.name: m for m in models}
    assert set(by_name) == {"User", "Account"}
    user_fields = [f[0] for f in by_name["User"].fields]
    assert "email" in user_fields and "address" in user_fields
    # method signature excluded
    assert "greet" not in user_fields


def test_discover_over_zip_produces_assets_with_fields():
    content = _zip(
        {
            "db/schema.sql": "CREATE TABLE orders (id INT, payment_reference VARCHAR(20));",
            "app/models.py": (
                "class Customer(Base):\n"
                "    email = Column(String)\n"
                "    first_name = Column(String)\n"
            ),
            "node_modules/pkg/index.ts": "interface Leaked { secret: string; }",
            "README.md": "# not scanned",
        }
    )
    connector = CodebaseConnector(content, "repo.zip")
    ok, _ = connector.test_connection()
    assert ok is True

    assets = connector.discover()
    names = {a.display_name for a in assets}
    assert "orders" in names
    assert "Customer" in names
    # node_modules is skipped
    assert "Leaked" not in names

    datasets = [a for a in assets if a.asset_type == AssetType.DATASET.value]
    for a in datasets:
        assert a.environment == "codebase"
        assert a.fields  # every emitted dataset has at least one field


def test_code_derived_email_field_classifies_as_personal_data():
    # No sample values (pattern_signal = 0); name signal alone must still flag it.
    from app.scanners.classifier import FieldSample

    result = classify_field(FieldSample(name="email", data_type="String", values=[]))
    assert result.classification == Classification.PERSONAL_DATA.value


def test_invalid_zip_reports_cleanly():
    connector = CodebaseConnector(b"not a zip", "bad.zip")
    ok, message = connector.test_connection()
    assert ok is False
    assert "zip" in message.lower()


# --- Third-party SDK / integration detection -----------------------------------

def test_detects_vendors_from_python_imports():
    content = _zip(
        {
            "app/pay.py": "import stripe\nfrom mixpanel import Mixpanel\n",
            "app/store.py": "import boto3\n",
            "app/util.py": "import os\nimport requests\n",  # not vendors
        }
    )
    integrations = CodebaseConnector(content, "app.zip").discover_integrations()
    names = {i.vendor_name for i in integrations}
    assert {"Stripe", "Mixpanel", "Amazon Web Services"} <= names
    assert "requests" not in names and "os" not in names


def test_detects_vendors_from_manifests():
    content = _zip(
        {
            "requirements.txt": "stripe==7.1.0\nsendgrid>=6\n# comment\nrequests==2.31\n",
            "package.json": (
                '{"dependencies": {"@sentry/node": "^7", "twilio": "^4"},'
                ' "devDependencies": {"typescript": "^5"}}'
            ),
        }
    )
    integrations = {i.vendor_name: i for i in CodebaseConnector(content, "x.zip").discover_integrations()}
    assert "Stripe" in integrations
    assert "SendGrid" in integrations
    assert "Sentry" in integrations
    assert "Twilio" in integrations


def test_flow_type_and_country_are_assigned():
    content = _zip({"a.py": "import mixpanel\nimport razorpay\n"})
    by_name = {i.vendor_name: i for i in CodebaseConnector(content, "x.zip").discover_integrations()}
    assert by_name["Mixpanel"].flow_type == "ANALYTICS"
    assert by_name["Mixpanel"].country == "United States"
    # Razorpay is a domestic (India) processor -> not cross-border downstream.
    assert by_name["Razorpay"].country == "India"


def test_discover_emits_application_node():
    content = _zip({"models.py": "class C(Base):\n    email = Column(String)\n"})
    assets = CodebaseConnector(content, "myapp.zip").discover()
    apps = [a for a in assets if a.asset_type == AssetType.APPLICATION.value]
    assert len(apps) == 1
    assert apps[0].display_name == "myapp"  # derived from archive name


# --- End-to-end scan: assets + vendors + flows in the graph --------------------

def test_codebase_scan_builds_graph_flows_and_vendors():
    import base64
    import uuid as _uuid

    from sqlalchemy import select

    from app.core.database import SessionLocal, utcnow
    from app.core.enums import ConnectorType
    from app.models.findings import Scan
    from app.models.identity import Organization
    from app.models.inventory import Connector, DataAsset, DataFlow, Vendor
    from app.security.encryption import encrypt_json
    from app.services.scan_service import run_scan

    zip_bytes = _zip(
        {
            "app/models.py": (
                "class Customer(Base):\n"
                "    email = Column(String)\n"
                "    phone = Column(String)\n"
            ),
            "app/pay.py": "import stripe\n",
            "requirements.txt": "boto3==1.34\nmixpanel==4.10\n",
        }
    )

    db = SessionLocal()
    try:
        org = Organization(name="CodeCorp", slug=f"codecorp-{_uuid.uuid4().hex[:8]}")
        db.add(org)
        db.flush()
        cfg = {
            "filename": "codecorp.zip",
            "content_b64": base64.b64encode(zip_bytes).decode("ascii"),
        }
        connector = Connector(
            organization_id=org.id,
            name="codecorp.zip",
            type=ConnectorType.CODEBASE.value,
            status="CONFIGURED",
            configuration_encrypted=encrypt_json(cfg),
        )
        db.add(connector)
        db.flush()
        scan = Scan(
            organization_id=org.id,
            connector_id=connector.id,
            status="QUEUED",
            stage="Queued",
            progress=0,
            created_at=utcnow(),
        )
        db.add(scan)
        db.flush()
        scan_id = scan.id
        db.commit()

        result = run_scan(db, scan_id)
        assert result.status == "COMPLETED", result.error_message

        vendors = {v.name for v in db.scalars(select(Vendor).where(Vendor.organization_id == org.id))}
        assert {"Stripe", "Amazon Web Services", "Mixpanel"} <= vendors

        app_asset = db.scalar(
            select(DataAsset).where(
                DataAsset.organization_id == org.id,
                DataAsset.asset_type == AssetType.APPLICATION.value,
            )
        )
        assert app_asset is not None

        flows = list(db.scalars(select(DataFlow).where(DataFlow.organization_id == org.id)))
        vendor_flows = [f for f in flows if f.vendor_id is not None]
        internal_flows = [f for f in flows if f.vendor_id is None]

        assert vendor_flows, "expected application -> vendor flows"
        assert all(f.discovered for f in vendor_flows)
        assert any(f.cross_border for f in vendor_flows)  # US vendors are cross-border
        assert all(f.source_asset_id == app_asset.id for f in vendor_flows)
        # personal dataset (Customer with email/phone) flows into the application
        assert any(f.contains_personal_data for f in internal_flows)
    finally:
        db.close()
