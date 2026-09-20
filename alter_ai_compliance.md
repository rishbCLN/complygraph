Here's your complete, exhaustive instruction file. Feed this directly to Claude as the task prompt. It's structured so that Claude can work module-by-module without ambiguity, with every regulation, schema, edge case, and demo scenario explicitly specified.

---

```markdown
# SOVEREIGN AI COMPLIANCE ENGINE — INSTRUCTIONS FOR AUTONOMOUS BUILD

## MISSION

Build a working, demo-ready **Sovereign AI Compliance Engine** — an agent that ingests an AI system's architecture description, autonomously maps it against India's full regulatory stack, identifies compliance gaps with severity scoring, generates remediation steps, produces a regulator-ready report, and simulates continuous drift monitoring.

This is a hackathon build. The demo must be visceral: show a sample architecture being scanned, violations being found in real-time, and a report being generated. The "wow" moment is the engine catching a subtle violation that a human auditor would miss (e.g., a logging pipeline sending telemetry to a US-based observability tool, or a RAG pipeline's vector store replicating to a foreign region for "backup").

---

## SECTION 1: REGULATORY KNOWLEDGE BASE (ENCODE ALL OF THIS)

This is the complete regulatory corpus the engine must check against. Structure it as a JSON/YAML knowledge base with the following entries. Each rule must have: `id`, `regulation`, `section`, `requirement`, `applies_to`, `data_type`, `severity`, `penalty`, `deadline`, `check_logic`, `remediation`.

### 1.1 DPDP Act 2023 + DPDP Rules 2025

**Status:** Enacted Aug 11, 2023. Rules notified Nov 13, 2025. Phase 1 (definitions, DPB constitution, digital functioning) operative Nov 14, 2025. Phase 2 (consent management rules) effective Nov 2026. Full substantive obligations: May 13, 2027.

**Core Principles (7):**
1. Purpose Limitation — Data collected for one AI use case cannot be repurposed without fresh, specific consent
2. Data Minimization — "More data = better model" requires explicit justification
3. Accuracy — Personal data in AI decision-making must be accurate and current
4. Storage Limitation — No permanent training data archives; retention schedules must be defined and enforced
5. Security Safeguards — Reasonable security across full AI data lifecycle (collection, training, inference, deletion)
6. Consent — Primary legal basis. NO "legitimate interest" exception for AI training data
7. Accountability — The Data Fiduciary is accountable for all processing

**Key Obligations for AI Systems:**

| ID | Obligation | Check Logic | Severity |
|---|---|---|---|
| DPDP-001 | Consent obtained for personal data processing in AI training | Architecture must declare consent mechanism; if training on personal data without explicit consent → VIOLATION | CRITICAL |
| DPDP-002 | Purpose limitation — data not repurposed across use cases | Check if same data source feeds multiple AI models without separate consent | HIGH |
| DPDP-003 | Data minimization — only necessary data collected | Check if training data includes fields beyond what's needed for the stated purpose | MEDIUM |
| DPDP-004 | Cross-border transfer compliance | If data flows to a foreign endpoint AND that country is on the restricted list → VIOLATION. (As of Sept 2026: no countries restricted, but flag as WATCH) | CRITICAL (if restricted) / LOW (watch) |
| DPDP-005 | Breach notification — immediate to DPB + affected individuals, detailed report within 72 hours | Architecture must have a breach detection + notification pipeline. If absent → GAP | HIGH |
| DPDP-006 | Children's data (under 18) — verifiable parental consent required | If system processes data of users under 18 without verifiable parental consent mechanism → VIOLATION | CRITICAL |
| DPDP-007 | Children's data — no tracking, behavioural monitoring, or targeted advertising | If system profiles or tracks users under 18 → VIOLATION | CRITICAL |
| DPDP-008 | Automated decision-making — right to dispute | If system makes automated decisions (credit, hiring, insurance) without a human-review/dispute mechanism → GAP | HIGH |
| DPDP-009 | Significant Data Fiduciary (SDF) obligations: DPIA, periodic audits, India-resident DPO | If data volume/sensitivity triggers SDF classification and these are absent → GAP | HIGH |
| DPDP-010 | Consent Manager registration (Phase 2, Nov 2026) | If relying on third-party consent platforms, they must be registered Consent Managers (Indian-incorporated, ₹2Cr net worth, AES-256, 7-year records) | MEDIUM |
| DPDP-011 | Data erasure — must honor deletion requests, implications for model retraining | If no mechanism to handle erasure requests (including from training data) → GAP | HIGH |
| DPDP-012 | Security safeguards across full lifecycle | Check: encryption at rest, in transit, access controls, key management, deletion verification | MEDIUM |

**Penalties:** Up to ₹250 crore (~$30M) per instance, graded by severity.

**Key Distinction from GDPR:** No "legitimate interest" basis. No data portability right. No explicit Article 22 equivalent. Cross-border is blacklist (permitted unless restricted), not whitelist. Breach notification: ALL breaches (not just those posing risk).

### 1.2 RBI Data Localization + AI Guidelines

**Status:** RBI PSS Circular 2018 (payment data), RBI Digital Lending Directions 2025, RBI AI-related circulars 2025-26.

| ID | Obligation | Check Logic | Severity |
|---|---|---|---|
| RBI-001 | Payment system data: end-to-end storage ONLY in India | If any payment transaction data (UPI, card, wallet) is stored, processed, or replicated outside India → VIOLATION | CRITICAL |
| RBI-002 | 24-hour repatriation rule: offshore-processed data must be deleted and repatriated within 24 hours | If architecture shows data leaving India for processing (even temporarily) without a 24h deletion+repatriation mechanism → VIOLATION | CRITICAL |
| RBI-003 | KYC data must reside in India | If KYC data (Aadhaar, PAN, biometric) is stored or processed outside India → VIOLATION | CRITICAL |
| RBI-004 | AI model training data containing payment/customer data must be processed within India | If training pipeline sends customer/payment data to foreign compute → VIOLATION | CRITICAL |
| RBI-005 | AI model inference must occur on India-based infrastructure (expected 2026-2027 enforcement) | If inference endpoint is outside India → VIOLATION (flag as EMERGING if not yet enforced) | CRITICAL |
| RBI-006 | Derived insights/scores must be stored in India | If risk scores, fraud scores, or derived analytics are stored outside India → VIOLATION | HIGH |
| RBI-007 | Logging and telemetry: AI system logs containing customer data must NOT be sent to global monitoring services | If architecture shows logs/telemetry flowing to Datadog/New Relic/Splunk in foreign regions → VIOLATION | HIGH |
| RBI-008 | Model improvement/fine-tuning loops: customer interaction data used for fine-tuning must stay in India | If fine-tuning pipeline sends interaction data to foreign infrastructure → VIOLATION | HIGH |
| RBI-009 | Backup and DR: copies of RBI-governed data must also be in India | If DR region is outside India → VIOLATION | HIGH |
| RBI-010 | Analytics pipelines: aggregated but still derived data must not flow to global analytics platforms | If analytics/BI tools pull from foreign regions → VIOLATION | MEDIUM |
| RBI-011 | Third-party AI vendors: must demonstrate India-only data processing, audit access, RBI inspection rights | If vendor contracts lack data localization clauses or audit rights → GAP | HIGH |
| RBI-012 | Digital lending: borrower data stored on servers in India; offshore data deleted within 24h; biometric data CANNOT be stored | If biometric data is stored (even encrypted) → VIOLATION. If borrower data offshore → VIOLATION | CRITICAL |
| RBI-013 | Video KYC: AI-assisted KYC allowed but liveness detection, document verification, face matching must comply with specific constraints | If AI KYC pipeline doesn't meet V-CIP guidelines → GAP | MEDIUM |
| RBI-014 | Board-level/IT Committee approval required for AI deployment | If architecture shows no governance approval trail → GAP | MEDIUM |
| RBI-015 | Outsourcing Direction applies to third-party AI: bank retains ultimate responsibility for AI outputs | If no accountability framework for vendor AI outputs → GAP | MEDIUM |

**Common Compliance Gaps (what the engine should specifically hunt for):**
- Logging/telemetry to global observability (Datadog, New Relic, Splunk, Honeycomb in US/EU regions)
- Model improvement loops using customer data on foreign infra
- DR copies in foreign regions
- Analytics pipelines pulling to global BI tools
- "Shadow" data flows: A/B testing platforms, feature stores, vector DBs with foreign replicas

### 1.3 SEBI (Securities & Exchange Board of India)

| ID | Obligation | Check Logic | Severity |
|---|---|---|---|
| SEBI-001 | Regulated entities using cloud must keep regulatory and compliance data within India | If SEBI-regulated data (broking, MF distribution, logs) is on shared cloud with non-India path → VIOLATION | HIGH |
| SEBI-002 | AI in trading/market surveillance: architecture must satisfy data residency independently of DPDP | If trading AI uses foreign inference endpoints → VIOLATION | HIGH |

### 1.4 IRDAI (Insurance Regulatory & Development Authority of India)

| ID | Obligation | Check Logic | Severity |
|---|---|---|---|
| IRDAI-001 | Policy and claims data must be stored locally in India | If insurance data is stored/processed outside India → VIOLATION | HIGH |

### 1.5 UIDAI (Aadhaar)

| ID | Obligation | Check Logic | Severity |
|---|---|---|---|
| UIDAI-001 | Aadhaar data must be in dedicated Aadhaar Data Vault: on-premises in India OR MeitY-empanelled Government Community Cloud | If Aadhaar data is in a general application database (even in India) → VIOLATION | CRITICAL |
| UIDAI-002 | Tokenised/encrypted Aadhaar in offshore application DB → VIOLATION | If Aadhaar tokens are in any foreign database → VIOLATION | CRITICAL |

### 1.6 CERT-In (Cyber Security Incident Reporting)

| ID | Obligation | Check Logic | Severity |
|---|---|---|---|
| CERTIN-001 | Cybersecurity incident logs must be maintained in India for 180 days | If logs are only in foreign SIEM with no Indian copy → VIOLATION | HIGH |
| CERTIN-002 | AI platforms must report cybersecurity incidents to CERT-In within 6 hours | If no incident reporting pipeline to CERT-In exists → GAP | HIGH |

### 1.7 IT Rules Amendment 2026 (effective Feb 20, 2026)

**Applies to:** All AI-integrated platforms serving Indian users. Enhanced obligations for platforms with 5M+ registered users (SSMI classification).

| ID | Obligation | Check Logic | Severity |
|---|---|---|---|
| IT26-001 | Active Moderation: proactive monitoring of AI-generated content (not just reactive) | If platform has AI content generation but no active moderation pipeline → VIOLATION | HIGH |
| IT26-002 | Mandatory AI content labeling: all SGI must be "clearly and prominently labeled" | If AI generates content (text, image, audio, video) without persistent visible labels → VIOLATION | HIGH |
| IT26-003 | Provenance metadata: embed permanent metadata/unique identifiers to trace origin of AI content | If AI-generated content lacks C2PA or equivalent provenance metadata → GAP | MEDIUM |
| IT26-004 | Takedown: 3 hours for court/government orders (reduced from 36h); 2 hours for high-risk (deepfake nudity, intimate imagery) | If takedown SLA exceeds these windows → VIOLATION | CRITICAL |
| IT26-005 | Automated filtering: must deploy AI filters to block CSAM and non-consensual intimate images generated by AI | If no automated filtering for prohibited SGI → VIOLATION | CRITICAL |
| IT26-006 | Quarterly user notification (previously annual) about platform rules, consequences, reporting | If notification cadence is not quarterly → GAP | LOW |
| IT26-007 | SSMI (5M+ users): Chief Compliance Officer, Nodal Contact Person, Resident Grievance Officer — all India-resident | If platform has 5M+ Indian users and lacks these roles → VIOLATION | HIGH |
| IT26-008 | Monthly compliance reports must be published (SSMI) | If no monthly compliance report mechanism → GAP | MEDIUM |
| IT26-009 | Safe harbour (Section 79) is CONDITIONAL on active moderation + labeling + meeting takedown deadlines | If any of the above are missing, safe harbour is lost → RISK FLAG | CRITICAL |
| IT26-010 | Upload declaration: users must declare if content is AI-generated | If no upload declaration workflow → GAP | MEDIUM |

### 1.8 MeitY AI Governance Guidelines (Nov 2025) — Voluntary but sets standard

**7 Sutras:**
1. Trust is the Foundation
2. People First (human-centric, human oversight)
3. Innovation over Restraint
4. Fairness & Equity (no bias/discrimination)
5. Accountability
6. Understandable by Design (explainability)
7. Safety, Resilience & Sustainability

**6 Pillars:** Infrastructure, Capacity Building, Policy & Regulation, Risk Mitigation, Accountability, Institutions

**3 Bodies:** AIGG (AI Governance Group), TPEC (Technology Policy Evaluation Committee), AISI (AI Safety Institute)

| ID | Obligation | Check Logic | Severity |
|---|---|---|---|
| MEITY-001 | AI system inventory: all AI/ML models in production must be inventoried | If architecture shows AI systems without a central inventory → GAP | MEDIUM |
| MEITY-002 | Bias audit: conduct and document algorithmic fairness testing across protected categories (religion, caste, gender, disability) | If no bias testing documented → GAP | HIGH |
| MEITY-003 | Explainability: AI systems should be explainable/interpretable to the extent feasible | If high-risk AI (credit, hiring, insurance) has no explainability mechanism → GAP | HIGH |
| MEITY-004 | Grievance mechanism: user complaint process for AI-related harms | If no grievance mechanism → GAP | MEDIUM |
| MEITY-005 | Self-certification: AI models must self-certify they don't generate unlawful content | If no self-certification documentation → GAP | MEDIUM |
| MEITY-006 | Human oversight: robust human oversight for high-stakes decisions | If fully automated high-stakes decisions without human-in-the-loop → GAP | HIGH |
| MEITY-007 | Incident reporting framework aligned with AISI | If no AI-specific incident reporting (beyond CERT-In) → GAP | LOW |

### 1.9 IndiaAI Mission (₹10,372 crore)

- No AI-specific licence required
- Companies register as standard entities
- Subsidized compute (₹65/GPU-hour)
- Responsible AI benchmarks (emerging)
- AI Safety Institute for frontier model evaluation

### 1.10 Cross-Cutting / Structural Rules

| ID | Rule | Check Logic |
|---|---|---|
| X-001 | Data flow mapping: every AI system must have a complete data flow map (source → processing → storage → deletion) | If architecture lacks complete data flow documentation → GAP |
| X-002 | Vendor register: every external service touching personal data must have a Data Processor agreement | If vendors are not registered with DPA → GAP |
| X-003 | Retention schedules: defined and enforced for all AI pipelines | If no retention policy → GAP |
| X-004 | Audit logging: every AI agent invocation must be logged (input, output, model version, parameters, timestamp) | If no invocation logging → GAP |
| X-005 | Model versioning + lineage: full lineage of any model output (prompt, retrieved context, model version, parameters, human reviewer) | If no model lineage tracking → GAP |
| X-006 | Disaster recovery: DR must be in India for regulated data | If DR is foreign → VIOLATION (for regulated data) |
| X-007 | Encryption: AES-256 at minimum for personal data at rest | If encryption is below AES-256 → GAP |
| X-008 | Access controls: role-based access to personal data, least privilege | If no RBAC or overly broad access → GAP |

---

## SECTION 2: SYSTEM ARCHITECTURE

### 2.1 High-Level Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SOVEREIGN AI COMPLIANCE ENGINE                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  INPUT LAYER  │───▶│  COMPLIANCE      │───▶│  REPORT          │  │
│  │              │    │  MAPPING AGENT   │    │  GENERATOR       │  │
│  │ • Architecture│    │                  │    │                  │  │
│  │   descriptor │    │ • Rule matching  │    │ • Regulator-ready│  │
│  │ • Data flow  │    │ • Gap analysis   │    │ • Severity scoring│  │
│  │   declarations│   │ • Remediation    │    │ • Executive summary│ │
│  │ • Vendor list│    │   generation     │    │ • Drill-down per  │  │
│  │ • Access ctrl│    │ • Cross-ref      │    │   violation       │  │
│  │   matrix     │    │   (rule↔rule)   │    │ • PDF/HTML output │  │
│  └──────────────┘    └──────────────────┘    └──────────────────┘  │
│         │                     │                          │          │
│         ▼                     ▼                          ▼          │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  KNOWLEDGE   │    │  DRIFT MONITOR   │    │  DASHBOARD       │  │
│  │  BASE        │    │  (simulated)     │    │  (demo UI)       │  │
│  │              │    │                  │    │                  │  │
│  │ • All rules  │    │ • Re-scan on     │    │ • Violation list │  │
│  │   from S1    │    │   config change  │    │ • Compliance     │  │
│  │ • Severity   │    │ • New data flow  │    │   score          │  │
│  │   weights    │    │   detection      │    │ • Timeline to    │  │
│  │ • Penalty    │    │ • Vendor change  │    │   deadline       │  │
│  │   references │    │   detection      │    │ • Remediation    │  │
│  │ • Deadline   │    │ • Alert generation│   │   tracker        │  │
│  │   tracking   │    │                  │    │                  │  │
│  └──────────────┘    └──────────────────┘    └──────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Tech Stack

- **Language:** Python 3.11+
- **Agent framework:** Claude Agent SDK (or direct API calls with tool use)
- **Model:** Claude Sonnet 4 (for the reasoning agent) — use Opus for the final report generation if tokens allow
- **Knowledge base:** JSON files (one per regulation) + a consolidated index
- **Input format:** YAML architecture descriptor (schema below)
- **Output:** JSON (structured findings) + HTML report (human-readable) + terminal output (for demo)
- **UI:** Simple Streamlit or Gradio dashboard for the demo (optional but recommended)
- **Testing:** pytest with fixture architectures

### 2.3 File Structure

```
sovereign-ai-compliance/
├── main.py                    # Entry point
├── agent/
│   ├── __init__.py
│   ├── compliance_agent.py    # Main agent loop
│   ├── tools.py               # Tool definitions for Claude
│   └── prompts.py             # System prompts for each agent phase
├── knowledge_base/
│   ├── __init__.py
│   ├── loader.py              # Loads and indexes all rules
│   ├── dpdp.json              # DPDP Act + Rules
│   ├── rbi.json               # RBI regulations
│   ├── sebi.json              # SEBI
│   ├── irdai.json             # IRDAI
│   ├── uidai.json             # UIDAI
│   ├── certin.json            # CERT-In
│   ├── it_rules_2026.json     # IT Rules Amendment 2026
│   ├── meity_ai.json          # MeitY AI Governance Guidelines
│   ├── indiaai.json           # IndiaAI Mission
│   └── cross_cutting.json     # Cross-cutting rules
├── input/
│   ├── schema.yaml            # Architecture descriptor schema
│   └── samples/
│       ├── bfsi_compliant.yaml    # A compliant BFSI AI system
│       ├── saas_violation.yaml    # A SaaS with multiple violations
│       ├── subtle_drift.yaml      # Architecture with hidden violations
│       └── platform_ssmi.yaml     # A large platform (SSMI)
├── output/
│   ├── findings/              # JSON findings per scan
│   └── reports/               # Generated HTML/PDF reports
├── monitor/
│   ├── __init__.py
│   ├── drift_detector.py      # Simulated drift monitoring
│   └── alerts.py              # Alert generation
├── report/
│   ├── __init__.py
│   ├── generator.py           # Report generation
│   ├── templates/
│   │   ├── regulator.html     # Regulator-ready template
│   │   └── executive.html     # Executive summary template
│   └── scoring.py             # Compliance score calculation
├── dashboard/
│   ├── app.py                 # Streamlit/Gradio app
│   └── components.py
├── tests/
│   ├── test_rules.py          # Test rule matching logic
│   ├── test_agent.py          # Test agent end-to-end
│   ├── test_report.py         # Test report generation
│   └── fixtures/              # Test fixtures
├── requirements.txt
├── README.md
└── demo.sh                    # One-command demo script
```

---

## SECTION 3: INPUT SCHEMA (ARCHITECTURE DESCRIPTOR)

The engine accepts a YAML file describing the AI system's architecture. This is the "input" that gets scanned.

```yaml
# architecture.yaml — Schema for AI System Architecture Descriptor

