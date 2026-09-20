"""India AI-compliance regulatory packs (RBI, CERT-In, MeitY).

These packs extend the DPDP control library (see seed.py) so an AI system's
architecture can be mapped against the broader India regulatory stack.

HONESTY RULES (non-negotiable, per the AI Compliance Compiler spec):
  - Every obligation carries an explicit `legal_status`. DPDP, RBI, CERT-In and
    MeitY materials have different legal force and MUST NOT be flattened into a
    generic "law" label.
  - `citation_status` is VERIFIED only where the section/paragraph reference is
    quoted from the authoritative source text. Everything derived from framework
    or guidance material is UNVERIFIED and surfaces as "HUMAN REVIEW REQUIRED".
  - No invented section numbers. Where a precise citation is not available the
    reference is described generically and left UNVERIFIED.

Sources (authoritative, first-party):
  - RBI PSS storage-of-payment-data direction (DPSS.CO.OD.No.2785/06.08.005/2017-18)
  - RBI FREE-AI Committee Report (framework material)
  - CERT-In Directions under s.70B of the IT Act, 28.04.2022
  - MeitY India AI Governance Guidelines (guidance)

Controls reference evaluator keys implemented by the control engine. Unknown
keys fall back to a generic evidence check, so this pack is safe to seed before
the AI-specific evaluators land.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.enums import CitationStatus, LegalStatus, MappingRelation, RegulationStatus
from app.models.regulatory import Control, ControlMapping, Obligation, Regulation

PACK_NAME = "india-ai-compliance"
PACK_VERSION = "0.1"

# --- Effective dates ------------------------------------------------------------
RBI_PSS_EFFECTIVE = datetime(2018, 4, 6, tzinfo=timezone.utc)
RBI_FREEAI_EFFECTIVE = datetime(2025, 8, 1, tzinfo=timezone.utc)
CERTIN_EFFECTIVE = datetime(2022, 6, 28, tzinfo=timezone.utc)
MEITY_AI_EFFECTIVE = datetime(2025, 11, 1, tzinfo=timezone.utc)


# --- Pack definition ------------------------------------------------------------
# Each regulation: (key, name, legal_status, version, source_document, source_url,
#                   source_date, effective_from, status)
# Each control:    (code, title, description, category, evaluator_key, severity,
#                   obligation_title, legal_reference, source_section, source_url,
#                   legal_status, citation_status, effective_from, applies_to)


def _rbi_pack() -> dict:
    return {
        "regulation": dict(
            name="RBI — Data Localisation & AI Governance (India, BFSI)",
            legal_status=LegalStatus.REGULATORY_DIRECTION.value,
            version="PSS 2018 + FREE-AI 2025",
            source_document=(
                "RBI Storage of Payment System Data direction "
                "(DPSS.CO.OD.No.2785/06.08.005/2017-18); RBI FREE-AI Committee Report"
            ),
            source_url="https://www.rbi.org.in/",
            source_date="2018-04-06",
            effective_from=RBI_PSS_EFFECTIVE,
            status=RegulationStatus.IN_FORCE.value,
        ),
        "controls": [
            (
                "RBI-LOCALIZATION-001",
                "Payment system data storage in India",
                "Payment system data must be stored only in India. Where AI systems "
                "process payment/customer data, that processing must not persist data "
                "outside India.",
                "CROSSBORDER",
                "rbi_localization",
                "CRITICAL",
                "Storage of Payment System Data",
                "RBI DPSS.CO.OD.No.2785/06.08.005/2017-18",
                "Storage of Payment System Data (6 April 2018)",
                "https://www.rbi.org.in/",
                LegalStatus.REGULATORY_DIRECTION.value,
                CitationStatus.VERIFIED.value,
                RBI_PSS_EFFECTIVE,
                {"sectors": ["bfsi"], "ai_types": ["all"], "conditions": ["processes_personal_data"]},
            ),
            (
                "RBI-LOGGING-001",
                "AI logs/telemetry containing customer data kept in India",
                "Logs and telemetry from AI systems that contain customer data should "
                "not be exported to observability/monitoring services hosted outside "
                "India. Treated as a data-residency review for BFSI systems.",
                "SECURITY",
                "rbi_logging_telemetry",
                "HIGH",
                "Data residency for BFSI AI systems",
                "RBI data-localisation framework (payment/customer data)",
                "Storage of Payment System Data; FREE-AI Committee Report",
                "https://www.rbi.org.in/",
                LegalStatus.REGULATOR_EXPECTATION.value,
                CitationStatus.UNVERIFIED.value,
                RBI_PSS_EFFECTIVE,
                {"sectors": ["bfsi"], "ai_types": ["all"], "conditions": ["uses_external_observability"]},
            ),
            (
                "RBI-INFERENCE-001",
                "AI inference on India-based infrastructure (BFSI)",
                "For BFSI systems processing customer/payment data, model inference "
                "should occur on India-based infrastructure. Emerging expectation; "
                "review against the specific deployment.",
                "CROSSBORDER",
                "ai_inference_region",
                "HIGH",
                "AI inference locality (BFSI)",
                "RBI FREE-AI Committee Report (framework material)",
                "FREE-AI Committee Report",
                "https://www.rbi.org.in/",
                LegalStatus.FORMAL_FRAMEWORK.value,
                CitationStatus.UNVERIFIED.value,
                RBI_FREEAI_EFFECTIVE,
                {"sectors": ["bfsi"], "ai_types": ["llm", "generative", "agentic", "hybrid"], "conditions": ["has_external_inference"]},
            ),
            (
                "RBI-VENDOR-001",
                "Third-party AI vendor / sub-processor data residency",
                "Vendors (and their sub-processors) that process BFSI customer data "
                "must demonstrate India-only processing and audit rights. A vendor in "
                "India with a foreign sub-processor is still a review item.",
                "VENDOR",
                "vendor_subprocessor",
                "HIGH",
                "Outsourcing & vendor governance (BFSI)",
                "RBI outsourcing directions (bank retains responsibility for outputs)",
                "RBI outsourcing framework",
                "https://www.rbi.org.in/",
                LegalStatus.REGULATOR_EXPECTATION.value,
                CitationStatus.UNVERIFIED.value,
                RBI_FREEAI_EFFECTIVE,
                {"sectors": ["bfsi"], "ai_types": ["all"], "conditions": ["has_vendors"]},
            ),
        ],
    }


def _certin_pack() -> dict:
    return {
        "regulation": dict(
            name="CERT-In — Cyber Security Directions (s.70B, IT Act)",
            legal_status=LegalStatus.REGULATORY_DIRECTION.value,
            version="28.04.2022",
            source_document="CERT-In Directions under sub-section (6) of section 70B of the IT Act, 2000",
            source_url="https://www.cert-in.org.in/Directions70B.jsp",
            source_date="2022-04-28",
            effective_from=CERTIN_EFFECTIVE,
            status=RegulationStatus.IN_FORCE.value,
        ),
        "controls": [
            (
                "CERTIN-LOGS-001",
                "Security logs retained in India for 180 days",
                "Logs of ICT systems must be maintained securely for a rolling period "
                "of 180 days within Indian jurisdiction.",
                "SECURITY",
                "certin_logging_retention",
                "HIGH",
                "Log retention",
                "CERT-In Directions 28.04.2022, direction on log retention",
                "Direction (iv) — enabling and maintaining logs for 180 days",
                "https://cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf",
                LegalStatus.REGULATORY_DIRECTION.value,
                CitationStatus.VERIFIED.value,
                CERTIN_EFFECTIVE,
                {"sectors": ["all"], "ai_types": ["all"], "conditions": []},
            ),
            (
                "CERTIN-INCIDENT-001",
                "Cyber incident reporting to CERT-In within 6 hours",
                "Reportable cyber incidents must be reported to CERT-In within 6 hours "
                "of noticing them. A reporting pathway must exist.",
                "BREACH",
                "certin_incident",
                "HIGH",
                "Incident reporting",
                "CERT-In Directions 28.04.2022, direction on incident reporting",
                "Direction (ii) — report cyber incidents within 6 hours",
                "https://cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf",
                LegalStatus.REGULATORY_DIRECTION.value,
                CitationStatus.VERIFIED.value,
                CERTIN_EFFECTIVE,
                {"sectors": ["all"], "ai_types": ["all"], "conditions": []},
            ),
        ],
    }


def _meity_pack() -> dict:
    return {
        "regulation": dict(
            name="MeitY — India AI Governance Guidelines",
            legal_status=LegalStatus.GUIDANCE.value,
            version="2025",
            source_document="India AI Governance Guidelines (MeitY / IndiaAI)",
            source_url="https://indiaai.gov.in/",
            source_date="2025-11-01",
            effective_from=MEITY_AI_EFFECTIVE,
            status=RegulationStatus.IN_FORCE.value,
        ),
        "controls": [
            (
                "MEITY-INVENTORY-001",
                "AI system inventory",
                "Maintain a central inventory of AI/ML systems in production. Advisory "
                "guidance, not a binding obligation.",
                "GOVERNANCE",
                "ai_inventory",
                "MEDIUM",
                "Accountability",
                "MeitY India AI Governance Guidelines (guidance)",
                "AI governance guidance — accountability",
                "https://indiaai.gov.in/",
                LegalStatus.GUIDANCE.value,
                CitationStatus.UNVERIFIED.value,
                MEITY_AI_EFFECTIVE,
                {"sectors": ["all"], "ai_types": ["all"], "conditions": []},
            ),
            (
                "MEITY-BIAS-001",
                "Algorithmic fairness / bias review",
                "Conduct and document fairness testing across protected categories for "
                "high-impact AI. Advisory guidance.",
                "GOVERNANCE",
                "meity_bias",
                "MEDIUM",
                "Fairness & Equity",
                "MeitY India AI Governance Guidelines (guidance)",
                "AI governance guidance — fairness & equity",
                "https://indiaai.gov.in/",
                LegalStatus.GUIDANCE.value,
                CitationStatus.UNVERIFIED.value,
                MEITY_AI_EFFECTIVE,
                {"sectors": ["all"], "ai_types": ["ml_model", "llm", "generative", "hybrid"], "conditions": ["high_risk"]},
            ),
            (
                "MEITY-OVERSIGHT-001",
                "Human oversight for high-stakes decisions",
                "Maintain human oversight for high-stakes automated decisions "
                "(credit, hiring, insurance). Advisory guidance.",
                "GOVERNANCE",
                "meity_human_oversight",
                "MEDIUM",
                "People First / Human oversight",
                "MeitY India AI Governance Guidelines (guidance)",
                "AI governance guidance — human oversight",
                "https://indiaai.gov.in/",
                LegalStatus.GUIDANCE.value,
                CitationStatus.UNVERIFIED.value,
                MEITY_AI_EFFECTIVE,
                {"sectors": ["all"], "ai_types": ["all"], "conditions": ["automated_decisions"]},
            ),
            (
                "MEITY-LINEAGE-001",
                "Model lineage / auditability",
                "Track lineage for AI outputs (prompt, retrieved context, model version, "
                "parameters, reviewer) to support explainability. Advisory guidance.",
                "GOVERNANCE",
                "model_lineage",
                "LOW",
                "Understandable by Design",
                "MeitY India AI Governance Guidelines (guidance)",
                "AI governance guidance — explainability",
                "https://indiaai.gov.in/",
                LegalStatus.GUIDANCE.value,
                CitationStatus.UNVERIFIED.value,
                MEITY_AI_EFFECTIVE,
                {"sectors": ["all"], "ai_types": ["all"], "conditions": []},
            ),
        ],
    }


def _seed_one_pack(db: Session, pack: dict) -> Regulation:
    reg_def = pack["regulation"]
    regulation = db.scalar(select(Regulation).where(Regulation.name == reg_def["name"]))
    if regulation is None:
        regulation = Regulation(
            jurisdiction="India",
            pack=PACK_NAME,
            pack_version=PACK_VERSION,
            enabled=True,
            created_at=utcnow(),
            updated_at=utcnow(),
            **reg_def,
        )
        db.add(regulation)
        db.flush()

    obligation_by_title: dict[str, Obligation] = {}
    for (
        code,
        title,
        description,
        category,
        evaluator,
        severity,
        obligation_title,
        legal_ref,
        section,
        source_url,
        legal_status,
        citation_status,
        eff,
        applies_to,
    ) in pack["controls"]:
        if db.scalar(select(Control).where(Control.code == code)) is not None:
            continue

        obligation = obligation_by_title.get(obligation_title)
        if obligation is None:
            obligation = db.scalar(
                select(Obligation).where(
                    Obligation.regulation_id == regulation.id,
                    Obligation.title == obligation_title,
                )
            )
        if obligation is None:
            obligation = Obligation(
                regulation_id=regulation.id,
                code=f"OBL-{code}",
                title=obligation_title,
                description=description,
                legal_reference=legal_ref,
                source_section=section,
                source_url=source_url,
                legal_status=legal_status,
                citation_status=citation_status,
                effective_from=eff,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(obligation)
            db.flush()
        obligation_by_title[obligation_title] = obligation

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
                applies_to=applies_to,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
    db.flush()
    return regulation


# --- Cross-framework mappings ---------------------------------------------------
# System (knowledge-base) mappings linking the DPDP control library to the RBI /
# CERT-In / MeitY packs. (source_code, target_code, relation, confidence, rationale)
# Direction: source -> target. Coverage relations (EQUIVALENT / SUPERSET) drive
# evidence reuse; RELATED is informational only.
_MAPPINGS: list[tuple[str, str, MappingRelation, float, str]] = [
    (
        "DPDP-SECURITY-003",
        "CERTIN-LOGS-001",
        MappingRelation.RELATED,
        0.8,
        "Both require logging/monitoring of access; CERT-In additionally fixes a "
        "180-day India-resident retention period, so DPDP evidence is related but "
        "does not by itself prove the CERT-In retention duration.",
    ),
    (
        "DPDP-BREACH-001",
        "CERTIN-INCIDENT-001",
        MappingRelation.RELATED,
        0.75,
        "Both concern breach/incident response. CERT-In imposes a specific 6-hour "
        "reporting pathway to CERT-In that DPDP breach handling does not, so this "
        "is related rather than equivalent.",
    ),
    (
        "DPDP-CROSSBORDER-001",
        "RBI-LOCALIZATION-001",
        MappingRelation.RELATED,
        0.7,
        "Both govern where data may reside/flow. RBI localisation is an absolute "
        "storage-in-India rule for payment data; DPDP cross-border governance is "
        "broader and restriction-list based.",
    ),
    (
        "DPDP-VENDOR-001",
        "RBI-VENDOR-001",
        MappingRelation.SUPERSET,
        0.85,
        "DPDP processor/vendor governance (valid contract, governed processing) "
        "broadly covers the RBI vendor expectation; RBI adds BFSI data-residency "
        "and audit-right specifics that still warrant review.",
    ),
    (
        "DPDP-SDF-001",
        "MEITY-INVENTORY-001",
        MappingRelation.RELATED,
        0.6,
        "A DPIA process and an AI-system inventory both support accountability, "
        "but address different artefacts.",
    ),
    (
        "DPDP-GOVERNANCE-001",
        "MEITY-OVERSIGHT-001",
        MappingRelation.RELATED,
        0.5,
        "Both sit under accountability/oversight; the DPDP contact-information "
        "control does not establish human oversight of automated decisions.",
    ),
]


def seed_mappings(db: Session) -> int:
    """Idempotently seed the system control-mapping graph. Returns count added."""
    added = 0
    for source_code, target_code, relation, confidence, rationale in _MAPPINGS:
        source = db.scalar(select(Control).where(Control.code == source_code))
        target = db.scalar(select(Control).where(Control.code == target_code))
        if source is None or target is None:
            continue
        existing = db.scalar(
            select(ControlMapping).where(
                ControlMapping.source_control_id == source.id,
                ControlMapping.target_control_id == target.id,
                ControlMapping.organization_id.is_(None),
            )
        )
        if existing is not None:
            continue
        db.add(
            ControlMapping(
                source_control_id=source.id,
                target_control_id=target.id,
                relation_type=relation.value,
                rationale=rationale,
                confidence=confidence,
                organization_id=None,
                created_by=None,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        added += 1
    db.flush()
    return added


def seed_packs(db: Session) -> list[Regulation]:
    """Idempotently seed the RBI, CERT-In and MeitY packs."""
    regs = [
        _seed_one_pack(db, _rbi_pack()),
        _seed_one_pack(db, _certin_pack()),
        _seed_one_pack(db, _meity_pack()),
    ]
    seed_mappings(db)
    return regs
