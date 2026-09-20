# AI Compliance Compiler — Full Build Instructions

## 0. Mission

Build a production-quality MVP of an **AI Compliance Compiler** for Indian organizations deploying AI systems.

The product is NOT a generic chatbot that summarizes regulations and NOT a static compliance-report generator.

The core product thesis is:

> **Translate an actual AI system architecture and runtime configuration into applicable regulatory obligations, concrete technical/organizational controls, evidence requirements, remediation actions, and continuous drift alerts.**

Think of the system as a compiler:

```text
AI SYSTEM / ARCHITECTURE
        ↓
SYSTEM UNDERSTANDING
        ↓
DATA / MODEL / VENDOR / REGION GRAPH
        ↓
APPLICABILITY ENGINE
        ↓
REGULATION → REQUIREMENT → CONTROL MAPPING
        ↓
EVIDENCE CHECK
        ↓
GAP DETECTION
        ↓
REMEDIATION PLAN
        ↓
CONTINUOUS DRIFT MONITORING
```

The MVP must make the above loop demonstrably real.

Do not build a visually impressive shell around fake AI compliance. Every major screen must be backed by actual data structures, deterministic logic where appropriate, and traceable evidence.

---

# 1. Critical Product Positioning

Do NOT position the product as:

- “India’s first AI compliance platform.”
- “A fully autonomous legal advisor.”
- “A tool that guarantees compliance.”
- “An AI that decides whether a company is legally compliant.”
- “A replacement for lawyers, auditors, or regulators.”

Position it as:

> **An engineering-to-compliance control plane for AI systems.**

Primary value proposition:

> **Know what AI you actually have, which rules apply, what controls are missing, and what changed since your last review.**

The differentiator is not merely regulation search. The differentiator is the connection between:

```text
code / infrastructure / data flows
             ↕
        AI system graph
             ↕
       regulatory graph
             ↕
         controls
             ↕
          evidence
             ↕
        remediation
             ↕
         monitoring
```

---

# 2. Important Regulatory Accuracy Rules

The product must be designed around **versioned regulatory knowledge**, not hard-coded assumptions.

As of September 20, 2026, the authoritative baseline must include at minimum:

1. Digital Personal Data Protection Act, 2023.
2. Digital Personal Data Protection Rules, 2025.
3. Applicable commencement/enforcement timeline for provisions that are in force at the time of analysis.
4. CERT-In directions relevant to covered entities and systems.
5. RBI AI governance material relevant to regulated entities, including the 2025 FREE-AI Committee Report, while explicitly distinguishing recommendations/framework material from binding directions.
6. IndiaAI / MeitY AI governance material that is applicable or guidance-oriented, with status clearly labeled.
7. Sector-specific rules where the demo organization falls into a regulated sector.

Do NOT claim that:

> “Indian law requires all AI data to remain in India.”

That is too broad. The product must distinguish:

- explicit localization/Indian-jurisdiction requirements,
- transfer restrictions,
- sector-specific requirements,
- contractual requirements,
- internal policy restrictions,
- and architecture preferences that are not themselves statutory obligations.

For every requirement, store its legal status:

```text
BINDING_LAW
BINDING_RULE
REGULATORY_DIRECTION
REGULATOR_EXPECTATION
FORMAL_FRAMEWORK
GUIDANCE
BEST_PRACTICE
INTERNAL_POLICY
```

Never merge these into a single generic “law” label.

Every generated finding must include:

- source title,
- issuing authority,
- version/date,
- jurisdiction,
- exact source URL,
- relevant section/rule/paragraph reference where available,
- applicability reasoning,
- confidence,
- whether the finding is legal interpretation or engineering inference.

The LLM must NEVER invent a section number.

If the system cannot prove a citation, it must say:

> `Citation not verified — human review required.`

---

# 3. Current Authoritative Sources To Seed

Use authoritative first-party sources as the primary corpus.

### MeitY / Government of India

DPDP Act 2023:
https://www.meity.gov.in/writereaddata/files/Digital%20Personal%20Data%20Protection%20Act%202023.pdf

DPDP Rules 2025:
https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digit

MeitY Acts and Policies:
https://www.meity.gov.in/documents/act-and-policies

IndiaAI AI-governance material:
https://indiaai.gov.in/

### RBI

FREE-AI Committee Report:
https://m.rbi.org.in/Scripts/BS_ViewPublicationReport.aspx

RBI home / regulatory publications:
https://www.rbi.org.in/

### CERT-In

CERT-In Directions under Section 70B:
https://www.cert-in.org.in/Directions70B.jsp

CERT-In Directions PDF:
https://cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf

These URLs are seed sources, not a substitute for a maintainable source registry. Build the source layer so URLs, documents, versions, and status can be updated without code changes.

---

# 4. Competitive Reality — Do Not Build a Fake Moat

There are already mature AI governance / GRC vendors with capabilities including AI inventory, regulatory mapping, risk assessment, monitoring, policy controls and audit evidence.

Examples that must be treated as existing competition / adjacent competition:

- OneTrust AI Governance
- Credo AI
- Holistic AI
- enterprise GRC platforms
- privacy-management platforms
- AI security / posture-management tools
- consulting-led compliance tooling