system:
  name: "string"                    # Name of the AI system
  owner: "string"                   # Organization name
  sector: "enum"                    # [bfsi, insurance, healthcare, government, saas, platform, edtech, other]
  description: "string"             # What the system does
  ai_type: "enum"                   # [llm, ml_model, generative, agentic, hybrid, rule_based]
  risk_level: "enum"                # [high, medium, low] — self-assessed
  deployment_model: "enum"          # [on_premise, private_cloud, sovereign_cloud, public_cloud, hybrid, air_gapped]
  cloud_provider: "string"          # e.g., "AWS", "Azure", "GCP", "On-prem"
  cloud_region: "string"            # e.g., "ap-south-1", "us-east-1", "in-west"
  users_in_india: "integer"         # Number of registered users in India
  is_intermediary: "boolean"        # Is this platform an intermediary under IT Act?
  is_ssmi: "boolean"                # Is it a Significant Social Media Intermediary (5M+ users)?

data_flows:
  - id: "string"                    # Unique flow ID
    name: "string"                  # Human-readable name
    source: "string"                # Where data originates
    destination: "string"           # Where data goes
    data_types: ["string"]          # Types of data in this flow (see data_type_enum)
    personal_data: "boolean"        # Does this flow contain personal data?
    cross_border: "boolean"         # Does this flow cross national borders?
    destination_country: "string"   # If cross_border, which country?
    purpose: "string"               # Why does this flow exist?
    encryption: "string"            # [none, tls_1_2, tls_1_3, aes_256, other]
    retention: "string"             # How long is data retained? [e.g., "30 days", "permanent", "7 years"]
    deletion_mechanism: "string"    # How is data deleted? [automatic, manual, none]

