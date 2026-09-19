"""Unit tests for static code risk analysis and Go/Mongoose model extraction."""

from __future__ import annotations

from app.scanners.code_analysis import analyze_source
from app.scanners.codebase_connector import extract_models


# --- PII in logs ----------------------------------------------------------------

def test_detects_pii_in_python_log():
    code = "logger.info('user login ' + user.email)\n"
    risks = analyze_source(code)
    kinds = {r.kind for r in risks}
    assert "pii_in_logs" in kinds


def test_detects_pii_in_console_log():
    code = "console.log(`phone is ${customer.phone}`)\n"
    risks = analyze_source(code)
    assert any(r.kind == "pii_in_logs" for r in risks)


def test_clean_log_not_flagged():
    code = "logger.info('request completed in %d ms', elapsed)\n"
    risks = [r for r in analyze_source(code) if r.kind == "pii_in_logs"]
    assert risks == []


def test_snippet_redacts_string_literals():
    code = "logger.info('secret email is aarav@example.com for user')\n"
    risks = analyze_source(code)
    assert risks
    for r in risks:
        assert "aarav@example.com" not in r.snippet


# --- Taint: PII -> third-party SDK ----------------------------------------------

def test_detects_direct_pii_to_sdk():
    code = "stripe.Customer.create(email=customer.email)\n"
    risks = [r for r in analyze_source(code) if r.kind == "pii_to_third_party"]
    assert risks
    assert "stripe" in risks[0].detail.lower()


def test_detects_tainted_variable_to_sdk():
    code = "addr = user.address\nmixpanel.track(addr)\n"
    risks = [r for r in analyze_source(code) if r.kind == "pii_to_third_party"]
    assert risks


def test_non_pii_sdk_call_not_flagged():
    code = "stripe.Product.list(limit=10)\n"
    risks = [r for r in analyze_source(code) if r.kind == "pii_to_third_party"]
    assert risks == []


# --- Go struct extraction -------------------------------------------------------

def test_extract_go_struct_uses_json_tag():
    go = """
type Customer struct {
    ID        int    `json:"id"`
    Email     string `json:"email"`
    FullName  string `json:"full_name"`
    // a comment
}
"""
    models = extract_models(go, "go")
    assert len(models) == 1
    assert models[0].name == "Customer"
    names = [f[0] for f in models[0].fields]
    assert "email" in names  # json tag name used
    assert "full_name" in names


# --- Mongoose schema extraction -------------------------------------------------

def test_extract_mongoose_schema_fields():
    js = """
const userSchema = new mongoose.Schema({
  email: String,
  phone: { type: String, required: true },
  name: String,
});
"""
    models = extract_models(js, "javascript")
    assert len(models) == 1
    assert models[0].name == "User"  # "Schema" suffix stripped, capitalized
    names = [f[0] for f in models[0].fields]
    assert "email" in names and "phone" in names and "name" in names


# --- End-to-end: code risks become findings ------------------------------------

def test_code_risks_become_findings_on_scan():
    import base64
    import io
    import uuid
    import zipfile

    from sqlalchemy import select

    from app.core.database import SessionLocal, utcnow
    from app.core.enums import ConnectorType
    from app.models.findings import Finding, Scan
    from app.models.identity import Organization
    from app.models.inventory import Connector
    from app.security.encryption import encrypt_json
    from app.services.scan_service import run_scan

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("app/models.py", "class C(Base):\n    email = Column(String)\n")
        zf.writestr(
            "app/svc.py",
            "import stripe\n"
            "def pay(user):\n"
            "    logger.info('paying for ' + user.email)\n"
            "    stripe.Customer.create(email=user.email)\n",
        )
    zip_bytes = buf.getvalue()

    db = SessionLocal()
    try:
        org = Organization(name="RiskCorp", slug=f"risk-{uuid.uuid4().hex[:8]}")
        db.add(org)
        db.flush()
        cfg = {"filename": "riskcorp.zip", "content_b64": base64.b64encode(zip_bytes).decode()}
        connector = Connector(
            organization_id=org.id,
            name="riskcorp.zip",
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

        run_scan(db, scan_id)

        finding_types = {
            f.title
            for f in db.scalars(select(Finding).where(Finding.source == "code_scan"))
            if f.organization_id == org.id
        }
        assert any("logs" in t for t in finding_types)
        assert any("third-party" in t for t in finding_types)
    finally:
        db.close()