Therefore the MVP must NOT claim that the category itself is empty.

The working strategic wedge is:

> **India-first, engineering-connected, regulation-versioned compliance compilation for actual AI architecture, with explicit evidence lineage and change/drift detection.**

Potential later moat:

1. high-fidelity architecture graph,
2. India-specific regulatory control packs,
3. source-to-control provenance,
4. change-impact engine,
5. engineering integrations,
6. historical compliance state,
7. machine-readable remediation,
8. eventually policy-as-code / CI gates.

Do not attempt to beat OneTrust/Credo/Holistic on breadth in the MVP.

---

# 5. Target Customer For MVP

Do not attempt to serve every company.

Target:

> **Indian technology companies and regulated enterprises with production or pre-production AI systems, especially teams with security, privacy, compliance, engineering, or risk responsibilities.**

Best initial personas:

- CISO / security lead
- privacy / DPO-equivalent function
- AI governance lead
- risk/compliance manager
- platform engineering lead
- CTO / technical founder
- internal audit / technology risk

The MVP user journey should take less than 15 minutes to create a first assessment from a sample architecture.

---

# 6. Core User Story

The demo organization has this architecture:

```text
Customer Web App
      ↓
Application API
      ↓
PostgreSQL (customer records)
      ↓
RAG service
   ↙       ↘
Vector DB   External LLM API
              ↓
        Generated response
```

The company tells the system:

- customer data exists,
- the AI processes support conversations,
- production users are in India,
- some processing is performed by an external AI provider,
- the system uses a third-party analytics service,
- employees can access logs,
- retention is configured for 180 days.

The application should generate a graph and identify relevant questions/findings such as:

- What personal data categories are processed?
- What is the purpose of processing?
- What legal basis / permitted purpose is being relied upon, where applicable?
- What notices / transparency mechanisms are required?
- Who are the data processors / service providers?
- Where does data leave the organization and through which vendors?
- What retention controls exist?
- What access controls exist?
- What evidence proves the control is operating?
- Which obligations apply based on sector and system context?
- Which recommendations are governance guidance rather than binding law?

The output must be traceable, not a magic “72% compliant” number.

---

# 7. Do NOT Use a Single Compliance Score as the Primary Output

Avoid a simplistic:

> `Compliance Score = 73%`

This looks impressive but is legally and technically weak.

Instead provide:

### Findings by severity

```text
CRITICAL
HIGH
MEDIUM
LOW
INFO
```

And every finding contains:

```text
Finding
Why it matters
Applicable source
Applicability reasoning
Observed evidence
Missing evidence
Required control
Suggested remediation
Owner
Status
Confidence
Last verified
```

If you expose a high-level posture indicator, call it something like:

> `Control coverage`

and explicitly explain what it measures.

---

# 8. Product Modules

Build the following modules.

## 8.1 Workspace

Organization profile:

- organization name
- country
- sectors
- operating regions
- regulated status
- company size
- AI governance maturity
- internal policies

The organization profile drives applicability.

Example:

```json
{
  "country": "IN",
  "sectors": ["fintech"],
  "regulated_entities": ["RBI"],
  "data_subjects": ["customers", "employees"],
  "ai_use_cases": ["customer_support", "fraud_detection"]
}
```

---

## 8.2 AI System Inventory

Every AI system becomes a first-class entity.

Fields:

```text
system_id
name
owner
business_purpose
risk_domain
lifecycle_stage
status
sector
users
regions
models
agents
data_sources
data_categories
vendors
endpoints
repositories
deployment_environment
last_reviewed
last_changed
```

Lifecycle:

```text
IDEA
DEVELOPMENT
TESTING
PILOT
PRODUCTION
DEPRECATED
RETIRED
```

---

# 9. Architecture Ingestion

This is the most important technical differentiator of the MVP.

Support at least three ingestion methods.

### A. Structured JSON/YAML import

Provide a clear schema such as:

```yaml
system:
  name: Support Copilot
  purpose: Customer support
  environment: production

data:
  - name: customer_profile
    category: personal_data
    region: India
    storage: postgres-prod

models:
  - name: support-rag-model
    provider: external_llm
    region: us

services:
  - name: vector-db
    type: database
    region: India

flows:
  - from: postgres-prod
    to: external_llm
    data_categories:
      - customer_profile
```

### B. Architecture file upload

Accept simple:

- JSON
- YAML
- Terraform plan/output where practical
- architecture diagram metadata

### C. Guided architecture builder

Allow a user to manually create:

- system
- model
- data store
- API
- vendor
- region
- data flow

Do NOT attempt a giant enterprise discovery engine overnight.

---

# 10. Architecture Graph

Represent architecture as a graph.

Node types:

```text
AI_SYSTEM
MODEL
AGENT
DATASET
DATA_STORE
DATA_CATEGORY
API
VENDOR
SERVICE
USER_GROUP
REGION
COUNTRY
CONTROL
REGULATION
REQUIREMENT
EVIDENCE
INCIDENT
POLICY
OWNER
```

Edge types:

