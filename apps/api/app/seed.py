"""Idempotent database seed for ComplyGraph.

Seeds:
  - The DPDP Act 2023 / DPDP Rules 2025 control library (regulation, obligations,
    controls) with real source references and effective dates. Controls whose
    effective date is after the assessment date are surfaced as UPCOMING, never
    as present failures.
  - The fictional AsterLane Technologies demo organization, its users/roles, a
    synthetic data source (DEMO connector) and CSV export, a cross-border vendor
    flow, processing activities, and a realistic mix of fresh/stale/missing
    evidence so the dashboard shows meaningful findings on first launch.

Run:  python -m app.seed
Safe to run repeatedly: existing rows are reused, not duplicated.

All demo data is synthetic. Demo credentials are for development only.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine, utcnow
from app.core.enums import (
    CitationStatus,
    ConnectorStatus,
    ConnectorType,
    DSRStatus,
    DSRType,
    EvidenceRelation,
    EvidenceType,
    FlowType,
    LegalStatus,
    Role,
)
from app.models.ai_systems import AISystem
from app.models.evidence import ControlEvidence, Evidence
from app.models.identity import Membership, Organization, User
from app.models.consent import ConsentNotice, ConsentPurpose
from app.models.inventory import Connector, DataAsset, DataFlow, ProcessingActivity, Vendor
from app.models.operations import BreachIncident, DataSubjectRequest
from app.models.regulatory import Control, Obligation, Regulation
from app.security.encryption import encrypt_json
from app.security.passwords import hash_password

# Fixed assessment date so the demo is deterministic and the effective-date
# engine produces a stable "upcoming vs active" split.
ASSESSMENT_DATE = datetime(2026, 9, 19, tzinfo=timezone.utc)
DEMO_PASSWORD = "DemoPass123!"  # development / demo only

DPDP_ACT_EFFECTIVE = datetime(2023, 8, 11, tzinfo=timezone.utc)
DPDP_RULES_EFFECTIVE = datetime(2025, 1, 1, tzinfo=timezone.utc)
# A rule that is not yet in force at the assessment date -> shown as UPCOMING.
FUTURE_RULE_EFFECTIVE = datetime(2027, 5, 13, tzinfo=timezone.utc)
DPDP_ACT_SOURCE_URL = (
    "https://www.meity.gov.in/writereaddata/files/"
    "Digital%20Personal%20Data%20Protection%20Act%202023.pdf"
)


# --- Control library ------------------------------------------------------------
# (code, title, description, category, evaluator_key, severity_default,
#  legal_reference, source_section, effective_from)
_CONTROLS: list[tuple] = [
    (
        "DPDP-NOTICE-001",
        "Notice / purpose transparency",
        "Provide a clear notice describing the personal data processed and the purposes.",
        "TRANSPARENCY",
        "notice",
        "HIGH",
        "DPDP Act 2023, s.5",
        "Section 5 (Notice)",
        DPDP_ACT_EFFECTIVE,
    ),
    (
        "DPDP-CONSENT-001",
        "Consent capture and purpose linkage",
        "Obtain and record consent that is linked to specific, declared purposes.",
        "CONSENT",
        "consent",
        "HIGH",
        "DPDP Act 2023, s.6",
        "Section 6 (Consent)",
        DPDP_ACT_EFFECTIVE,
    ),
    (
        "DPDP-CONSENT-002",
        "Consent withdrawal workflow",
        "Provide an easy mechanism for a Data Principal to withdraw consent.",
        "CONSENT",
        "consent_withdrawal",
        "MEDIUM",
        "DPDP Act 2023, s.6(4)-(6)",
        "Section 6 (Consent withdrawal)",
        DPDP_ACT_EFFECTIVE,
    ),
    (
        "DPDP-RIGHTS-001",
        "Data Principal rights request mechanism",
        "Operate a mechanism to receive and act on access, correction and erasure requests.",
        "RIGHTS",
        "rights",
        "HIGH",
        "DPDP Act 2023, ss.11-14",
        "Sections 11-14 (Rights of Data Principals)",
        DPDP_ACT_EFFECTIVE,
    ),
    (
        "DPDP-SECURITY-001",
        "Encryption / obfuscation / tokenisation safeguards",
        "Apply encryption, obfuscation or tokenisation to protect personal data.",
        "SECURITY",
        "security",
        "HIGH",
        "DPDP Act 2023, s.8(5); DPDP Rules 2025",
        "Section 8(5) (Reasonable security safeguards)",
        DPDP_RULES_EFFECTIVE,
    ),
    (
        "DPDP-SECURITY-002",
        "Access control",
        "Restrict access to personal data to authorised persons on a need-to-know basis.",
        "SECURITY",
        "security",
        "HIGH",
        "DPDP Act 2023, s.8(5); DPDP Rules 2025",
        "Section 8(5) (Reasonable security safeguards)",
        DPDP_RULES_EFFECTIVE,
    ),
    (
        "DPDP-SECURITY-003",
        "Logging / monitoring / review",
        "Maintain logs and monitor access to detect and investigate unauthorised processing.",
        "SECURITY",
        "security",
        "MEDIUM",
        "DPDP Act 2023, s.8(5); DPDP Rules 2025",
        "Section 8(5) (Reasonable security safeguards)",
        DPDP_RULES_EFFECTIVE,
    ),
    (
        "DPDP-SECURITY-004",
        "Backup / availability / recovery",
        "Maintain backups to ensure continued availability and recovery of personal data.",
        "SECURITY",
        "security",
        "MEDIUM",
        "DPDP Act 2023, s.8(5); DPDP Rules 2025",
        "Section 8(5) (Reasonable security safeguards)",
        DPDP_RULES_EFFECTIVE,
    ),
    (
        "DPDP-SECURITY-005",
        "Security obligations in processor contracts",
        "Ensure processors are bound by contract to implement reasonable security safeguards.",
        "SECURITY",
        "security",
        "MEDIUM",
        "DPDP Act 2023, s.8(2)",
        "Section 8(2) (Processing through a Data Processor)",
        DPDP_ACT_EFFECTIVE,
    ),
    (
        "DPDP-BREACH-001",
        "Personal data breach detection and response",
        "Detect, contain and respond to personal data breaches.",
        "BREACH",
        "breach",
        "HIGH",
        "DPDP Act 2023, s.8(6)",
        "Section 8(6) (Breach intimation)",
        DPDP_ACT_EFFECTIVE,
    ),
    (
        "DPDP-BREACH-002",
        "Affected Data Principal notification readiness",
        "Be able to notify the Board and affected Data Principals of a breach.",
        "BREACH",
        "breach",
        "HIGH",
        "DPDP Act 2023, s.8(6); DPDP Rules 2025",
        "Section 8(6) (Breach notification)",
        DPDP_RULES_EFFECTIVE,
    ),
    (
        "DPDP-RETENTION-001",
        "Purpose-based retention",
        "Retain personal data only as long as necessary for the declared purpose.",
        "RETENTION",
        "retention",
        "HIGH",
        "DPDP Act 2023, s.8(7)",
        "Section 8(7) (Erasure on purpose completion)",
        DPDP_ACT_EFFECTIVE,
    ),
    (
        "DPDP-RETENTION-002",
        "Deletion / erasure execution",
        "Execute deletion/erasure when retention periods lapse or consent is withdrawn.",
        "RETENTION",
        "retention",
        "HIGH",
        "DPDP Act 2023, s.8(7); s.12",
        "Section 8(7) (Erasure)",
        DPDP_ACT_EFFECTIVE,
    ),
    (
        "DPDP-CHILDREN-001",
        "Child-data consent / age verification workflow",
        "Obtain verifiable parental consent before processing a child's personal data.",
        "CHILDREN",
        "children",
        "HIGH",
        "DPDP Act 2023, s.9",
        "Section 9 (Processing of children's data)",
        DPDP_ACT_EFFECTIVE,
    ),
    (
        "DPDP-SDF-001",
        "Data Protection Impact Assessment",
        "Significant Data Fiduciaries must conduct periodic Data Protection Impact Assessments.",
        "GOVERNANCE",
        "sdf",
        "MEDIUM",
        "DPDP Act 2023, s.10(2)",
        "Section 10 (Significant Data Fiduciary)",
        DPDP_ACT_EFFECTIVE,
    ),
    (
        "DPDP-SDF-002",
        "Periodic audit",
        "Significant Data Fiduciaries must undergo periodic independent data audits.",
        "GOVERNANCE",
        "sdf",
        "MEDIUM",
        "DPDP Act 2023, s.10(2)",
        "Section 10 (Significant Data Fiduciary)",
        DPDP_ACT_EFFECTIVE,
    ),
    (
        "DPDP-VENDOR-001",
        "Processor/vendor governance",
        "Engage Data Processors only under a valid contract and govern their processing.",
        "VENDOR",
        "vendor",
        "HIGH",
        "DPDP Act 2023, s.8(2)",
        "Section 8(2) (Processing through a Data Processor)",
        DPDP_ACT_EFFECTIVE,
    ),
    (
        "DPDP-CROSSBORDER-001",
        "Cross-border data-flow governance",
        "Govern transfers of personal data outside India per applicable restrictions.",
        "CROSSBORDER",
        "crossborder",
        "MEDIUM",
        "DPDP Act 2023, s.16",
        "Section 16 (Processing outside India)",
        DPDP_ACT_EFFECTIVE,
    ),
    (
        "DPDP-GOVERNANCE-001",
        "Privacy contact / responsible person information",
        "Publish contact information of the Data Protection Officer or responsible person.",
        "GOVERNANCE",
        "governance",
        "MEDIUM",
        "DPDP Act 2023, s.8(9)",
        "Section 8(9) (Contact information)",
        DPDP_ACT_EFFECTIVE,
    ),
    (
        "DPDP-RULE-SECURITY-001",
        "Enhanced security safeguards (DPDP Rules)",
        "Enhanced technical security safeguards introduced by the DPDP Rules, effective later.",
        "SECURITY",
        "security",
        "MEDIUM",
        "DPDP Rules 2025 (enhanced safeguards)",
        "DPDP Rules 2025",
        FUTURE_RULE_EFFECTIVE,
    ),
]


def seed_framework(db: Session) -> Regulation:
    regulation = db.scalar(select(Regulation).where(Regulation.name == "Digital Personal Data Protection Act, 2023"))
    if regulation is None:
        regulation = Regulation(
            name="Digital Personal Data Protection Act, 2023",
            jurisdiction="India",
            version="2023 + DPDP Rules 2025",
            source_document="Digital Personal Data Protection Act, 2023 (No. 22 of 2023)",
            source_url=DPDP_ACT_SOURCE_URL,
            source_date="2023-08-11",
            pack="india-ai-compliance",
            pack_version="0.1",
            legal_status=LegalStatus.BINDING_LAW.value,
            effective_from=DPDP_ACT_EFFECTIVE,
            status="IN_FORCE",
            enabled=True,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(regulation)
        db.flush()

    # One obligation per control category grouping, keyed by control code prefix.
    obligation_by_code: dict[str, Obligation] = {}
    for (code, title, description, category, evaluator, severity, legal_ref, section, eff) in _CONTROLS:
        control = db.scalar(select(Control).where(Control.code == code))
        if control is not None:
            continue
        # Reuse an obligation per legal section.
        obligation = obligation_by_code.get(section)
        if obligation is None:
            obligation = db.scalar(
                select(Obligation).where(
                    Obligation.regulation_id == regulation.id,
                    Obligation.source_section == section,
                )
            )
        if obligation is None:
            # DPDP Rules 2025 provisions carry BINDING_RULE weight; the DPDP Act
            # itself is BINDING_LAW. Both are cited to precise sections -> VERIFIED.
            is_rule = "Rules" in (legal_ref or "")
            obligation = Obligation(
                regulation_id=regulation.id,
                code=f"OBL-{code}",
                title=section,
                description=description,
                legal_reference=legal_ref,
                source_section=section,
                source_url=DPDP_ACT_SOURCE_URL,
                legal_status=(
                    LegalStatus.BINDING_RULE.value if is_rule else LegalStatus.BINDING_LAW.value
                ),
                citation_status=CitationStatus.VERIFIED.value,
                effective_from=eff,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(obligation)
            db.flush()
        obligation_by_code[section] = obligation

        db.add(
            Control(
                obligation_id=obligation.id,
                code=code,
                title=title,
                description=description,
                category=category,
                assessment_method="deterministic",
                evaluator_key=evaluator,
                effective_from=eff,
                severity_default=severity,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
    db.flush()
    return regulation


# --- Organization + users -------------------------------------------------------

_USERS = [
    ("admin@asterlane.demo", "Aditi Rao", Role.ADMIN),
    ("privacy@asterlane.demo", "Vikram Nair", Role.PRIVACY_OFFICER),
    ("security@asterlane.demo", "Meera Iyer", Role.SECURITY_ANALYST),
    ("engineer@asterlane.demo", "Sanjay Bose", Role.ENGINEER),
    ("auditor@asterlane.demo", "Farah Khan", Role.AUDITOR),
    ("viewer@asterlane.demo", "Dev Kapoor", Role.VIEWER),
]


def seed_org(db: Session) -> Organization:
    org = db.scalar(select(Organization).where(Organization.slug == "asterlane"))
    if org is None:
        org = Organization(
            name="AsterLane Technologies Pvt. Ltd.",
            slug="asterlane",
            industry="SaaS / e-commerce infrastructure",
            country="India",
            plan="GROWTH",
            assessment_date=ASSESSMENT_DATE,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(org)
        db.flush()
    else:
        org.assessment_date = ASSESSMENT_DATE

    password_hash = hash_password(DEMO_PASSWORD)
    for email, full_name, role in _USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                full_name=full_name,
                password_hash=password_hash,
                is_active=True,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(user)
            db.flush()
        membership = db.scalar(
            select(Membership).where(
                Membership.user_id == user.id, Membership.organization_id == org.id
            )
        )
        if membership is None:
            db.add(
                Membership(
                    organization_id=org.id,
                    user_id=user.id,
                    role=role.value,
                    created_at=utcnow(),
                )
            )
    db.flush()
    return org


# --- Connectors + scan-driven inventory -----------------------------------------

_MARKETING_CSV = (
    "customer_id,email,phone,campaign,created_at\n"
    "1,aarav@example.com,+919876543210,spring_sale,2024-03-01\n"
    "2,diya@example.com,+919812345678,spring_sale,2024-03-02\n"
    "3,kabir@example.com,+919800000000,winter_sale,2024-03-03\n"
)


def seed_connectors_and_scan(db: Session, org: Organization) -> None:
    from app.services.scan_service import run_scan
    from app.models.findings import Scan

    demo = db.scalar(
        select(Connector).where(
            Connector.organization_id == org.id, Connector.type == ConnectorType.DEMO.value
        )
    )
    if demo is None:
        demo = Connector(
            organization_id=org.id,
            name="AsterLane Customer Platform (demo)",
            type=ConnectorType.DEMO.value,
            status=ConnectorStatus.CONNECTED.value,
            configuration_encrypted=encrypt_json({}),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(demo)
        db.flush()

    csv_conn = db.scalar(
        select(Connector).where(
            Connector.organization_id == org.id, Connector.type == ConnectorType.CSV.value
        )
    )
    if csv_conn is None:
        csv_conn = Connector(
            organization_id=org.id,
            name="marketing_export.csv",
            type=ConnectorType.CSV.value,
            status=ConnectorStatus.CONFIGURED.value,
            configuration_encrypted=encrypt_json(
                {
                    "content_b64": base64.b64encode(_MARKETING_CSV.encode("utf-8")).decode("utf-8"),
                    "filename": "marketing_export.csv",
                }
            ),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(csv_conn)
        db.flush()

    # Run scans (idempotent: assets/fields keyed by fingerprint).
    for connector in (demo, csv_conn):
        scan = Scan(
            organization_id=org.id,
            connector_id=connector.id,
            status="QUEUED",
            progress=0,
            created_at=utcnow(),
        )
        db.add(scan)
        db.flush()
        db.commit()
        run_scan(db, scan.id)


# --- Vendor, flows, processing activities ---------------------------------------


def seed_flows_and_activities(db: Session, org: Organization) -> None:
    vendor = db.scalar(
        select(Vendor).where(Vendor.organization_id == org.id, Vendor.name == "PulseMetrics Analytics")
    )
    if vendor is None:
        vendor = Vendor(
            organization_id=org.id,
            name="PulseMetrics Analytics",
            description="Third-party product analytics provider.",
            service_type="Product analytics",
            country="Singapore",
            data_processing="Receives customer identifiers and device data for analytics.",
            contract_status="MISSING",  # drives the vendor-governance finding
            risk_level="HIGH",
            owner="privacy@asterlane.demo",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(vendor)
        db.flush()

    customers = db.scalar(
        select(DataAsset).where(
            DataAsset.organization_id == org.id, DataAsset.name == "public.customers"
        )
    )
    marketing_csv_asset = db.scalar(
        select(DataAsset).where(
            DataAsset.organization_id == org.id, DataAsset.name.ilike("%marketing_export%")
        )
    )

    # Cross-border third-party flow: Customer DB -> PulseMetrics (Singapore).
    existing_flow = db.scalar(
        select(DataFlow).where(
            DataFlow.organization_id == org.id, DataFlow.vendor_id == vendor.id
        )
    )
    if existing_flow is None and customers is not None:
        db.add(
            DataFlow(
                organization_id=org.id,
                source_asset_id=customers.id,
                destination_asset_id=marketing_csv_asset.id if marketing_csv_asset else None,
                flow_type=FlowType.THIRD_PARTY.value,
                purpose=None,  # incomplete purpose mapping -> finding
                contains_personal_data=True,
                contains_sensitive_category=False,
                cross_border=True,
                vendor_id=vendor.id,
                discovered=False,
                confidence=1.0,
                status="ACTIVE",
                categories="email, customer_id, device_id",
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )

    activity = db.scalar(
        select(ProcessingActivity).where(
            ProcessingActivity.organization_id == org.id,
            ProcessingActivity.name == "Customer account management",
        )
    )
    if activity is None:
        db.add(
            ProcessingActivity(
                organization_id=org.id,
                name="Customer account management",
                purpose="Provide and support customer accounts and orders.",
                description="Core processing for the AsterLane platform.",
                lawful_basis="Consent",
                owner="privacy@asterlane.demo",
                status="ACTIVE",
                retention_period_days=730,
                has_notice=True,
                has_consent=True,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
    # A marketing activity WITHOUT documented retention (drives a retention gap).
    marketing_activity = db.scalar(
        select(ProcessingActivity).where(
            ProcessingActivity.organization_id == org.id,
            ProcessingActivity.name == "Marketing analytics export",
        )
    )
    if marketing_activity is None:
        db.add(
            ProcessingActivity(
                organization_id=org.id,
                name="Marketing analytics export",
                purpose="Share campaign engagement data with analytics vendor.",
                description="Exports customer marketing data. Retention not defined.",
                lawful_basis="Consent",
                owner="privacy@asterlane.demo",
                status="ACTIVE",
                retention_period_days=None,
                has_notice=False,
                has_consent=False,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
    db.flush()


# --- Evidence + operational workflows -------------------------------------------


def _link_evidence(db: Session, org: Organization, control_code: str, evidence: Evidence) -> None:
    control = db.scalar(select(Control).where(Control.code == control_code))
    if control is None:
        return
    exists = db.scalar(
        select(ControlEvidence).where(
            ControlEvidence.control_id == control.id, ControlEvidence.evidence_id == evidence.id
        )
    )
    if exists is None:
        db.add(
            ControlEvidence(
                control_id=control.id,
                evidence_id=evidence.id,
                relation_type=EvidenceRelation.SUPPORTS.value,
                created_at=utcnow(),
            )
        )


def _evidence(
    db: Session,
    org: Organization,
    name: str,
    ev_type: EvidenceType,
    *,
    collected_days_ago: int,
    expires_in_days: int | None,
) -> Evidence:
    existing = db.scalar(
        select(Evidence).where(Evidence.organization_id == org.id, Evidence.name == name)
    )
    if existing is not None:
        return existing
    collected = utcnow() - timedelta(days=collected_days_ago)
    expires = utcnow() + timedelta(days=expires_in_days) if expires_in_days is not None else None
    ev = Evidence(
        organization_id=org.id,
        type=ev_type.value,
        name=name,
        description="Synthetic demo evidence.",
        source="seed",
        collected_at=collected,
        expires_at=expires,
        owner="security@asterlane.demo",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(ev)
    db.flush()
    return ev


def seed_evidence_and_ops(db: Session, org: Organization) -> None:
    # Fresh evidence -> these controls pass.
    enc = _evidence(db, org, "Encryption at rest configuration", EvidenceType.CONFIGURATION, collected_days_ago=10, expires_in_days=180)
    _link_evidence(db, org, "DPDP-SECURITY-001", enc)
    acl = _evidence(db, org, "IAM access-control policy", EvidenceType.POLICY, collected_days_ago=20, expires_in_days=180)
    _link_evidence(db, org, "DPDP-SECURITY-002", acl)
    backup = _evidence(db, org, "Backup & recovery runbook", EvidenceType.DOCUMENT, collected_days_ago=30, expires_in_days=180)
    _link_evidence(db, org, "DPDP-SECURITY-004", backup)
    notice = _evidence(db, org, "Published privacy notice", EvidenceType.DOCUMENT, collected_days_ago=15, expires_in_days=365)
    _link_evidence(db, org, "DPDP-NOTICE-001", notice)
    consent = _evidence(db, org, "Consent capture configuration", EvidenceType.CONFIGURATION, collected_days_ago=15, expires_in_days=365)
    _link_evidence(db, org, "DPDP-CONSENT-001", consent)
    withdrawal = _evidence(db, org, "Consent-withdrawal workflow screenshot", EvidenceType.SCREENSHOT, collected_days_ago=15, expires_in_days=365)
    _link_evidence(db, org, "DPDP-CONSENT-002", withdrawal)
    governance = _evidence(db, org, "Published DPO contact information", EvidenceType.DOCUMENT, collected_days_ago=15, expires_in_days=365)
    _link_evidence(db, org, "DPDP-GOVERNANCE-001", governance)

    # Expired evidence -> logging control needs review (Finding 4).
    logging_ev = _evidence(db, org, "Access-log monitoring report", EvidenceType.LOG, collected_days_ago=400, expires_in_days=-30)
    _link_evidence(db, org, "DPDP-SECURITY-003", logging_ev)

    # Near-expiry evidence -> drives an "expiring soon" reminder (feature #6).
    dpia = _evidence(db, org, "DPIA sign-off record", EvidenceType.DOCUMENT, collected_days_ago=160, expires_in_days=25)
    _link_evidence(db, org, "DPDP-GOVERNANCE-001", dpia)

    # DPDP-SECURITY-005 (processor-contract security) intentionally has NO evidence
    # -> "Vendor processing agreement evidence is missing" (Finding 5).

    # A Data Subject Request makes the rights workflow "configured" -> rights passes.
    dsr = db.scalar(select(DataSubjectRequest).where(DataSubjectRequest.organization_id == org.id))
    if dsr is None:
        db.add(
            DataSubjectRequest(
                organization_id=org.id,
                requester_identifier="principal-0001",
                request_type=DSRType.ACCESS.value,
                status=DSRStatus.IN_PROGRESS.value,
                received_at=utcnow() - timedelta(days=3),
                due_at=utcnow() + timedelta(days=27),
                verification_status="VERIFIED",
                notes="Synthetic demo access request.",
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )

    # A breach incident record makes the breach workflow "configured".
    breach = db.scalar(select(BreachIncident).where(BreachIncident.organization_id == org.id))
    if breach is None:
        db.add(
            BreachIncident(
                organization_id=org.id,
                title="Contained misconfiguration (synthetic)",
                description="A synthetic, already-contained demo incident.",
                severity="LOW",
                detected_at=utcnow() - timedelta(days=45),
                contained_at=utcnow() - timedelta(days=44),
                affected_records_estimate=0,
                status="CLOSED",
                board_notification_status="NOT_REQUIRED",
                principal_notification_status="NOT_REQUIRED",
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
    db.flush()


def seed_ai_systems(db: Session, org: Organization) -> None:
    """Seed a realistic AI-system inventory so the applicability engine has
    something to compile against on first launch.

    AsterLane runs a merchant-financing product, so it operates a BFSI credit
    decisioning copilot (a high-risk, production LLM with an externally hosted
    model, external observability and a foreign model vendor) alongside a purely
    internal documentation assistant. The contrast is deliberate: the BFSI system
    trips the RBI / MeitY controls, while the internal tool keeps the BFSI- and
    condition-scoped controls NOT_APPLICABLE — demonstrating applicability, not a
    blanket rule sweep.
    """
    from app.services import ai_system_service

    if db.scalar(select(AISystem).where(AISystem.organization_id == org.id)) is not None:
        return  # idempotent

    admin = db.scalar(select(User).where(User.email == "admin@asterlane.demo"))
    user_id = admin.id if admin else None

    # A dedicated foreign model vendor so the vendor / sub-processor control has a
    # concrete counterparty (distinct from the generic analytics vendor).
    model_vendor = db.scalar(
        select(Vendor).where(Vendor.organization_id == org.id, Vendor.name == "NovaModel AI")
    )
    if model_vendor is None:
        model_vendor = Vendor(
            organization_id=org.id,
            name="NovaModel AI",
            description="US-hosted foundation-model API used for credit narrative generation.",
            service_type="Hosted LLM inference",
            country="US",
            data_processing="Receives applicant features to generate credit rationale.",
            contract_status="MISSING",
            risk_level="HIGH",
            owner="ml-platform@asterlane.demo",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(model_vendor)
        db.flush()

    # 1) BFSI credit decisioning copilot — trips the India AI stack.
    ai_system_service.import_architecture(
        db,
        org.id,
        user_id,
        {
            "system": {
                "name": "Merchant Credit Scoring Copilot",
                "description": "Generates credit decisions and rationale for merchant financing.",
                "business_purpose": "Automated merchant credit underwriting.",
                "owner": "ml-platform@asterlane.demo",
                "system_type": "LLM",
                "sector": "bfsi",
                "lifecycle_stage": "PRODUCTION",
                "review_status": "NOT_REVIEWED",
                "processes_personal_data": True,
                "makes_automated_decisions": True,
                "high_risk": True,
                "regions": ["India"],
                "deployment_environment": "AWS ap-south-1 + external LLM API",
            },
            "components": [
                {
                    "key": "llm",
                    "name": "NovaModel Hosted LLM",
                    "type": "MODEL",
                    "external": True,
                    "region": "us",
                    "provider": "NovaModel AI",
                    "vendor": "NovaModel AI",
                    "description": "US-hosted model used to generate credit rationale.",
                },
                {
                    "key": "apm",
                    "name": "External APM / Log Pipeline",
                    "type": "SERVICE",
                    "external": True,
                    "region": "us",
                    "provider": "Datadog",
                    "description": "Application telemetry shipped to a US observability service.",
                },
                {
                    "key": "features",
                    "name": "Feature Store",
                    "type": "DATA_STORE",
                    "region": "India",
                    "description": "Applicant and transaction features (personal data).",
                },
                {
                    "key": "decision_api",
                    "name": "Decision API",
                    "type": "API",
                    "region": "India",
                    "description": "Internal service returning the underwriting decision.",
                },
            ],
            "flows": [
                {
                    "from": "features",
                    "to": "llm",
                    "relation": "SENDS_TO",
                    "purpose": "Generate credit rationale",
                    "contains_personal_data": True,
                    "cross_border": True,
                },
                {
                    "from": "llm",
                    "to": "decision_api",
                    "relation": "SENDS_TO",
                    "purpose": "Return decision + rationale",
                    "contains_personal_data": True,
                    "cross_border": True,
                },
            ],
        },
    )

    # 2) Internal documentation assistant — general, low-risk, India-only.
    ai_system_service.import_architecture(
        db,
        org.id,
        user_id,
        {
            "system": {
                "name": "Internal Docs Assistant",
                "description": "Answers employee questions over internal runbooks.",
                "business_purpose": "Internal knowledge search.",
                "owner": "platform@asterlane.demo",
                "system_type": "RAG",
                "sector": "general",
                "lifecycle_stage": "PRODUCTION",
                "review_status": "REVIEWED",
                "processes_personal_data": False,
                "makes_automated_decisions": False,
                "high_risk": False,
                "regions": ["India"],
                "deployment_environment": "Self-hosted in AWS ap-south-1",
            },
            "components": [
                {
                    "key": "embed",
                    "name": "Embedding Model",
                    "type": "MODEL",
                    "external": False,
                    "region": "India",
                },
                {
                    "key": "index",
                    "name": "Runbook Index",
                    "type": "DATA_STORE",
                    "region": "India",
                },
            ],
            "flows": [
                {
                    "from": "index",
                    "to": "embed",
                    "relation": "SENDS_TO",
                    "purpose": "Retrieve context",
                    "contains_personal_data": False,
                    "cross_border": False,
                },
            ],
        },
    )
    db.flush()


def seed_findings(db: Session, org: Organization) -> int:
    """Run the deterministic assessment + finding generation over the complete state.

    Findings and assessments generated during the initial discovery scans (which
    ran before evidence/flows/activities were seeded) are cleared first, so the
    final state reflects a single, consistent evaluation against all seeded
    evidence. This is safe because every finding here is machine-generated.
    """
    from app.services.scan_service import _generate_findings
    from app.models.findings import Finding, Scan
    from app.models.regulatory import ControlAssessment

    for finding in db.scalars(select(Finding).where(Finding.organization_id == org.id)):
        db.delete(finding)
    for assessment in db.scalars(
        select(ControlAssessment).where(ControlAssessment.organization_id == org.id)
    ):
        db.delete(assessment)
    db.flush()

    scan = Scan(
        organization_id=org.id,
        connector_id=None,
        status="COMPLETED",
        progress=100,
        created_at=utcnow(),
        completed_at=utcnow(),
    )
    db.add(scan)
    db.flush()
    count = _generate_findings(db, org, scan)
    db.commit()
    return count


def seed_integrations(db: Session, org: Organization) -> None:
    """Seed a demo outbound webhook endpoint (feature #10).

    Registered but pointed at a placeholder receiver so the Integrations settings
    page has something to display. Delivery is best-effort and gated by
    ``settings.webhooks_enabled``; no live event fires during seeding because this
    runs after all event-emitting seed steps.
    """
    from app.services import webhook_service

    endpoint, _secret = webhook_service.create_endpoint(
        db,
        org.id,
        name="Demo receiver (SIEM)",
        url="https://example.com/complygraph/webhook",
        events=[
            "finding.created",
            "risk.status_changed",
            "breach.created",
            "assessment.regressed",
        ],
    )
    db.flush()


def seed_consent(db: Session, org: Organization) -> None:
    """Seed a purpose catalogue, a published notice, and a few consent records."""
    from app.services import consent_service

    existing = db.scalar(
        select(ConsentPurpose).where(ConsentPurpose.organization_id == org.id)
    )
    if existing is not None:
        return

    # Link purposes to the seeded processing activities where names match.
    account_activity = db.scalar(
        select(ProcessingActivity).where(
            ProcessingActivity.organization_id == org.id,
            ProcessingActivity.name == "Customer account management",
        )
    )
    marketing_activity = db.scalar(
        select(ProcessingActivity).where(
            ProcessingActivity.organization_id == org.id,
            ProcessingActivity.name == "Marketing analytics export",
        )
    )

    purposes = [
        {
            "code": "account",
            "name": "Account management",
            "description": "Create and support your AsterLane account and orders.",
            "lawful_basis": "Contract",
            "requires_consent": False,  # necessary for the service -> shown, not withdrawable
            "display_order": 10,
            "processing_activity_id": account_activity.id if account_activity else None,
        },
        {
            "code": "marketing",
            "name": "Marketing communications",
            "description": "Send you product news, offers and campaign emails.",
            "lawful_basis": "Consent",
            "requires_consent": True,
            "default_expiry_days": 365,
            "display_order": 20,
            "processing_activity_id": marketing_activity.id if marketing_activity else None,
        },
        {
            "code": "analytics",
            "name": "Usage analytics",
            "description": "Analyse how you use the product to improve it.",
            "lawful_basis": "Consent",
            "requires_consent": True,
            "display_order": 30,
        },
        {
            "code": "health-personalisation",
            "name": "Health-based personalisation",
            "description": "Tailor recommendations using health-related information.",
            "lawful_basis": "Consent",
            "requires_consent": True,
            "is_sensitive": True,
            "display_order": 40,
        },
    ]
    created: dict[str, ConsentPurpose] = {}
    for spec in purposes:
        p = consent_service.create_purpose(db, org.id, spec)
        created[spec["code"]] = p

    # Publish an initial notice (version 1).
    consent_service.create_notice(
        db,
        org.id,
        {
            "title": "AsterLane Privacy Notice",
            "body": (
                "AsterLane processes your personal data to provide our services, and (with your "
                "consent) for marketing, analytics and personalisation. You can withdraw consent at "
                "any time from this Privacy Center. For access, correction or erasure of your data, "
                "submit a request below. This notice is provided for transparency and does not "
                "constitute a determination of your legal rights."
            ),
        },
        publish=True,
    )

    # A couple of demo consent records so the ledger is not empty.
    consent_service.record_consent(
        db, org.id, purpose_id=created["marketing"].id, principal="[email protected]", verified=True
    )
    consent_service.record_consent(
        db, org.id, purpose_id=created["analytics"].id, principal="[email protected]", verified=True
    )
    consent_service.withdraw_consent(
        db, org.id, purpose_id=created["marketing"].id, principal="[email protected]"
    )
    db.flush()


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_framework(db)
        db.commit()
        from app.seed_packs import seed_packs

        seed_packs(db)
        db.commit()
        org = seed_org(db)
        db.commit()
        seed_connectors_and_scan(db, org)
        db.commit()
        seed_flows_and_activities(db, org)
        db.commit()
        seed_ai_systems(db, org)
        db.commit()
        seed_evidence_and_ops(db, org)
        db.commit()
        seed_consent(db, org)
        db.commit()
        findings = seed_findings(db, org)
        db.commit()
        # Baseline assessment history so re-assessment has a prior state to diff,
        # then generate reminder notifications from the seeded data.
        from app.services.reassessment_service import run_reassessment
        from app.services.reminder_service import generate_for_org

        run_reassessment(db, org)
        db.commit()
        reminders = generate_for_org(db, org)
        db.commit()
        seed_integrations(db, org)
        db.commit()
        print(f"Seed complete. Organization: {org.name}")
        print(f"Assessment date: {org.assessment_date}")
        print(f"Findings generated: {findings}")
        print(f"Reminders generated: {reminders.get('total', 0)}")
        print("Demo login (development only): admin@asterlane.demo / DemoPass123!")
    finally:
        db.close()


if __name__ == "__main__":
    run()