data_storage:
  - id: "string"
    name: "string"
    location: "string"              # Physical location (e.g., "Mumbai, India", "Virginia, USA")
    type: "enum"                    # [database, vector_db, object_storage, data_lake, cache, log_store, model_weights]
    data_types: ["string"]
    personal_data: "boolean"
    encryption_at_rest: "string"    # [none, aes_256, other]
    access_control: "string"        # [none, rbac, abac, mfa_required, other]
    retention: "string"
    is_dr_copy: "boolean"           # Is this a disaster recovery copy?
    dr_location: "string"           # If is_dr_copy, where is primary?

model:
  name: "string"
  type: "enum"                      # [llm, fine_tuned, rag, traditional_ml, ensemble]
  base_model: "string"              # e.g., "GPT-4", "Claude", "Llama", "Custom"
  model_hosting: "string"           # Where the model runs (region/infra)
  inference_endpoint: "string"      # URL or region of inference
  training_data:
    source: "string"
    contains_personal_data: "boolean"
    consent_obtained: "boolean"
    consent_mechanism: "string"     # How consent was obtained
    data_location: "string"         # Where training data is stored
  fine_tuning:
    enabled: "boolean"
    data_source: "string"
    data_location: "string"         # Where fine-tuning data is processed
    contains_customer_data: "boolean"
  rag:
    enabled: "boolean"
    vector_store: "string"          # e.g., "Pinecone", "Weaviate", "Milvus"
    vector_store_location: "string" # Region of vector store
    vector_store_replicas: ["string"] # All replica locations
    document_source: "string"       # Where source documents come from