```text
PROCESSES
STORES
SENDS_TO
HOSTED_BY
OPERATED_BY
ACCESSED_BY
GENERATES
DEPENDS_ON
APPLIES_TO
SATISFIED_BY
EVIDENCED_BY
VIOLATES
REMEDIATED_BY
OWNED_BY
```

A relational database can back this graph for MVP; do not prematurely introduce Neo4j unless it materially simplifies the build.

PostgreSQL tables + graph-style edge tables are acceptable.

---

# 11. Regulatory Knowledge Graph

Each regulation is stored as versioned structured data.

Schema:

```text
regulation
regulation_version
source_document
requirement
applicability_rule
control
control_mapping
citation
status
jurisdiction
sector
risk_domain
last_verified
```

Example:

```json
{
  "requirement_id": "DPDP-EXAMPLE-001",
  "title": "Example requirement",
  "status": "BINDING_LAW",
  "jurisdiction": "IN",
  "sector": "general",
  "source": "DPDP Act 2023",
  "citation": "section X",
  "applies_when": [
    "digital_personal_data_processed"
  ],
  "controls": [
    "CTRL-001",
    "CTRL-002"
  ]
}
```

Do not create fake legal requirements merely to populate the demo.

Where exact legal mapping requires expert interpretation, mark the mapping:

```text
LEGAL_MAPPING_CONFIDENCE = REVIEW_REQUIRED
```

---

# 12. Requirement Applicability Engine

This is where the product becomes more than a document summarizer.

Input:

```text
organization profile
+
AI system architecture
+
data flows
+
sector
+
region
+
vendors
+
processing activities
```

Output:

```text
applicable requirements
potentially applicable requirements
not applicable requirements
unknown / needs review
```

Every decision needs a machine-readable explanation.

Example:

```text
Requirement: R-013
Status: POTENTIALLY_APPLICABLE
Reason:
- System processes personal data
- Organization operates in India
- System is deployed in production

Open questions:
- confirm data-subject relationship
- confirm processing purpose
- confirm applicability of sector-specific rules
```

Never silently turn unknown facts into assumptions.

---

# 13. Control Library

Controls should be engineering-operational, not vague sentences.

Bad:

> “Ensure adequate security.”

Good:

> “Production AI endpoint authentication is enforced using a centrally managed identity mechanism, and requests are attributable to a service/user identity.”

Control attributes:

```text
control_id
name
description
control_type
owner
implementation_examples
evidence_types
automation_possible
applicable_requirements
verification_method
status
```

Control types:

```text
PRIVACY
SECURITY
ACCESS
DATA_GOVERNANCE
MODEL_GOVERNANCE
VENDOR
RETENTION
AUDIT
INCIDENT
HUMAN_OVERSIGHT
TRANSPARENCY
CHANGE_MANAGEMENT
```

---

# 14. Evidence Engine

A compliance assertion without evidence is weak.

For each control, the platform asks:

> **What evidence proves this control exists and is operating?**

Evidence types:

- architecture configuration
- source code
- CI/CD configuration
- cloud configuration
- policy document
- access-control export
- database configuration
- log sample
- ticket
- approval
- model card
- vendor agreement
- screenshot
- test result
- signed attestation

Evidence object:

```text
id
type
source
owner
created_at
valid_from
valid_until
hash
linked_control
linked_system
verification_status
```

Do not allow an LLM-generated narrative to count as independent evidence.

---

# 15. Gap Detection

The engine compares:

```text
APPLICABLE REQUIREMENT
        ↓
REQUIRED CONTROL
        ↓
OBSERVED CONTROL STATE
        ↓
AVAILABLE EVIDENCE
```

Possible results:

```text
SATISFIED
PARTIALLY_SATISFIED
NOT_SATISFIED
NO_EVIDENCE
UNKNOWN
NOT_APPLICABLE
```

Example:

```text
Requirement
   ↓
CTRL-017: external data-processing vendor inventory
   ↓
Vendor OpenAI detected
   ↓
No vendor record found
   ↓
Finding: NO_EVIDENCE
```

---

# 16. Remediation Engine

Every meaningful gap should produce an actionable remediation.

The remediation must have:

```text
finding
recommended_action
technical_steps
policy_steps
owner_type
priority
estimated_effort
verification_method
rollback_notes
```

Example:

```text
Finding:
External AI provider detected but no data-transfer classification exists.

Suggested remediation:
1. Classify data sent to provider.
2. Confirm provider location and subprocessors.
3. Confirm contractual/privacy requirements.
4. Add data-flow record.
5. Re-run applicability analysis.

Verification:
Inspect API gateway request schema + provider contract metadata.
```

Avoid pretending the system can provide definitive legal advice.

---

# 17. Continuous Drift Monitoring

This is a core differentiator.

Create a simulated event stream for the MVP.

Examples:

```text
MODEL_PROVIDER_CHANGED
REGION_CHANGED
NEW_VENDOR_ADDED
NEW_DATA_CATEGORY_DETECTED
NEW_API_ENDPOINT
DATA_RETENTION_CHANGED
ACCESS_POLICY_CHANGED
NEW_MODEL_VERSION
RAG_SOURCE_ADDED
LOGGING_DISABLED
PRODUCTION_DEPLOYMENT
```

When an event occurs:

1. determine affected architecture nodes,
2. determine affected controls,
3. determine affected requirements,
4. recalculate findings,
5. generate a human-readable impact statement,
6. create a remediation task if necessary.

Example:

```text
CHANGE DETECTED

Support Copilot
External LLM provider changed
US endpoint introduced

Potential impact:
3 requirements
2 controls
1 evidence item

Action:
Review cross-border data-flow implications.
```

Do not state “this violates Indian law” unless the mapping is actually supported by the knowledge base and the applicability logic.

Prefer:

> “Potential compliance impact detected — review required.”

---

# 18. Regulation Change Monitoring

Separate from infrastructure drift.

A regulation source can change.

The system should support:

```text
old regulation version
        ↓
new regulation version
        ↓
changed requirements
        ↓
affected controls
        ↓
affected AI systems
```

Example:

```text
REGULATION UPDATE
DPDP Rules 2025 → v2

Affected:
7 controls
3 systems
2 vendors

Priority review:
Support Copilot
Customer Analytics
HR Assistant
```

For MVP, implement this using manually seeded versioned documents/diffs if live crawling is too risky.

Do NOT rely entirely on uncontrolled web scraping for legal truth.

---

# 19. LLM Responsibilities

Use the LLM for:

- extracting architecture information from natural language,
- classifying data categories,
- mapping architecture descriptions into known ontology entities,
- explaining findings,
- producing remediation drafts,
- summarizing regulatory text,
- finding candidate mappings.

Do NOT use the LLM as the sole authority for:

- whether a law applies,
- whether a company is legally compliant,
- whether a citation exists,
- legal section numbering,
- final regulatory interpretation.

The architecture should be:

```text
LLM proposal
      ↓
structured candidate
      ↓
deterministic validation
      ↓
source-backed knowledge base
      ↓
final finding
```

The LLM is the analyst/copilot, not the legal source of truth.

---

# 20. Retrieval Architecture

Implement RAG properly.

Pipeline:

```text
SOURCE DOCUMENT
    ↓
extract text
    ↓
segment by logical provision
    ↓
store metadata
    ↓
embeddings + lexical index
    ↓
retrieve candidate provisions
    ↓
LLM synthesis
    ↓
citation validation
    ↓
structured requirement output
```

Metadata must include:

```text
source_id
source_title
issuer
jurisdiction
document_date
version
section
paragraph/page if available
status
url
```

Do not rely only on vector similarity. Use hybrid retrieval:

- lexical search,
- metadata filters,
- semantic search.

---

# 21. Database Design

Use PostgreSQL.

Minimum tables:

```text
organizations
users
ai_systems
models
agents
data_assets
data_categories
data_stores
vendors
services
regions
architecture_nodes
architecture_edges
regulations
regulation_versions
requirements
applicability_rules
controls
requirement_controls
controls_evidence
evidence
findings
remediations
change_events
subscriptions
source_documents
source_chunks
audit_events
```

Use foreign keys and indexes.

All important state changes require timestamps.

Use soft deletion for governance objects where practical.

---

# 22. API Design

Implement clean REST or typed RPC endpoints.

Minimum endpoints:

```text
POST /organizations
POST /systems
POST /systems/import
GET  /systems/:id
GET  /systems/:id/graph
POST /systems/:id/analyze
GET  /systems/:id/findings
GET  /systems/:id/controls
GET  /systems/:id/evidence
POST /systems/:id/events
POST /regulations/import
GET  /regulations
GET  /requirements
POST /findings/:id/remediate
GET  /dashboard
```

Do not expose raw database operations to the frontend.

---

# 23. Frontend Information Architecture

Use a serious enterprise product UI.

Pages:

### Dashboard

Show:

- AI systems
- high-priority findings
- unresolved controls
- architecture changes
- regulation changes
- evidence coverage

### AI Estate

Table of systems with:

- owner
- stage
- risk domain
- last review
- current finding count
- last architecture change

### System Detail

This is the hero page.

Show:

1. system overview,
2. architecture graph,
3. data flows,
4. applicable requirements,
5. control status,
6. evidence,
7. findings,
8. change history.

### Finding Detail

Show the complete reasoning chain:

```text
Observed architecture
      ↓
Why this requirement applies
      ↓
Source citation
      ↓
Control expected
      ↓
Evidence found
      ↓
Evidence missing
      ↓
Remediation
```

### Regulations

Show source/version/status.

### Change Monitor

Timeline of architecture and regulatory changes.

---

# 24. Hero Demo Scenario

Build ONE extremely polished demo around a fictional Indian fintech.

Company:

```text
FinServe Technologies Pvt. Ltd.
```

System:

```text
Customer Support Copilot
```

Architecture:

```text
Web App
   ↓
API Gateway
   ↓
Support Backend
   ↓
Customer PostgreSQL
   ↓
RAG Service
   ├── India-hosted Vector DB
   └── External LLM API
           ↓
        US endpoint
```

Data:

```text
name
email
account metadata
support conversations
transaction-related context
```

Seed several deliberately problematic but plausible configuration states.

Example states:

1. External vendor not entered into vendor registry.
2. Data-flow classification missing.
3. Retention evidence missing.
4. Access review evidence outdated.
5. New external model endpoint added.
6. AI system owner not assigned.
7. Production system missing documented review state.

The engine should discover these as **control/evidence gaps**, not invent a legal violation.

---

# 25. The “Aha” Demo

The demo must be understandable in under 90 seconds.

Sequence:

### Step 1
Import architecture.

### Step 2
System renders graph.

### Step 3
Click:

> `Analyze Compliance`

### Step 4
The system produces:

```text
Applicable requirements: 14
Controls evaluated: 31
Evidence items: 19
Open findings: 7
High priority: 2
```

These numbers are generated from real seeded entities.

### Step 5
Click one finding.

Show:

```text
OBSERVATION
External LLM endpoint detected in US.

CONTEXT
Customer support data may be transmitted to this service.

RELEVANT REQUIREMENT
[authoritative source + section]

CONTROL
Document and govern the applicable data flow / transfer controls.

EVIDENCE
No verified data-flow record found.

REMEDIATION
[concrete steps]
```

### Step 6
Trigger a simulated architecture event:

```text
External LLM provider changed.
```

The product immediately shows:

```text
Impact detected
3 controls affected
2 findings reopened
1 system requires re-review
```

That is the money shot.

---

# 26. Security Requirements

Even for an MVP, do not build an insecure toy.

Minimum:

- password hashing / secure auth provider,
- session management,
- RBAC,
- organization isolation,
- server-side authorization on every organization-scoped request,
- encrypted secrets,
- no API keys exposed to frontend,
- audit log for changes,
- input validation,
- file upload restrictions,
- malware/file-type checks where practical,
- rate limiting on expensive analysis endpoints,
- secure error messages.

Roles:

```text
OWNER
ADMIN
ANALYST
VIEWER
```

Tenant isolation must be tested.

---

# 27. Auditability

Every AI-generated assessment should be reproducible.

Store:

```text
analysis_id
system_id
timestamp
knowledge_base_version
prompt_version
model_name
retrieved_source_ids
rule_engine_version
output_hash
review_status
```

If a finding changes later, the old finding must remain in history.

This is crucial for compliance software.

---

# 28. Knowledge Base Versioning

This is non-negotiable.

Never overwrite a regulation silently.

Use:

```text
source v1
source v2
source v3
```

And map analyses to a specific knowledge snapshot.

The UI must show:

> `Analysis performed against Regulatory Pack: India AI Compliance Pack v0.3 — 20 Sep 2026`

---

# 29. “Human Review Required” System

Introduce explicit review states.

```text
AI_DRAFT
ANALYST_REVIEW
LEGAL_REVIEW
APPROVED
REJECTED
EXPIRED
```

A high-impact regulatory finding should never become “approved” automatically.

The app should make it easy for a human reviewer to:

- accept,
- reject,
- modify,
- add rationale,
- attach evidence,
- assign an owner.

---

# 30. No Hallucinated Compliance

Build automatic validation rules.

Before displaying a requirement:

```text
Does source_document exist?
Does citation exist?
Does retrieved source contain citation?
Does requirement have status?
Does applicability rule exist?
```

If any fail:

```text
UNVERIFIED — HUMAN REVIEW REQUIRED
```

Do not fabricate confidence scores merely for aesthetics.

---

# 31. Policy-as-Code Direction

Architect the system so controls can eventually become machine-evaluable policies.

Example:

```yaml
policy:
  id: external_ai_data_flow_review
  applies_when:
    data_category: personal_data
    destination_type: external_llm
  expected:
    vendor_registered: true
    data_flow_documented: true
    approved_destination: true
```

This enables the future product to integrate with:

- CI/CD
- Terraform
- API gateways
- cloud configuration
- service meshes
- DLP
- logging
- SIEM

Do not build all of these integrations now. Build the policy representation so they are possible later.

---

# 32. CI/CD Future Mode

Design a future flow like:

```text
Developer changes model provider
        ↓
Pull request
        ↓
Compliance Compiler
        ↓
Policy evaluation
        ↓
Potential impact
        ↓
PASS / REVIEW / BLOCK
```

MVP should simulate this with an “Import change” action.

---

# 33. AI Agent Support

Do not make agents the entire MVP, but design the ontology to support them.

Agent fields:

```text
name
model
instructions
tools
permissions
memory
external_actions
human_approval_points
execution_environment
```

Later, this enables governance of:

- customer-support agents,
- coding agents,
- procurement agents,
- internal workflow agents.

The important distinction is that an agent can **act**, not just generate text.

---

# 34. UX Rules

The interface must feel like enterprise infrastructure, not a hackathon dashboard.

Avoid:

- excessive gradients,
- giant “AI” labels,
- cartoon illustrations,
- fake futuristic animations,
- meaningless scorecards,
- endless chat UI.

Prefer:

- clean tables,
- compact status indicators,
- evidence chains,
- dependency graphs,
- change timelines,
- strong typography,
- precise language.