vendors:
  - name: "string"
    service: "string"               # What they provide
    data_access: "boolean"          # Do they access personal data?
    data_location: "string"         # Where they process/store data
    dpa_signed: "boolean"           # Data Processor Agreement signed?
    audit_rights: "boolean"         # Do you have audit rights?
    sub_processors: ["string"]      # Their sub-processors

access_controls:
  authentication: "string"          # [none, password, mfa, sso, hardware_key]
  authorization: "string"           # [none, rbac, abac, other]
  audit_logging: "boolean"          # Is there audit logging?
  log_location: "string"            # Where logs are stored
  log_retention: "string"           # How long logs are kept
  siem: "string"                    # What SIEM is used (if any)
  siem_location: "string"           # Where SIEM data is stored

consent:
  mechanism: "string"               # [banner, in_app, api, third_party, none]
  consent_manager: "string"         # If third_party, which Consent Manager?
  consent_manager_registered: "boolean"
  withdrawal_mechanism: "string"    # How can users withdraw consent?
  childrens_consent: "string"       # [not_applicable, verifiable_parental, age_gate, none]
  purpose_specific: "boolean"       # Is consent specific to each purpose?

breach_response:
  detection_mechanism: "string"     # How are breaches detected?
  notification_pipeline: "string"   # How is DPB notified?
  notification_timeline: "string"   # Target timeline
  user_notification: "boolean"      # Are affected users notified?
  runbook_exists: "boolean"         # Is there an incident response runbook?
  last_drill_date: "string"         # When was the last breach response drill?

governance:
  ai_inventory: "boolean"           # Is there a central AI system inventory?
  bias_testing: "boolean"           # Is bias/fairness testing conducted?
  bias_test_documentation: "string" # Where are results stored?
  explainability: "string"          # [none, lime, shap, attention, custom, not_applicable]
  human_oversight: "string"         # [none, sampling, full_review, escalation_only]
  grievance_mechanism: "boolean"    # Is there a user grievance process?
  self_certification: "boolean"     # Has self-certification been done?
  board_approval: "boolean"         # Has board/IT committee approved deployment?
  model_lineage: "boolean"          # Is full model lineage tracked?

content_generation:
  enabled: "boolean"                # Does the system generate content?
  content_types: ["string"]         # [text, image, audio, video, code]
  labeling: "boolean"               # Is AI-generated content labeled?
  label_mechanism: "string"         # How? [visible_badge, metadata, watermark, c2pa, none]
  provenance_metadata: "boolean"    # Is provenance metadata embedded?
  takedown_sla_hours: "number"      # What's the takedown SLA?
  automated_filtering: "boolean"    # Is there automated filtering for prohibited content?
  upload_declaration: "boolean"     # Do users declare if content is AI-generated?

compliance:
  dpdp_registered: "boolean"        # Registered with Data Protection Board?
  dpo_appointed: "boolean"          # Data Protection Officer appointed?
  dpo_resident_india: "boolean"     # Is DPO India-resident?
  is_sdf: "boolean"                 # Is the entity a Significant Data Fiduciary?
  dpia_conducted: "boolean"         # Data Protection Impact Assessment done?
  certin_reporting: "boolean"       # CERT-In incident reporting pipeline exists?
  certin_log_retention_days: "integer"  # How many days are logs retained for CERT-In?
```

**data_type_enum** (for use in data_flows and data_storage):
```
[payment_transaction, kyc, aadhaar, biometric, health, financial, 
 personal_identity, contact_info, behavioral, transactional, 
 model_training, inference_output, log_telemetry, analytics_derived,
 content_generated, user_generated, vendor_shared, government]
```

---

## SECTION 4: AGENT DESIGN

### 4.1 Agent Loop

The compliance agent operates in a **multi-phase pipeline**, not a single ReAct loop. Each phase has a specific job:

```
PHASE 1: INGEST & PARSE
  → Read the architecture YAML
  → Validate against schema
  → Build an internal "system model" (graph of data flows, storage, vendors)
  → Identify sector-specific applicability (which rules apply based on sector, user count, etc.)

PHASE 2: RULE MATCHING (the core)
  → For each applicable rule in the knowledge base:
    → Check the system model against the rule's check_logic
    → Determine: COMPLIANT / VIOLATION / GAP / WATCH / NOT_APPLICABLE
    → If VIOLATION or GAP: extract the specific evidence from the architecture
    → Assign severity (from rule definition, adjusted by context)
  → Cross-reference: check if multiple rules are violated by the same data flow
  → Check for "hidden" violations (e.g., a vendor's sub-processor in a foreign country)

PHASE 3: REMEDIATION GENERATION
  → For each VIOLATION and GAP:
    → Generate specific, actionable remediation steps
    → Estimate effort (hours/days)
    → Prioritize by severity × deadline urgency
  → Generate a remediation roadmap (what to fix first, what can wait)

PHASE 4: REPORT GENERATION
  → Calculate overall compliance score (weighted)
  → Generate executive summary (1 page)
  → Generate regulator-ready detailed report
  → Generate drill-down per violation
  → Flag items with approaching deadlines

PHASE 5: DRIFT SIMULATION (for demo)
  → Take the "compliant" architecture
  → Inject a subtle change (e.g., "3 days ago, a new logging pipeline was added sending telemetry to Datadog us-east-1")
  → Re-run the scan
  → Show the NEW violation that was caught
  → Generate an alert
```

### 4.2 Tool Definitions for Claude

```python
tools = [
    {
        "name": "get_rule",
        "description": "Retrieve a specific compliance rule by ID from the knowledge base",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule_id": {"type": "string", "description": "e.g., 'DPDP-001', 'RBI-007'"}
            },
            "required": ["rule_id"]
        }
    },
    {
        "name": "get_all_rules",
        "description": "Retrieve all rules applicable to a given sector and system type",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {"type": "string"},
                "ai_type": {"type": "string"},
                "is_intermediary": {"type": "boolean"},
                "is_ssmi": {"type": "boolean"}
            }
        }
    },
    {
        "name": "get_data_flow",
        "description": "Get details of a specific data flow from the architecture",
        "input_schema": {
            "type": "object",
            "properties": {
                "flow_id": {"type": "string"}
            },
            "required": ["flow_id"]
        }
    },
    {
        "name": "get_all_data_flows",
        "description": "Get all data flows, optionally filtered by data type or cross-border status",
        "input_schema": {
            "type": "object",
            "properties": {
                "data_type": {"type": "string"},
                "cross_border_only": {"type": "boolean"},
                "personal_data_only": {"type": "boolean"}
            }
        }
    },
    {
        "name": "get_storage",
        "description": "Get details of a specific storage location",
        "input_schema": {
            "type": "object",
            "properties": {
                "storage_id": {"type": "string"}
            },
            "required": ["storage_id"]
        }
    },
    {
        "name": "get_vendor",
        "description": "Get details of a specific vendor including sub-processors",
        "input_schema": {
            "type": "object",
            "properties": {
                "vendor_name": {"type": "string"}
            },
            "required": ["vendor_name"]
        }
    },
    {
        "name": "record_finding",
        "description": "Record a compliance finding (violation, gap, or watch item)",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule_id": {"type": "string"},
                "status": {"type": "string", "enum": ["VIOLATION", "GAP", "WATCH", "COMPLIANT"]},
                "evidence": {"type": "string", "description": "Specific evidence from the architecture"},
                "severity": {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
                "affected_components": {"type": "array", "items": {"type": "string"}},
                "penalty_reference": {"type": "string"},
                "deadline": {"type": "string"},
                "remediation": {"type": "string"}
            },
            "required": ["rule_id", "status", "evidence", "severity"]
        }
    },
    {
        "name": "calculate_compliance_score",
        "description": "Calculate the overall compliance score based on all findings",
        "input_schema": {
            "type": "object",
            "properties": {
                "findings": {"type": "array"}
            },
            "required": ["findings"]
        }
    },
    {
        "name": "generate_report",
        "description": "Generate the final compliance report in the specified format",
        "input_schema": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["regulator", "executive", "json"]},
                "include_remediation": {"type": "boolean"}
            },
            "required": ["format"]
        }
    }
]
```

### 4.3 System Prompt for the Agent

```
You are the Sovereign AI Compliance Engine for India. Your job is to analyze an AI system's architecture and determine its compliance status against India's full regulatory stack.

REGULATORY FRAMEWORKS YOU MUST CHECK AGAINST:
1. DPDP Act 2023 + DPDP Rules 2025 (data protection)
2. RBI Data Localization + AI Guidelines (if sector = bfsi)
3. SEBI Cloud Framework (if sector involves capital markets)
4. IRDAI Data Localization (if sector = insurance)
5. UIDAI Aadhaar Vault Requirements (if Aadhaar data is present)
6. CERT-In Cyber Security Directions (all systems)
7. IT Rules Amendment 2026 (if system generates content or is an intermediary)
8. MeitY AI Governance Guidelines (voluntary but sets standard)
9. Cross-cutting structural requirements

YOUR PROCESS:
1. First, determine which rules are APPLICABLE based on the system's sector, type, user count, and data types.
2. For each applicable rule, check the architecture against the rule's requirements.
3. For each check, determine the status:
   - COMPLIANT: The architecture satisfies the requirement
   - VIOLATION: The architecture explicitly violates the requirement
   - GAP: The architecture does not demonstrate compliance (missing controls, undocumented)
   - WATCH: Currently compliant but at risk (e.g., cross-border transfer to a country that could be restricted)
   - NOT_APPLICABLE: The rule doesn't apply to this system
4. For every VIOLATION and GAP, provide:
   - Specific evidence from the architecture (quote the relevant field)
   - The exact rule being violated
   - Severity (CRITICAL/HIGH/MEDIUM/LOW)
   - Penalty reference
   - Specific remediation steps (not generic — tell them exactly what to change)
   - Deadline (if time-bound)

CRITICAL RULES FOR YOUR ANALYSIS:
- Be THOROUGH. Check every data flow. Check every storage location. Check every vendor AND their sub-processors.
- Look for HIDDEN violations: a logging pipeline to a foreign SIEM, a vector DB with foreign replicas, a "backup" that's actually a DR copy in a foreign region, telemetry to a global observability tool.
- Cross-reference: if a data flow contains personal data AND crosses borders, check BOTH the DPDP cross-border rule AND the sector-specific localization rule.
- Consider the FULL data lifecycle: collection → training → inference → storage → deletion. A violation at any stage counts.
- If the system is in the BFSI sector, RBI rules are ABSOLUTE. There are no exceptions for "temporary" processing.
- The 24-hour repatriation rule means: if data leaves India for processing, it MUST be deleted from the foreign location within 24 hours. "We'll delete it later" is not a valid mechanism.
- As of September 2026, no countries are on the DPDP restricted list. However, flag any cross-border flow as WATCH with a note: "Currently permitted, but subject to future restriction. Recommend building data localization capability as contingency."

OUTPUT FORMAT:
Use the record_finding tool for each finding. At the end, call calculate_compliance_score and generate_report.