The hero visual should be the **architecture → requirement → control → evidence graph**.

---

# 35. Suggested Technical Stack

Use a stack optimized for fast reliable execution.

Recommended:

### Frontend

- Next.js
- TypeScript
- Tailwind
- shadcn/ui
- React Flow for graph visualization
- TanStack Query

### Backend

Either:

- Next.js API routes for a smaller MVP,

or:

- FastAPI + Python if the rules/RAG layer is more naturally Python-based.

### Database

- PostgreSQL
- pgvector if available

### RAG

- hybrid BM25/full-text + embeddings
- pgvector is acceptable for MVP

### LLM

Use whichever high-quality model endpoint is already configured for the development environment.

Abstract the provider behind a service interface:

```text
LLMProvider
  ├── OpenAI
  ├── Anthropic
  └── Gemini
```

Do not hard-code one model throughout the app.

### Background jobs

Use a simple job abstraction.

Do not introduce Kafka unless genuinely necessary.

---

# 36. Repository Structure

Use a clean monorepo or clean full-stack structure.

Example:

```text
/apps/web
/apps/api
/packages/domain
/packages/rules
/packages/knowledge
/packages/llm
/packages/ui
/packages/types
/scripts/seed
```

Important modules:

```text
/domain/architecture
/domain/regulation
/domain/control
/domain/evidence
/domain/finding
/domain/change
/rules/applicability
/rules/evaluation
/knowledge/sources
/knowledge/retrieval
/llm/extraction
/llm/explanation
```

---

# 37. Seed Data

The MVP must ship with realistic seed data.

Create:

### Organization

FinServe Technologies Pvt. Ltd.

### Systems

1. Customer Support Copilot
2. Fraud Detection Model
3. HR Screening Assistant

### Vendors

- external LLM provider
- vector database provider
- analytics provider
- cloud provider

### Data categories

- identity data
- contact information
- support conversation data
- transaction context
- employee data

### Findings

Create enough real graph relationships that the dashboard is meaningful.

---

# 38. Automated Tests

Write tests for:

### Applicability

- personal-data system → relevant DPDP pack candidates
- non-personal system → DPDP-specific data processing requirements should not automatically apply
- fintech organization → RBI pack candidates
- non-RBI organization → RBI-only requirements should not automatically apply

### Graph

- architecture nodes create expected edges
- data flow is traversable
- vendor changes propagate to dependent controls

### Evidence

- missing evidence produces NO_EVIDENCE
- valid evidence changes state
- expired evidence becomes stale

### Drift

- provider change re-evaluates affected findings
- region change re-evaluates affected flows
- data category change re-evaluates applicability

### Security

- tenant isolation
- RBAC
- unauthorized access rejected

### Citations

- unverified citation never appears as verified

---

# 39. Acceptance Criteria

The project is successful only if all of these are true.

## Functional

- [ ] User can create organization.
- [ ] User can create/import AI system.
- [ ] User can define architecture.
- [ ] Architecture renders as graph.
- [ ] Regulatory knowledge is versioned.
- [ ] Requirements have explicit source metadata.
- [ ] Applicability engine produces structured results.
- [ ] Controls map to requirements.
- [ ] Evidence maps to controls.
- [ ] Findings are generated from actual graph state.
- [ ] Remediation can be created.
- [ ] Architecture change event triggers re-analysis.
- [ ] Regulation version change can trigger impact analysis.
- [ ] Human review workflow exists.
- [ ] Audit history exists.

## Product

- [ ] New user can understand the product without a tutorial.
- [ ] First analysis takes under 15 minutes.
- [ ] Demo produces an obvious “aha”.
- [ ] No fake compliance score dominates the UX.
- [ ] Every important finding has evidence/citation lineage.

## Technical

- [ ] Tests pass.
- [ ] No major TypeScript errors.
- [ ] No unresolved critical runtime errors.
- [ ] DB migrations are reproducible.
- [ ] Environment variables are documented.
- [ ] Seed script works from a clean DB.
- [ ] Docker/dev setup works.
- [ ] Production build works.

## Trust

- [ ] No fabricated law.
- [ ] No fabricated citation.
- [ ] No claim of legal guarantee.
- [ ] Guidance/recommendation is distinguished from binding law.
- [ ] Current knowledge base version is visible.
- [ ] Human-review state is visible.

---

# 40. What NOT To Build Overnight

Do not waste time implementing:

- 50+ integrations,
- enterprise SSO/SAML,
- billing,
- marketplace,
- mobile app,
- custom LLM training,
- autonomous legal-agent mode,
- full SIEM integrations,
- full Terraform scanning,
- complete cloud posture management,
- every Indian regulation,
- every sector,
- international regulation packs,
- blockchain audit trails,
- fancy analytics.

The MVP needs one excellent closed loop.

---

# 41. The Closed Loop That Must Work

The entire overnight project should make this loop work end-to-end:

```text
IMPORT AI ARCHITECTURE
        ↓
BUILD SYSTEM GRAPH
        ↓
IDENTIFY DATA / VENDORS / REGIONS
        ↓
APPLY INDIA REGULATORY PACK
        ↓
MAP REQUIREMENTS
        ↓
MAP CONTROLS
        ↓
CHECK EVIDENCE
        ↓
CREATE FINDINGS
        ↓
GENERATE REMEDIATION
        ↓
TRIGGER ARCHITECTURE CHANGE
        ↓
RE-RUN IMPACT ANALYSIS
        ↓
SHOW EXACTLY WHAT CHANGED
```

If this loop works beautifully, the MVP is valid.

---

# 42. Development Execution Order

Execute in this order.

## Phase 1 — Foundation

- initialize repository
- install dependencies
- configure DB
- define environment variables
- create migrations
- create shared domain types

## Phase 2 — Domain Model

Implement:

- organizations
- AI systems
- architecture nodes/edges
- regulations
- requirements
- controls
- evidence
- findings
- change events

## Phase 3 — Knowledge Base

- import authoritative seed documents
- create normalized requirement records
- create citations
- tag legal status
- create applicability conditions
- create control mappings

## Phase 4 — Analysis Engine

Build deterministic engine first.

Then add LLM augmentation.

Do not reverse this order.

## Phase 5 — Frontend

Build:

- dashboard
- estate
- system detail
- graph
- findings
- evidence
- regulation page
- change monitor

## Phase 6 — Demo

Seed FinServe.

Create the full end-to-end scenario.

## Phase 7 — Testing

Run unit, integration and security tests.

## Phase 8 — Polish

Fix UX, copy, empty states, loading states, errors and visual hierarchy.

---

# 43. Analysis Engine Architecture

Use this conceptual pipeline.

```python
architecture = ingest_architecture(input)

facts = normalize_architecture(architecture)

candidates = retrieve_regulatory_requirements(
    org_context,
    facts
)

applicable = applicability_engine.evaluate(
    org_context,
    facts,
    candidates
)

controls = control_mapper.map(applicable)

evidence_state = evidence_engine.evaluate(
    controls,
    available_evidence
)

findings = gap_engine.evaluate(
    applicable,
    controls,
    evidence_state
)

findings = citation_validator.verify(findings)

remediations = remediation_engine.generate(findings)

persist_analysis_snapshot(...)
```

The same pipeline must be callable after a change event.

---

# 44. Change Impact Engine

For an incoming event:

```json
{
  "type": "MODEL_PROVIDER_CHANGED",
  "system_id": "support-copilot",
  "old_value": "ProviderA",
  "new_value": "ProviderB",
  "timestamp": "..."
}
```

Compute:

```text
affected nodes
affected edges
affected data flows
affected requirements
affected controls
affected evidence
affected findings
```

Show the dependency chain in the UI.

Example:

```text
MODEL PROVIDER CHANGE
        ↓
EXTERNAL DATA PROCESSING PATH
        ↓
CONTROL CTRL-014
        ↓
EVIDENCE E-991
        ↓
FINDING F-122
```

This graph-based explanation is a core product feature.

---

# 45. Regulatory Source Ingestion Rules

When ingesting a regulation:

1. Preserve original source.
2. Record issuer.
3. Record publication date.
4. Record effective/commencement status when available.
5. Record version/change date.
6. Extract provisions.
7. Preserve section numbering.
8. Store source location.
9. Store retrieval timestamp.
10. Flag ambiguous provisions for review.

Do not “summarize away” the original text before storing the source metadata.

---

# 46. Legal/Compliance Language Rules

Use:

- “applicable requirement”
- “potential compliance gap”
- “control not evidenced”
- “review required”
- “based on current regulatory pack”
- “engineering inference”

Avoid:

- “you are illegal”
- “this guarantees compliance”
- “regulator will reject this”
- “this definitely violates the law”

unless the evidence and legal authority support the precise statement and the product is intentionally presenting a human-reviewed legal conclusion.

---

# 47. Logging / Audit Events

Record events such as:

```text
SYSTEM_CREATED
ARCHITECTURE_IMPORTED
ANALYSIS_STARTED
ANALYSIS_COMPLETED
FINDING_CREATED
FINDING_REVIEWED
EVIDENCE_ADDED
CONTROL_CHANGED
REGULATION_VERSION_ADDED
CHANGE_EVENT_INGESTED
REMEDIATION_CREATED
REMEDIATION_CLOSED
```

Audit logs should be immutable from normal application operations.

---

# 48. Demo Data Must Be Honest

Never seed a fake regulatory requirement and present it as a real law.

It is acceptable to create:

```text
DEMO_POLICY
```

for an internal company policy.

It is not acceptable to create:

```text
Indian law requires X
```

unless the knowledge base contains a real source.

---

# 49. Future Monetization Architecture

Do not implement billing in MVP, but design for these future tiers:

### Starter

Single environment, limited systems.

### Growth

Multiple AI systems + integrations + evidence workflow.

### Enterprise

- continuous integrations,
- custom regulatory packs,
- SSO,
- audit history,
- policy-as-code,
- CI/CD enforcement,
- private deployment.

### Services / Expert Review

Human legal/compliance review can become an add-on, but the software itself must remain valuable.