COMPLIANCE SCORING:
- Start at 100
- CRITICAL violation: -25 points each
- HIGH violation/gap: -10 points each
- MEDIUM gap: -5 points each
- LOW gap/watch: -2 points each
- Floor at 0
- Score bands: 90-100 = Compliant, 70-89 = Minor Gaps, 50-69 = Significant Gaps, <50 = Critical Non-Compliance
```

### 4.4 Phase-Specific Prompts

**Phase 1 (Ingest & Parse):**
```
Parse the following architecture descriptor. Build a mental model of:
1. All data flows and their characteristics
2. All storage locations and what they contain
3. All vendors and their sub-processors
4. The model's training, inference, and RAG pipeline
5. The consent and breach response mechanisms
6. The governance and content generation capabilities

Then determine:
- Which sector-specific rules apply?
- Is this an intermediary? Is it SSMI?
- Does it process children's data?
- Does it handle Aadhaar?
- Does it generate content?
- Is it in the BFSI sector?

List all applicable rule IDs before proceeding to Phase 2.
```

**Phase 2 (Rule Matching):**
```
For each applicable rule, perform the check. Be systematic — go rule by rule, in this order:
1. Cross-cutting rules (X-001 to X-008)
2. DPDP rules (DPDP-001 to DPDP-012)
3. Sector-specific rules (RBI/SEBI/IRDAI/UIDAI as applicable)
4. CERT-In rules
5. IT Rules 2026 (if applicable)
6. MeitY guidelines

For each rule, state:
- Rule ID and name
- What you're checking
- What you found in the architecture
- Status: COMPLIANT / VIOLATION / GAP / WATCH / NOT_APPLICABLE
- If not compliant: evidence, severity, remediation

Pay special attention to:
- Data flows that contain personal data AND cross borders
- Storage locations that are DR copies (check their location)
- Vendors whose sub-processors are in foreign countries
- Logging/telemetry pipelines (these are the most commonly missed)
- Vector DB replicas (RAG systems often have replicas in multiple regions)
- Fine-tuning pipelines (where does the data go?)
- The model's inference endpoint location
```

**Phase 3 (Remediation):**
```
For each VIOLATION and GAP identified, generate specific remediation steps.

Rules for remediation:
- Be SPECIFIC. Don't say "implement data localization." Say "Move the Pinecone vector store from us-west-2 to ap-south-1. Update the application configuration in config/vector_store.yaml. Run a one-time data migration. Verify no cross-region replication is enabled."
- Include effort estimates (e.g., "2-3 engineering days")
- Include priority ordering (fix CRITICAL first, then HIGH, etc.)
- If a remediation has a deadline, state it explicitly
- If the remediation requires a vendor change, say which vendor and what contract amendment is needed
- Group related remediations (e.g., "All three of these flows need the same fix: move the logging pipeline to an India-region Datadog workspace")

Generate a remediation roadmap:
- Week 1: [CRITICAL items]
- Week 2-3: [HIGH items]
- Week 4-6: [MEDIUM items]
- Ongoing: [WATCH items, monitoring]
```

**Phase 4 (Report Generation):**
```
Generate the compliance report. Two formats:

1. EXECUTIVE SUMMARY (1 page):
   - Overall compliance score
   - Top 5 most critical findings
   - Deadline urgency (what needs to be fixed by when)
   - Financial exposure (sum of potential penalties)
   - Recommended immediate actions

2. REGULATOR-READY REPORT (detailed):
   - System identification
   - Scope of assessment
   - Methodology
   - Findings table (all findings, sorted by severity)
   - Detailed analysis per finding
   - Remediation plan
   - Compliance score calculation
   - Attestation section (for the Data Fiduciary to sign)
   - Appendix: list of all rules checked
```

**Phase 5 (Drift Simulation):**
```
Now simulate a drift event. Take the original architecture and make this change:

[INJECTED CHANGE — varies per demo scenario]

Re-run the compliance scan. Identify:
1. What NEW violations appeared?
2. What was previously compliant that is now violated?
3. Generate an alert in the format:
   "⚠️ DRIFT DETECTED: [description]
    Rule violated: [rule_id]
    Severity: [severity]
    Detected: [timestamp]
    Action required: [immediate remediation]"