---

# 50. What Makes This Defensible

Do not claim defensibility from “using Claude/GPT”.

Potential defensibility comes from:

```text
1. Regulatory ontology
2. Architecture ontology
3. Control ontology
4. Source provenance
5. Historical system state
6. Engineering integrations
7. Change-impact graph
8. India-specific mappings
9. Human review feedback loop
10. Policy-as-code layer
```

The long-term asset is the mapping:

```text
REAL AI SYSTEM
      ↕
REGULATORY REQUIREMENT
      ↕
CONTROL
      ↕
EVIDENCE
      ↕
OBSERVED RUNTIME STATE
```

---

# 51. Investor / Customer Narrative

Do NOT pitch:

> “AI-powered compliance chatbot.”

Pitch:

> **“AI systems change every week, but compliance reviews are still snapshots. We compile the actual AI architecture into a live map of regulatory obligations, controls and evidence, then detect the compliance impact whenever the system changes.”**

That is the core story.

---

# 52. Definition of Done

Do not stop at “the pages render.”

The build is DONE only when a reviewer can:

1. create FinServe,
2. import its AI architecture,
3. view the architecture graph,
4. run analysis,
5. see real requirement mappings,
6. open a finding,
7. inspect its source citation,
8. inspect missing evidence,
9. create remediation,
10. trigger an architecture change,
11. see exactly which controls/findings became affected,
12. review and close a finding,
13. see the entire action in audit history.

Run this entire sequence from a fresh environment before calling the MVP complete.

---

# 53. Final Agent Instructions

You are operating as the lead product engineer and technical architect.

Do not merely generate recommendations. Build the actual application.

Do not stop to ask for approval on routine implementation choices.

When a choice is ambiguous, choose the option that maximizes:

1. correctness,
2. demonstrability,
3. maintainability,
4. security,
5. speed of implementation.

Do not add features merely because they look impressive.

Prefer a smaller number of deep, connected capabilities over a larger number of shallow ones.

Before declaring success:

- run tests,
- run the production build,
- seed the demo environment,
- execute the full hero demo,
- inspect for hallucinated legal claims,
- verify citations,
- verify tenant isolation,
- verify change-impact propagation,
- fix obvious defects,
- leave clear setup instructions in the repository.

If a regulatory mapping cannot be verified from an authoritative source, mark it for human review instead of inventing an answer.

If an implementation is simulated, label it as simulated in the UI.

The goal is not to create the appearance of a compliance platform.

The goal is to produce a **working architecture-to-regulation compiler prototype that could credibly become a real enterprise product.**

---

# Appendix A — Strategic Guardrails

### Do not overclaim novelty

The global AI governance market already has serious vendors. The novelty being pursued is the specific product architecture and India-first execution, not the invention of AI governance itself.

### Do not overclaim regulation

DPDP, RBI, CERT-In and IndiaAI materials have different legal and institutional statuses. The application must represent that distinction explicitly.

### Do not overclaim automation

Legal interpretation and high-impact compliance decisions require human review.

### Do not turn the product into a document generator

Reports are an output. They are not the core product.

### Do not make dashboards the moat

The moat must be the graph + source provenance + applicability engine + controls + evidence + drift loop.

---

# Appendix B — Useful Current Sources

1. MeitY — Digital Personal Data Protection Act, 2023
   https://www.meity.gov.in/writereaddata/files/Digital%20Personal%20Data%20Protection%20Act%202023.pdf

2. MeitY — Digital Personal Data Protection Rules, 2025
   https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digit

3. MeitY — Acts and Policies
   https://www.meity.gov.in/documents/act-and-policies

4. RBI — FREE-AI Committee Report listing
   https://m.rbi.org.in/Scripts/BS_ViewPublicationReport.aspx

5. RBI
   https://www.rbi.org.in/

6. CERT-In — Directions under Section 70B
   https://www.cert-in.org.in/Directions70B.jsp

7. CERT-In Directions PDF
   https://cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf

8. IndiaAI
   https://indiaai.gov.in/

9. OneTrust AI Governance — competitor reference
   https://www.onetrust.com/solutions/ai-governance/

10. Credo AI — competitor reference
    https://www.credo.ai/

11. Holistic AI — competitor reference
    https://www.holisticai.com/ai-governance-platform

---

# Appendix C — First Prompt To Use With a Coding Agent

Use the following as the execution kickoff after placing this file in the repository:

```text
Read AI_Compliance_Compiler_Instructions.md completely before making changes.

You are the lead engineer responsible for executing the entire MVP described in the document.

Start by inspecting the repository and current environment. Then build the product end-to-end without waiting for routine confirmations.

Prioritize the mandatory closed loop:

architecture import → system graph → India regulatory pack → applicability → controls → evidence → findings → remediation → change event → impact analysis.

Do not substitute static mock screens for functioning logic.

Where the instructions distinguish legally binding sources from guidance, preserve that distinction in the data model and UI.

Where a legal citation cannot be verified, do not invent it. Mark it for human review.

When finished, run the full demo scenario, run tests, run the production build, and fix failures before declaring completion.
```