```

---

## SECTION 5: KNOWLEDGE BASE FORMAT

Each rule in the JSON knowledge base must follow this schema:

```json
{
  "id": "RBI-007",
  "regulation": "RBI Data Localization + AI Guidelines",
  "section": "RBI Circular 2018 + 2025 AI Circular",
  "requirement": "AI system logs containing customer data must not be sent to global monitoring services",
  "applies_to": {
    "sectors": ["bfsi"],
    "ai_types": ["all"],
    "conditions": ["system processes customer data", "system uses external logging/observability"]
  },
  "data_types_affected": ["log_telemetry", "personal_identity", "financial"],
  "severity": "HIGH",
  "penalty": "Authorization revocation + monetary penalties (RBI)",
  "deadline": "Immediate (already enforced)",
  "check_logic": "If any data_flow has data_types containing 'log_telemetry' AND cross_border is true AND destination is not India → VIOLATION. Also check: if siem_location is not in India AND audit_logging is true AND sector is bfsi → VIOLATION.",
  "remediation_template": "Move SIEM/logging to India-region deployment. [Specific: e.g., 'Migrate from Datadog us-east-1 to Datadog ap-south-1, or deploy an on-premises logging solution in India. Ensure log retention meets CERT-In 180-day requirement. Update all application logging configurations to point to the new endpoint.']",
  "common_violation_patterns": [
    "Datadog/New Relic/Splunk in US or EU regions",
    "CloudWatch logs in non-India regions",
    "Centralized logging platform with foreign primary",
    "A/B testing platform receiving user data in foreign region"
  ],
  "cross_references": ["CERTIN-001", "DPDP-012", "X-004"]
}
```

**CRITICAL:** The `check_logic` field must be precise enough that the agent can deterministically evaluate it against the architecture. Avoid ambiguity. Use pseudo-code where necessary.

---

## SECTION 6: SAMPLE ARCHITECTURES (FOR DEMO + TESTING)

### 6.1 `bfsi_compliant.yaml` — A Compliant BFSI AI System

This should score 95+ (nearly perfect, maybe 1-2 WATCH items).

Key characteristics:
- Sector: bfsi
- Cloud: AWS ap-south-1 (Mumbai)
- All data flows stay in India
- Inference on India-based infra
- RBI-compliant data localization
- DPDP-compliant consent
- CERT-In logging in India
- No cross-border flows
- DR in India (ap-south-1 secondary AZ)

### 6.2 `saas_violation.yaml` — A SaaS with Multiple Obvious Violations

This should score 30-50 (critical non-compliance).

Key characteristics:
- Sector: saas (customer-facing AI chatbot)
- Cloud: AWS us-east-1 (primary) + ap-south-1 (secondary)
- Personal data flows to US for inference
- No consent mechanism
- No breach response pipeline
- Logging to Datadog us-east-1
- No data minimization
- Children's data processed without parental consent
- No audit logging

### 6.3 `subtle_drift.yaml` — The "Wow" Demo Architecture

This is the one that makes the room go quiet. It LOOKS compliant at first glance but has 3-4 hidden violations that a human auditor would miss:

Key characteristics:
- Sector: bfsi
- Cloud: AWS ap-south-1 (looks correct)
- All primary data flows in India (looks correct)
- BUT:
  1. **Hidden violation 1:** The RAG pipeline's Pinecone vector store has a "read replica" in us-west-2 for "latency optimization" (the architecture lists it under `vector_store_replicas: ["ap-south-1", "us-west-2"]`). This means customer data in the vector store is replicated to the US.
  2. **Hidden violation 2:** A "new" observability pipeline was added 2 weeks ago: `data_flows` includes a flow from the AI service to `Honeycomb.io (us-east-1)` with `data_types: [log_telemetry, inference_output]` and `personal_data: true` (because inference outputs contain customer names). This is RBI-007 + DPDP-004.
  3. **Hidden violation 3:** The fine-tuning pipeline sends interaction data to a "model improvement" service hosted by the vendor. The vendor's `data_location` says "India" but their `sub_processors` list includes "AWS us-east-1 (for batch processing)". This is a vendor sub-processor violation.
  4. **Hidden violation 4:** The DR copy of the payment transaction database is in `ap-southeast-1` (Singapore) for "cross-AZ redundancy" — but this is a different COUNTRY, not just a different AZ. RBI-009 violation.

The demo moment: The engine finds all 4. A human would have caught #4 at best. #1, #2, and #3 require understanding the full data lifecycle and vendor sub-processor chains.

### 6.4 `platform_ssmi.yaml` — A Large Platform (SSMI)

This tests the IT Rules 2026 + MeitY guidelines:

Key characteristics:
- 12 million users in India
- Is an intermediary
- Is SSMI
- Generates content (text + image)
- Has AI content labeling but NO provenance metadata
- Takedown SLA is 12 hours (should be 3)
- No automated filtering for CSAM
- No upload declaration
- No CCO/Nodal Contact/Grievance Officer
- No monthly compliance reports
- Bias testing not conducted
- No explainability for content ranking

---

## SECTION 7: DRIFT MONITOR (SIMULATED)

The drift monitor is a simplified simulation for the demo. It doesn't need real-time infrastructure.

### 7.1 How It Works

1. Store the "baseline" scan results (from the initial architecture)
2. Accept a "change event" (a diff to the architecture YAML)
3. Re-run the compliance scan on the modified architecture
4. Diff the findings: what's NEW? What changed status?
5. Generate alerts for new violations

### 7.2 Change Event Format

```yaml
# drift_event.yaml
timestamp: "2026-09-20T03:00:00Z"
description: "New observability pipeline added for inference monitoring"
changes:
  - type: "add_data_flow"
    data:
      id: "flow-obs-001"
      name: "Inference telemetry to Honeycomb"
      source: "ai-inference-service"
      destination: "Honeycomb.io (us-east-1)"
      data_types: ["log_telemetry", "inference_output"]
      personal_data: true
      cross_border: true
      destination_country: "USA"
      purpose: "Latency monitoring and error tracking"
      encryption: "tls_1_3"
      retention: "30 days"
      deletion_mechanism: "automatic"
```

### 7.3 Alert Format

```
╔══════════════════════════════════════════════════════════╗
║  ⚠️  SOVEREIGN AI COMPLIANCE DRIFT ALERT                ║
╠══════════════════════════════════════════════════════════╣
║  Detected: 2026-09-20 03:00 UTC                         ║
║  System: BFSI Credit Assessment AI                       ║
║                                                          ║
║  NEW VIOLATION: RBI-007 (HIGH)                           ║
║  "Inference telemetry containing customer data is being  ║
║   sent to Honeycomb.io in us-east-1 (USA)."              ║
║                                                          ║
║  NEW VIOLATION: DPDP-004 (WATCH → now CRITICAL if        ║
║   USA is ever restricted)                                ║
║  "Personal data in inference outputs is crossing         ║
║   borders without a localization mechanism."             ║
║                                                          ║
║  ACTION REQUIRED:                                        ║
║  1. Immediately disable the Honeycomb pipeline           ║
║  2. Deploy India-region observability (Datadog           ║
║     ap-south-1 or on-prem)                              ║
║  3. Purge all data already sent to Honeycomb             ║
║  4. Document the incident for RBI audit trail            ║
║                                                          ║
║  SLA: Fix within 24 hours (RBI 24-hour rule)             ║
╚══════════════════════════════════════════════════════════╝
```

---

## SECTION 8: REPORT TEMPLATES

### 8.1 Executive Summary (HTML)

```
┌─────────────────────────────────────────────────────────┐
│  SOVEREIGN AI COMPLIANCE REPORT                         │
│  [System Name] — [Organization]                         │
│  Assessment Date: [date]                                │
│  Assessor: Sovereign AI Compliance Engine v1.0          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  OVERALL SCORE: [XX]/100  [COMPLIANT / MINOR GAPS /    │
│  SIGNIFICANT GAPS / CRITICAL NON-COMPLIANCE]            │
│                                                         │
│  FINDINGS SUMMARY:                                      │
│  • CRITICAL: [N]                                        │
│  • HIGH: [N]                                            │
│  • MEDIUM: [N]                                          │
│  • LOW/WATCH: [N]                                       │
│                                                         │
│  FINANCIAL EXPOSURE: Up to ₹[X] crore                   │
│  (based on [N] violations × maximum penalty)            │
│                                                         │
│  DEADLINE URGENCY:                                      │
│  • [N] items require action before [date]               │
│  • [N] items are currently in breach                    │
│                                                         │
│  TOP 5 CRITICAL FINDINGS:                               │
│  1. [Rule ID] — [one-line description]                  │
│  2. ...                                                 │
│  3. ...                                                 │
│  4. ...                                                 │
│  5. ...                                                 │
│                                                         │
│  IMMEDIATE ACTIONS (next 72 hours):                      │
│  1. [Action]                                            │
│  2. [Action]                                            │
│  3. [Action]                                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 8.2 Regulator-Ready Report (HTML)

Full detailed report with:
- Cover page (system name, org, date, assessor)
- Table of contents
- Section 1: System identification & scope
- Section 2: Methodology (rules checked, framework version)
- Section 3: Findings (table + detailed analysis per finding)
- Section 4: Compliance score calculation (show the math)
- Section 5: Remediation plan (roadmap with timelines)
- Section 6: Attestation (signature block for Data Fiduciary)
- Appendix A: Full list of rules checked (with status)
- Appendix B: Data flow diagram (text-based)
- Appendix C: Vendor register
- Appendix D: Regulatory references

---

## SECTION 9: EDGE CASES & FAILURE MODES

The agent MUST handle these:

1. **Missing fields in the architecture:** If a field is null/missing, treat it as GAP (not COMPLIANT). "We didn't think about it" = gap.

2. **Ambiguous data types:** If a data flow says `data_types: ["misc"]` and `personal_data: true`, flag it as GAP for data classification (X-001).

3. **Vendor sub-processor chains:** If vendor A has sub-processor B, and B is in a foreign country, that's a violation even if vendor A is in India. Check the FULL chain.

4. **"Temporary" cross-border processing:** RBI's 24-hour rule means "temporary" is not an exception. If data leaves India, it must come back AND be deleted from the foreign location within 24 hours. If the architecture doesn't show a deletion mechanism, it's a violation.

5. **DR vs. Backup:** A "backup" in a foreign region is the same as a "DR copy" in a foreign region. Both violate RBI-009 for regulated data. Don't let the label fool you.

6. **Inference vs. Training:** Both are subject to localization. "We only do inference in India, training is in the US" is a violation if the training data contains Indian personal data (RBI-004, DPDP-001).

7. **Aggregated/derived data:** RBI-010 explicitly covers "aggregated but still derived data." If you aggregate customer transactions and send the aggregate to a global analytics platform, it's still a violation.

8. **Multi-region deployments:** If the primary is in India but there's a "read replica" in another country for "performance," the data has crossed borders. It's a violation for regulated data.

9. **Consent for AI training specifically:** General consent for "service use" does NOT cover AI training. The consent must be specific to the AI use case. If the architecture says `consent_obtained: true` but `consent_mechanism: "terms_of_service"`, that's a GAP (not specific enough).

10. **The "we'll fix it later" problem:** If a violation is identified, the remediation must be specific and time-bound. "Plan to migrate to India region in Q3" is not a valid remediation for an active RBI violation.

---

## SECTION 10: DEMO SCRIPT

The demo should follow this exact sequence:

### Act 1: The Setup (2 min)
- Show the `subtle_drift.yaml` architecture
- "This is a BFSI credit assessment AI system. On the surface, it looks compliant. All primary infrastructure is in Mumbai. Let's see what the engine finds."

### Act 2: The Scan (3 min)
- Run the engine
- Watch it parse the architecture
- Watch it go rule by rule (show the terminal output)
- It finds 4 violations (the hidden ones)
- Highlight each one as it's found:
  - "Found: Vector store replica in us-west-2. Customer data in RAG pipeline is replicated to the US. RBI-001 + DPDP-004."
  - "Found: Inference telemetry flowing to Honeycomb us-east-1. Contains customer names in inference outputs. RBI-007."
  - "Found: Vendor sub-processor in us-east-1 for batch processing. Customer interaction data leaves India via vendor chain. RBI-004."
  - "Found: DR copy in ap-southeast-1 (Singapore). Payment transaction data replicated to a foreign country. RBI-009."

### Act 3: The Report (2 min)
- Show the generated report
- Compliance score: 42/100 (Critical Non-Compliance)
- Financial exposure: Up to ₹500 crore (2 CRITICAL × ₹250Cr max)
- Remediation roadmap

### Act 4: The Drift (2 min)
- "Now, it's 3 days later. The team added a new feature: A/B testing via Optimizely (US-based)."
- Inject the drift event
- Re-run the scan
- New violation appears: "A/B testing platform receiving user behavioral data in US. DPDP-004 + RBI-007."
- Alert fires

### Act 5: The Close (1 min)
- "This is what a $500K consulting engagement takes 6 weeks to do. This engine does it in 90 seconds. And it catches the things humans miss — the sub-processor chains, the vector replicas, the telemetry pipelines."
- "Every bank, every insurance company, every SaaS in India that ships AI needs this. The regulatory deadline is May 2027. They have 8 months."

---

## SECTION 11: QUALITY GATES (DEFINITION OF DONE)

The build is NOT done until ALL of the following pass:

- [ ] All 80+ rules from Section 1 are encoded in the knowledge base JSON files
- [ ] The agent correctly identifies ALL violations in `subtle_drift.yaml` (4/4)
- [ ] The agent correctly identifies ALL violations in `saas_violation.yaml` (8+ violations)
- [ ] The agent gives `bfsi_compliant.yaml` a score of 90+ (no false positives on critical rules)
- [ ] The report generates valid HTML (opens in browser, is readable)
- [ ] The drift monitor correctly detects the injected change
- [ ] The terminal output is clean and readable (not a wall of text)
- [ ] `demo.sh` runs the full demo end-to-end without errors
- [ ] `pytest` passes (all test cases)
- [ ] The README explains how to run the system in < 5 steps
- [ ] The system handles a malformed YAML gracefully (error message, not crash)

---

## SECTION 12: BUILD ORDER (WORK IN THIS SEQUENCE)

1. **Knowledge base** (2-3 hours): Create all JSON rule files. This is the foundation. Get every rule from Section 1 encoded with precise `check_logic`.
2. **Input schema + samples** (1 hour): Create the YAML schema and all 4 sample architectures.
3. **Agent core** (3-4 hours): Build the compliance agent with the tool definitions and phase prompts. Test with `saas_violation.yaml` first (obvious violations, easy to verify).
4. **Report generator** (2 hours): Build the HTML report templates and scoring logic.
5. **Drift monitor** (1-2 hours): Build the simulated drift detection.
6. **Dashboard** (1-2 hours, optional): Streamlit app that shows the compliance score, findings table, and remediation roadmap.
7. **Demo script** (1 hour): Write `demo.sh` and the demo narrative.
8. **Testing + polish** (2 hours): Run all test cases, fix edge cases, clean up output.

**Total estimated build time: 12-16 hours of focused work.**

---

## SECTION 13: CRITICAL REMINDERS

- **Do NOT hallucinate regulations.** Only use the rules explicitly defined in Section 1. If you're unsure whether a rule exists, mark it as WATCH with a note "verify current status."
- **Do NOT be lenient.** "It's probably fine" is not a valid assessment. If the architecture doesn't explicitly demonstrate compliance, it's a GAP.
- **Do NOT miss the hidden stuff.** The whole point of this engine is to find what humans miss. Vector replicas, sub-processor chains, telemetry pipelines, DR in "neighboring" countries — these are the high-value findings.
- **Be specific in remediation.** "Implement data localization" is useless. "Move Pinecone from us-west-2 to ap-south-1, update config/vector_store.yaml line 14, run migration script, verify no cross-region replication" is useful.
- **The demo is everything.** The technical depth is for the judges who dig in. The demo is for the 30 seconds that decide your score. Make it visceral.
```

---

This is your complete build spec. A few practical notes:

**How to use it:** Paste the entire markdown as Claude's task prompt. If you're using the Claude Agent SDK, this becomes your system prompt + the first user message. If you're using the API directly, feed it as the system prompt and then say "Begin Phase 1."

**Token budget:** This spec is ~12K tokens. The knowledge base JSON files will add another ~8-10K. Each scan run will burn 5-15K tokens depending on architecture complexity. For an overnight build with multiple iterations, budget **200K-500K tokens** total.

**The single most important file to get right:** `subtle_drift.yaml`. If the engine catches all 4 hidden violations in that file, you win. Build the knowledge base and agent around that test case first, then expand.

