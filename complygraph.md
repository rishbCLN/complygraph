# COMPLYGRAPH — MASTER AUTONOMOUS BUILD SPECIFICATION

## 0. EXECUTION DIRECTIVE

You are the principal software architect, senior full-stack engineer, security engineer, data engineer, product designer, QA engineer, and DevOps engineer responsible for delivering the complete working system described in this document.

The goal is to build a production-quality capstone application named:


# COMPLYGRAPH

### Product descriptor

**Continuous Data Governance & Compliance Infrastructure**

The product is designed initially around India's Digital Personal Data Protection Act, 2023 and the Digital Personal Data Protection Rules, 2025.

The system must not be a generic AI chatbot, generic compliance checklist, generic document repository, or generic dashboard.

The core product concept is:

> Continuously discover where personal data exists, understand how it moves through systems, map those data flows to regulatory obligations and technical controls, collect evidence that controls actually operate, detect control gaps, prioritize remediation, and provide an AI investigation layer grounded in the system's evidence.

The most important architectural idea is:

```text
REGULATION
    ↓
OBLIGATION
    ↓
CONTROL
    ↓
DATA ASSET / PROCESS
    ↓
EVIDENCE
    ↓
CONTROL EVALUATION
    ↓
FINDING
    ↓
REMEDIATION
    ↓
VERIFICATION

1. NON-NEGOTIABLE BUILD RULES

Follow these rules throughout the implementation.

Do not reduce this to:

PDF → LLM → compliance answer

That is explicitly NOT the product.
1.1 Complete the application, do not merely scaffold it

Do not stop at:

wireframes
placeholder pages
API stubs
fake charts
TODO comments
empty service methods
mock database repositories
fake AI responses
disconnected frontend screens
"future implementation" buttons

Every major screen must be connected to actual backend functionality.

Every major feature must have:

database model
migration
backend service
API endpoint
frontend UI
validation
error handling
test coverage
1.2 Autonomous overnight execution

Do NOT repeatedly stop to ask the user what to build next.

The architecture and requirements have already been decided.

Make reasonable implementation decisions yourself when something is unspecified.

If an optional external dependency is unavailable:

do not stop
do not leave the feature broken
implement a deterministic local fallback
document the fallback
continue with the rest of the system

The project must be usable entirely locally.

1.3 No cloud dependency

The complete application must run locally using:

Docker Compose

The required baseline command must eventually be:

docker compose up --build

After startup, the user must be able to open the application and use the seeded demo organization without configuring AWS, Azure, GCP, Kubernetes, Kafka, managed PostgreSQL, or any third-party SaaS account.

1.4 No Kubernetes

Do not introduce Kubernetes.

Do not introduce unnecessary microservices.

This is a sophisticated modular monolith with a dedicated background worker, not a miniature cloud platform.

Architecture:

                    ┌───────────────────┐
                    │     Next.js       │
                    │      Web App      │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │     FastAPI       │
                    │      Backend      │
                    └───────┬─────┬─────┘
                            │     │
                ┌───────────┘     └────────────┐
                ▼                              ▼
        ┌───────────────┐              ┌───────────────┐
        │  PostgreSQL   │              │     Redis     │
        └───────────────┘              └───────┬───────┘
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │ Background      │
                                      │ Worker          │
                                      └─────────────────┘
2. PRODUCT VISION

ComplyGraph answers four questions continuously:

Question 1

Where does our personal data exist?

Question 2

Where does it flow?

Question 3

Which controls and obligations apply to those data flows?

Question 4

Do we have evidence that those controls actually work?

The platform therefore maintains five major graphs:

DATA GRAPH
SYSTEM GRAPH
FLOW GRAPH
CONTROL GRAPH
EVIDENCE GRAPH

These graphs should be represented as related entities in PostgreSQL and rendered as interactive views in the frontend.

3. IMPORTANT LEGAL/PRODUCT BOUNDARY

ComplyGraph is software for governance, evidence collection and internal control assessment.

It is NOT a law firm.

It must NOT tell users:

"You are legally compliant."

Instead use language such as:

"Control appears satisfied"
"Control gap detected"
"Evidence missing"
"Review required"
"Potential regulatory obligation"
"Upcoming requirement"
"Control assessment"
"Requires legal/privacy review"

Do not claim legal certification.

Do not invent regulatory requirements.

Do not invent legal citations.

Every regulation, obligation and control must contain a source reference.

4. REGULATORY FOUNDATION

The initial regulatory framework is:

Digital Personal Data Protection Act, 2023
Digital Personal Data Protection Rules, 2025

Use the official Ministry of Electronics and Information Technology documents as the authoritative source.

The project must maintain the regulatory library as database records.

DO NOT hard-code applicability solely in frontend code.

Each obligation/control must contain:

id
framework_id
title
description
legal_reference
source_document
source_section
effective_from
status
category
applicability
assessment_logic
evidence_requirements
created_at
updated_at

The effective_from field is essential.

The application must be able to represent:

IN_FORCE
UPCOMING
NOT_APPLICABLE
RETIRED

The system must calculate status using the project's configured "assessment date."

Default assessment date:

current system date

Provide a setting that allows a user to simulate a future date.

Example:

Assessment date:
2026-09-19

Control:
DPDP-RULE-SECURITY-001

Effective:
2027-05-13

Status:
UPCOMING

Do not display this as a current failure.

5. REGULATORY SEED CONTENT

Seed a useful initial DPDP control library.

At minimum include controls for:

DPDP-NOTICE-001
Notice / purpose transparency

DPDP-CONSENT-001
Consent capture and purpose linkage

DPDP-CONSENT-002
Consent withdrawal workflow

DPDP-RIGHTS-001
Data Principal rights request mechanism

DPDP-SECURITY-001
Encryption / obfuscation / tokenisation safeguards

DPDP-SECURITY-002
Access control

DPDP-SECURITY-003
Logging / monitoring / review

DPDP-SECURITY-004
Backup / availability / recovery

DPDP-SECURITY-005
Security obligations in processor contracts

DPDP-BREACH-001
Personal data breach detection and response

DPDP-BREACH-002
Affected Data Principal notification readiness

DPDP-RETENTION-001
Purpose-based retention

DPDP-RETENTION-002
Deletion / erasure execution

DPDP-CHILDREN-001
Child-data consent / age verification workflow

DPDP-SDF-001
Data Protection Impact Assessment

DPDP-SDF-002
Periodic audit

DPDP-VENDOR-001
Processor/vendor governance

DPDP-CROSSBORDER-001
Cross-border data-flow governance

DPDP-GOVERNANCE-001
Privacy contact / responsible person information

These are product control objects.

Do not present all of them as presently operative unless their effective date makes them operative.

6. PRIMARY DIFFERENTIATOR

The key feature is:

CONTINUOUS DATA-FLOW COMPLIANCE

The user should be able to connect a data source.

ComplyGraph should inspect it.

Example:

PostgreSQL
  ↓
schema discovery
  ↓
table discovery
  ↓
column discovery
  ↓
sample analysis
  ↓
PII classification
  ↓
asset inventory

Example result:

customers.email
classification: PERSONAL_DATA
category: CONTACT
confidence: 0.98

customers.phone
classification: PERSONAL_DATA
category: CONTACT
confidence: 0.96

customers.created_at
classification: OPERATIONAL_METADATA
confidence: 0.91

The system then links those assets to:

processing purposes
systems
vendors
flows
controls
evidence
findings
7. INITIAL TARGET CUSTOMER

Build the product for:

Indian mid-market technology companies

Examples:

SaaS
fintech
edtech
healthtech
e-commerce
B2B platforms
consumer internet

Typical customer:

100–2000 employees
multiple databases
multiple internal systems
customer PII
engineering team
security/compliance owner
privacy/legal owner

Also support a second customer type:

privacy/compliance consulting firms

The UI should therefore support:

Organization
    ↓
Workspace
    ↓
Systems
    ↓
Data
    ↓
Controls
    ↓
Evidence
    ↓
Findings
    ↓
Remediation
8. TECHNICAL STACK

Use exactly this architecture unless a dependency is technically impossible.

Frontend
Next.js
TypeScript
App Router
Tailwind CSS
shadcn/ui
TanStack Query
React Hook Form
Zod
@xyflow/react
Recharts
Lucide icons
Backend
Python 3.12+
FastAPI
Pydantic v2
SQLAlchemy 2
Alembic
PostgreSQL
Redis
Celery
PyJWT
pwdlib with Argon2
httpx
AI
Anthropic API

Use an environment variable:

ANTHROPIC_API_KEY

and:

ANTHROPIC_MODEL

Never hard-code a model name throughout the codebase.

Centralize model configuration.

If the API key is absent:

AI_MODE=deterministic

must activate a local fallback.

The application must still work.

9. DEVELOPMENT INFRASTRUCTURE

Create:

docker-compose.yml
docker-compose.dev.yml
Dockerfile
.env.example
Makefile
README.md

Services:

web
api
worker
postgres
redis

Use health checks.

The API must not declare itself healthy until PostgreSQL is reachable.

The worker must not start processing jobs until Redis and PostgreSQL are available.

10. REPOSITORY STRUCTURE

Create this repository structure:

complygraph/
│
├── apps/
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── types/
│   │   └── styles/
│   │
│   └── api/
│       ├── app/
│       │   ├── api/
│       │   ├── core/
│       │   ├── models/
│       │   ├── schemas/
│       │   ├── services/
│       │   ├── repositories/
│       │   ├── workers/
│       │   ├── scanners/
│       │   ├── graph/
│       │   ├── controls/
│       │   ├── ai/
│       │   ├── security/
│       │   └── main.py
│       └── tests/
│
├── demo/
│   ├── source-db/
│   ├── datasets/
│   ├── connectors/
│   ├── scenarios/
│   └── seed/
│
├── infra/
│   ├── docker/
│   └── scripts/
│
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── security/
│   ├── regulatory/
│   └── demo/
│
├── scripts/
│   ├── bootstrap.sh
│   ├── full-check.sh
│   ├── demo-reset.sh
│   └── seed-demo.sh
│
├── .github/
│   └── workflows/
│
├── docker-compose.yml
├── Makefile
├── README.md
├── SECURITY.md
├── LICENSE
└── .env.example
11. DATABASE ARCHITECTURE

Use PostgreSQL.

Use UUID primary keys.

Use timestamps in UTC.

Use foreign keys.

Use indexes on:

organization_id
workspace_id
status
created_at
updated_at
asset_type
control_id
finding_status
severity
12. DATABASE TABLES

Implement at least the following.

organizations
id
name
slug
industry
country
created_at
updated_at
users
id
email
full_name
password_hash
is_active
created_at
updated_at
memberships
id
organization_id
user_id
role
created_at

Roles:

OWNER
ADMIN
PRIVACY_OFFICER
SECURITY_ANALYST
ENGINEER
AUDITOR
VIEWER
sessions
id
user_id
token_hash
expires_at
created_at
revoked_at
connectors
id
organization_id
name
type
status
configuration_encrypted
last_scan_at
created_at
updated_at

Connector types:

POSTGRES
CSV
JSON
DEMO

Do not build external SaaS connectors in the overnight MVP.

Design interfaces so they can be added later.

data_assets
id
organization_id
connector_id
name
display_name
asset_type
system_name
environment
classification
sensitivity_level
owner
description
row_count
last_seen_at
created_at
updated_at

Asset types:

DATABASE
TABLE
FILE
API
SAAS
BUCKET
DATASET
APPLICATION
asset_fields
id
asset_id
name
data_type
classification
category
confidence
detection_method
sample_count
sensitive_count
created_at
updated_at

Data categories:

IDENTITY
CONTACT
LOCATION
FINANCIAL
HEALTH
AUTHENTICATION
DEVICE
BEHAVIORAL
PROFESSIONAL
OTHER_PERSONAL
NON_PERSONAL
UNKNOWN
processing_activities
id
organization_id
name
purpose
description
lawful_basis
owner
status
created_at
updated_at

Do not present lawful_basis as a legal conclusion.
It is an organization's declared basis that may require review.

data_flows
id
organization_id
source_asset_id
destination_asset_id
flow_type
purpose
contains_personal_data
contains_sensitive_category
cross_border
vendor_id
discovered
confidence
status
created_at
updated_at

Flow types:

INTERNAL
PROCESSOR
THIRD_PARTY
ANALYTICS
EXPORT
BACKUP
ARCHIVE
vendors
id
organization_id
name
description
service_type
country
data_processing
contract_status
risk_level
owner
created_at
updated_at
regulations
id
name
jurisdiction
version
source_document
effective_from
status
created_at
updated_at
obligations
id
regulation_id
code
title
description
legal_reference
source_section
effective_from
applicability_logic
created_at
updated_at
controls
id
obligation_id
code
title
description
category
assessment_method
effective_from
severity_default
created_at
updated_at
control_asset_scopes
id
control_id
asset_id
reason
applicable
created_at
evidence
id
organization_id
type
name
description
source
source_url
file_path
hash
collected_at
expires_at
status
owner
created_at
updated_at

Evidence types:

DOCUMENT
CONFIGURATION
SCAN_RESULT
LOG
SCREENSHOT
POLICY
TICKET
API_RESPONSE
DATABASE_CHECK
MANUAL_ATTESTATION
control_evidence
id
control_id
evidence_id
relation_type
created_at

Relation types:

SUPPORTS
CONTRADICTS
PARTIAL
control_assessments
id
organization_id
control_id
status
score
assessment_date
reason
evidence_count
automated
created_at
updated_at

Statuses:

PASS
PARTIAL
FAIL
NO_EVIDENCE
UPCOMING
NOT_APPLICABLE
NEEDS_REVIEW
findings
id
organization_id
control_id
asset_id
data_flow_id
title
description
severity
risk_score
status
source
detected_at
due_at
resolved_at
resolved_by
created_at
updated_at

Statuses:

OPEN
ACKNOWLEDGED
IN_PROGRESS
RESOLVED
ACCEPTED_RISK
FALSE_POSITIVE
remediation_tasks
id
organization_id
finding_id
title
description
assignee_id
priority
status
due_at
completed_at
created_at
updated_at
scans
id
organization_id
connector_id
status
started_at
completed_at
items_scanned
findings_created
error_message
created_at
scan_results
id
scan_id
asset_id
field_name
result_type
classification
confidence
evidence
created_at

Do not store unmasked raw PII in evidence.

data_subject_requests
id
organization_id
requester_identifier
request_type
status
received_at
due_at
assigned_to
verification_status
notes
completed_at
created_at
updated_at

Request types:

ACCESS
CORRECTION
ERASURE
NOMINATION
GRIEVANCE
WITHDRAW_CONSENT
breach_incidents
id
organization_id
title
description
severity
detected_at
contained_at
affected_assets
affected_records_estimate
status
board_notification_status
principal_notification_status
root_cause
remediation
created_at
updated_at

Statuses:

DETECTED
INVESTIGATING
CONTAINED
NOTIFICATION_PENDING
NOTIFIED
CLOSED
audit_events
id
organization_id
user_id
action
entity_type
entity_id
metadata
ip_address
created_at

Every security-relevant mutation must write an audit event.

ai_investigations
id
organization_id
finding_id
input_hash
model
status
summary
root_causes
recommendations
missing_evidence
legal_review_required
raw_response_redacted
created_at
completed_at

Never store raw personal data in AI requests or responses.

13. MULTI-TENANCY

All organization-owned records must be scoped by organization_id.

Backend authorization must verify organization membership.

Never rely on frontend filtering for tenancy.

Every repository/service method must receive organization context.

Implement tests for:

Organization A cannot access Organization B data.

This test is mandatory.

14. AUTHENTICATION

Implement:

email/password login
logout
current-user endpoint
password hashing
session handling
role-based authorization

Passwords:

Argon2id

Sessions:

HTTP-only cookie
Secure cookie in production
SameSite=Lax

Do not store authentication tokens in localStorage.

Implement:

POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/change-password
15. API DESIGN

Use /api/v1.

Implement at minimum:

Dashboard
GET /api/v1/dashboard/summary
GET /api/v1/dashboard/risk-trend
GET /api/v1/dashboard/top-findings
GET /api/v1/dashboard/data-posture
Organizations
GET /api/v1/organization
PATCH /api/v1/organization
Connectors
GET /api/v1/connectors
POST /api/v1/connectors
GET /api/v1/connectors/{id}
PATCH /api/v1/connectors/{id}
DELETE /api/v1/connectors/{id}
POST /api/v1/connectors/{id}/test
POST /api/v1/connectors/{id}/scan
Assets
GET /api/v1/assets
GET /api/v1/assets/{id}
GET /api/v1/assets/{id}/fields
GET /api/v1/assets/{id}/flows
GET /api/v1/assets/{id}/controls
PATCH /api/v1/assets/{id}

Support filters:

classification
category
sensitivity
system
owner
asset_type
search
Data graph
GET /api/v1/graph/data
GET /api/v1/graph/asset/{id}

Return:

{
  "nodes": [],
  "edges": []
}
Processing activities
GET /api/v1/processing-activities
POST /api/v1/processing-activities
PATCH /api/v1/processing-activities/{id}
DELETE /api/v1/processing-activities/{id}
Vendors
GET /api/v1/vendors
POST /api/v1/vendors
GET /api/v1/vendors/{id}
PATCH /api/v1/vendors/{id}
Regulations
GET /api/v1/regulations
GET /api/v1/regulations/{id}
GET /api/v1/regulations/{id}/obligations
Controls
GET /api/v1/controls
GET /api/v1/controls/{id}
GET /api/v1/controls/{id}/evidence
GET /api/v1/controls/{id}/assessment
POST /api/v1/controls/{id}/assess
Findings
GET /api/v1/findings
GET /api/v1/findings/{id}
PATCH /api/v1/findings/{id}
POST /api/v1/findings/{id}/assign
POST /api/v1/findings/{id}/resolve
POST /api/v1/findings/{id}/accept-risk
POST /api/v1/findings/{id}/investigate
Evidence
GET /api/v1/evidence
POST /api/v1/evidence
GET /api/v1/evidence/{id}
PATCH /api/v1/evidence/{id}
DELETE /api/v1/evidence/{id}
POST /api/v1/evidence/{id}/link
Tasks
GET /api/v1/tasks
POST /api/v1/tasks
PATCH /api/v1/tasks/{id}
Data requests
GET /api/v1/data-requests
POST /api/v1/data-requests
GET /api/v1/data-requests/{id}
PATCH /api/v1/data-requests/{id}
POST /api/v1/data-requests/{id}/verify
POST /api/v1/data-requests/{id}/complete
Breaches
GET /api/v1/incidents
POST /api/v1/incidents
GET /api/v1/incidents/{id}
PATCH /api/v1/incidents/{id}
POST /api/v1/incidents/{id}/notify
POST /api/v1/incidents/{id}/close
Reports
GET /api/v1/reports/executive
GET /api/v1/reports/findings
GET /api/v1/reports/data-inventory
GET /api/v1/reports/audit
GET /api/v1/reports/executive/pdf
Audit
GET /api/v1/audit-events
16. DATA DISCOVERY ENGINE

Build real discovery functionality.

PostgreSQL scanner

Given a PostgreSQL connection:

connect safely
enumerate schemas
enumerate tables
enumerate columns
inspect data types
count rows
sample a bounded number of rows
classify fields
store only metadata and redacted detection evidence
create/update data assets
create/update asset fields
run applicable controls
create findings where appropriate

Sampling limit:

maximum 100 rows per field

Do not retrieve entire datasets.

Never store raw sampled rows in PostgreSQL.

17. CSV SCANNER

When a CSV is uploaded:

file metadata
headers
row count
sample rows

Infer:

field names
types
PII classes
confidence

Store:

hash
row count
field metadata
classification
masked examples

Example masked result:

j***@example.com
+91******1234

Never display full synthetic or production-like PII unnecessarily.

18. JSON SCANNER

Support:

JSON arrays
nested JSON
objects with repeated records

Flatten nested paths:

customer.contact.email
customer.contact.phone

Classify fields.

19. PII CLASSIFICATION ENGINE

Do NOT use an LLM for baseline classification.

Implement a deterministic hybrid classifier.

Inputs:

column name
data type
sample pattern
value frequency
field path

Signals:

Column-name rules

Examples:

email
email_address
phone
mobile
telephone
first_name
last_name
dob
date_of_birth
address
postal_code
ip_address
passport
bank
account_number
Regex rules

Implement safe patterns for:

email
Indian phone-like values
IP address
date of birth formats
generic card-like number patterns

Do not attempt to claim identity verification.

Confidence

Use a deterministic score:

name_signal = 0.0–1.0
pattern_signal = 0.0–1.0
type_signal = 0.0–1.0

confidence =
    0.45 * name_signal +
    0.45 * pattern_signal +
    0.10 * type_signal

Thresholds:

>= 0.85 HIGH
0.65–0.849 MEDIUM
< 0.65 LOW

Use needs_review=true for medium/low classification where the field could matter.

20. DATA SENSITIVITY

Assign:

1 = non-personal
2 = ordinary personal
3 = sensitive operational
4 = high-risk personal
5 = critical

Do not imply that this ranking is mandated by law.

It is an internal risk model.

21. DATA FLOW GRAPH

Build a graph engine representing:

SOURCE → PROCESS → DESTINATION

Example:

Customer PostgreSQL
        ↓
Marketing ETL
        ↓
CSV Export
        ↓
Analytics Vendor

The frontend must render this using React Flow.

Nodes should have:

name
type
classification
sensitivity
owner
status

Edges should have:

flow_type
purpose
contains_personal_data
cross_border
vendor
confidence

Clicking a node must open asset details.

Clicking an edge must open flow details.

22. CHANGE DETECTION

A scan must compare the current state against the previous scan.

Detect:

new asset
deleted asset
new field
deleted field
classification changed
sensitivity changed
new data flow
removed data flow
row count changed materially
vendor changed
retention metadata changed

Example UI:

DATA INVENTORY CHANGE

+ marketing_export.csv
+ customer.phone classified as PERSONAL_DATA
~ customer.email sensitivity: 2 → 3
- old_customer_backup.csv

Create audit events for scan results.

23. CONTROL ENGINE

Controls must be deterministic first.

Each control implements an evaluator.

Conceptually:

evaluate(context) -> ControlAssessment

It should return:

status
score
reason
evidence_ids
affected_asset_ids
recommended_actions

Example:

control:
DPDP-RETENTION-001

context:
customer table exists
personal data exists
retention policy absent

result:
FAIL

Another example:

control:
DPDP-SECURITY-003

context:
audit logs configured
latest review timestamp within policy threshold

result:
PASS

Do not let the LLM decide control status.

24. CONTROL EVALUATION RULES

Implement the following baseline logic.

Notice control

Pass if:

processing activity exists
AND purpose exists
AND personal data categories are mapped
AND notice evidence exists

Otherwise:

NO_EVIDENCE
or
FAIL

depending on exact missing condition.

Consent control

Pass if:

purpose is defined
AND consent capture evidence exists
AND withdrawal workflow exists when applicable
Rights control

Pass if:

request intake mechanism exists
AND request tracking exists
AND responsible owner exists
AND status workflow exists
Security control

Assess:

encryption
access control
logging
backup
monitoring

Produce separate findings.

Breach control

Pass if:

breach intake exists
AND incident workflow exists
AND notification workflow exists
AND responsible owner exists
Retention control

Pass if:

retention policy exists
AND retention period defined
AND deletion mechanism exists
AND last execution exists

Fail when:

personal-data asset
+
no retention policy

or:

retention policy exists
+
deletion job has failed
Vendor control

Pass if:

vendor exists
AND contract status recorded
AND data processing purpose recorded
AND data categories mapped
SDF/DPIA control

Where configured as applicable:

DPIA evidence
audit evidence
algorithmic risk review evidence
25. RISK SCORING

Create an internal risk score from 0–100.

This is a product risk score, NOT a statutory score.

Inputs:

sensitivity        1–5
exposure           1–5
control_gap        0–5
volume             1–5

Formula:

weighted =
    0.35 * sensitivity +
    0.25 * exposure +
    0.25 * control_gap +
    0.15 * volume

risk_score = round(weighted / 5 * 100)

Severity:

80–100 CRITICAL
60–79  HIGH
35–59  MEDIUM
0–34   LOW

Always display:

Internal risk assessment

rather than implying the law itself assigns this numerical score.

26. FINDING GENERATION

A finding should include:

What was detected
Why it matters
Affected assets
Affected data categories
Relevant control
Relevant obligation
Evidence
Risk score
Owner
Suggested remediation

Example:

UNMANAGED PERSONAL-DATA EXPORT

Personal data was discovered in a CSV asset
outside the documented retention workflow.

Affected:
marketing_export.csv

Detected:
email
phone

Control:
DPDP-RETENTION-001

Risk:
HIGH

Evidence:
scan_2026_09_19_001

Recommended actions:
1. Identify owner
2. Define retention period
3. Remove unmanaged copy
4. Add export to inventory
5. verify recurring deletion
27. EVIDENCE ENGINE

Evidence is one of the most important parts of the product.

Users must be able to attach evidence to controls.

Evidence can come from:

scan
document
configuration
manual upload
database check
ticket
policy
system output

Every evidence item should have:

source
collector
collected_at
hash
expiration
status

Hashes are important so an auditor can determine if the artifact changed.

28. EVIDENCE FRESHNESS

Support:

fresh
stale
expired
unknown

based on expires_at.

Dashboard example:

Evidence Health

Fresh       84%
Stale       11%
Expired      5%
29. REMEDIATION WORKFLOW

Finding:

OPEN
 ↓
ACKNOWLEDGED
 ↓
IN_PROGRESS
 ↓
RESOLVED

Alternative:

OPEN
 ↓
ACCEPTED_RISK

Require justification for:

ACCEPTED_RISK
FALSE_POSITIVE

All state changes generate audit events.

30. DATA PRINCIPAL REQUEST WORKFLOW

Implement a simple operational workflow.

Flow:

REQUESTED
 ↓
IDENTITY_VERIFICATION
 ↓
IN_PROGRESS
 ↓
FULFILLED

or:

REJECTED

Request types:

ACCESS
CORRECTION
ERASURE
WITHDRAW_CONSENT
GRIEVANCE
NOMINATION

The purpose of this feature is workflow management.

Do not attempt to perform real legal identity verification.

31. BREACH MANAGEMENT

Build a breach incident module.

Features:

incident intake
severity
affected assets
affected data
estimated records
timeline
containment actions
root cause
remediation
notification status
audit history

Timeline:

Detected
Investigating
Contained
Notification Pending
Notified
Closed

Support separate:

Data Principal notification status
Board notification status

Do not automatically claim a legal notification deadline unless the applicable regulatory data is in force and configured.

The deadline logic must be configuration-driven.

32. AI LAYER

The AI is an investigation and explanation layer.

It is NOT the source of regulatory truth.

Architecture:

Deterministic System
        ↓
Facts
        ↓
Evidence
        ↓
AI Investigator
        ↓
Narrative / hypotheses / remediation

The AI should have structured access to:

finding
asset
data flow
control
control assessment
evidence
audit events
scan history
vendor
processing activity
33. AI INVESTIGATION OUTPUT

The AI must return validated JSON.

Schema:

{
  "summary": "string",
  "root_causes": [
    {
      "title": "string",
      "likelihood": 0.0,
      "evidence": ["evidence-id"],
      "reasoning": "string"
    }
  ],
  "recommended_actions": [
    {
      "action": "string",
      "priority": "LOW|MEDIUM|HIGH|CRITICAL",
      "owner_type": "PRIVACY|SECURITY|ENGINEERING|LEGAL|BUSINESS",
      "requires_human_review": true
    }
  ],
  "missing_evidence": [],
  "legal_review_required": true,
  "uncertainty": "string"
}

Validate this with Pydantic.

If validation fails:

retry once
if still invalid, store error safely
show "AI investigation unavailable"
do not crash the application
34. AI DATA PRIVACY

This is critical.

Never send raw production personal data to Claude.

Before creating an AI request:

remove raw values
remove names
remove email addresses
remove phone numbers
remove addresses
remove authentication secrets
remove database credentials
remove API keys

Send:

field names
data categories
asset types
risk levels
masked examples
aggregate statistics
control results
evidence summaries

The system should explicitly display:

AI input sanitized
Raw personal data excluded

in the investigation detail.

35. AI MODEL PROMPTING

The investigator system prompt should say:

You are a compliance investigation assistant.

You do not determine legal compliance.

You analyze evidence collected by the platform.

You must not invent regulations, legal obligations, evidence, facts, controls, or system states.

Every factual claim must derive from supplied evidence.

When evidence is insufficient, say so.

Separate:
- observed fact
- inferred hypothesis
- recommendation
- legal review required

Never fabricate citations.
36. AI FALLBACK

If:

ANTHROPIC_API_KEY

is absent:

use:

AI_MODE=deterministic

The fallback should generate useful but deterministic output from findings.

Example:

Summary:
This finding is associated with a missing retention control.

Root cause:
No retention policy evidence was found.

Recommendation:
Define a retention policy and attach evidence
of scheduled deletion.

The application must remain fully demoable.

37. AI COST CONTROL

Cache investigation results by:

SHA256(
finding
+
evidence
+
control
+
asset
+
graph_context
)

If the same inputs are investigated again:

reuse previous result

Make a setting:

AI_MAX_CALLS_PER_SESSION=20
38. FRONTEND INFORMATION ARCHITECTURE

Build these pages.

/login

/dashboard

/data-assets
/data-assets/[id]

/data-map

/processing-activities

/vendors
/vendors/[id]

/regulations
/regulations/[id]

/controls
/controls/[id]

/findings
/findings/[id]

/evidence

/tasks

/data-requests
/data-requests/[id]

/incidents
/incidents/[id]

/reports

/audit-log

/ai-investigator

/settings
/settings/members
/settings/connectors
/settings/regulatory
39. DESIGN LANGUAGE

The product must look like a serious B2B security/compliance platform.

Style:

clean
dense
professional
technical
minimal
high information density
strong hierarchy

Avoid:

neon gradients
crypto aesthetic
huge rounded cards
cartoon illustrations
fake futuristic AI visuals
excessive animations
generic SaaS landing-page fluff

Think:

enterprise security console
+
modern developer tooling
+
high-quality data visualization
40. APP SHELL

Desktop-first application.

Layout:

┌────────────────────────────────────────────────────┐
│ Top bar                                            │
├────────────┬───────────────────────────────────────┤
│            │                                       │
│ Sidebar    │ Main content                          │
│            │                                       │
│ Dashboard  │                                       │
│ Data       │                                       │
│ Controls   │                                       │
│ Findings   │                                       │
│ Evidence   │                                       │
│ Graph      │                                       │
│ Reports    │                                       │
│ Audit      │                                       │
│ Settings   │                                       │
│            │                                       │
└────────────┴───────────────────────────────────────┘
41. DASHBOARD

The dashboard is the first important screen.

Do not use meaningless vanity metrics.

Display:

Data Assets
Personal Data Assets
Open Findings
Critical Findings
Control Coverage
Evidence Freshness
Unmapped Data Flows
Vendors Processing Personal Data
Upcoming Obligations

Main visualization:

Data Governance Posture

Do not call it:

"Legal Compliance Score"

Use:

Internal Control Posture
42. DASHBOARD LAYOUT

Top:

Organization
Assessment Date
Last Scan
Scan Now

Metrics:

1,284 Data Assets
327 Personal Data Assets
18 Critical Findings
74 Open Findings
81% Control Coverage
11% Evidence Stale

These values should be derived from the database.

Never hard-code the visible numbers.

43. DATA MAP PAGE

This is one of the centerpiece features.

Interactive graph:

Customer DB
      ↓
Order Service
      ↓
Marketing ETL
      ↓
Analytics Vendor

Use color/shape coding for:

database
application
file
vendor
external system

Provide filters:

personal data only
high risk
third party
cross border
vendor
system
category
44. ASSET DETAIL PAGE

Example:

Customer Database

TYPE:
PostgreSQL

OWNER:
Engineering

SENSITIVITY:
HIGH

PERSONAL DATA:
Yes

FIELDS:
email
phone
name
address

FLOWS:
Marketing ETL
Support Platform
Analytics Vendor

CONTROLS:
Retention
Access
Security
Deletion

FINDINGS:
3

LAST SCAN:
2 minutes ago

Tabs:

Overview
Fields
Data Flows
Controls
Evidence
History
Findings
45. FINDINGS PAGE

Table columns:

Severity
Finding
Asset
Control
Owner
Status
Detected
Due

Filters:

severity
status
owner
control
system
category

Click opens detailed finding.

46. FINDING DETAIL

This page must be excellent.

Header:

HIGH

Unmanaged Customer Data Export

Status:
OPEN

Sections:

Why this was detected
Affected data
Affected systems
Regulatory/control mapping
Evidence
Risk calculation
Recommended remediation
AI Investigation
Activity

Risk explanation:

Sensitivity      5/5
Exposure         4/5
Control gap      4/5
Volume           3/5

Overall:
82 / 100
47. CONTROL DETAIL

Show:

CONTROL CODE
TITLE
DESCRIPTION
LEGAL REFERENCE
SOURCE
EFFECTIVE DATE
STATUS

Applicable assets

Assessment

Evidence

Findings

Remediation tasks

If upcoming:

UPCOMING

Effective:
13 May 2027

This control is displayed for preparation,
not as a current failed control.
48. EVIDENCE PAGE

Show evidence lifecycle:

Name
Type
Source
Collected
Freshness
Hash
Linked controls
Linked findings
Owner

Allow:

upload
link
view metadata
expire
delete
49. REPORTING

Implement report generation.

Reports:

Executive Report
Data Inventory Report
Findings Report
Evidence Report
Audit Trail Report
Vendor Report

Support:

CSV
JSON
PDF

Executive report should contain:

Organization
Assessment date
Data inventory summary
Open findings
Critical risks
Control posture
Evidence freshness
Major vendors
Major data flows
Upcoming obligations
Top remediation actions

Include disclaimer:

This report is an internal governance and control assessment
generated by ComplyGraph. It is not legal advice or a
legal certification of compliance.
50. AUDIT LOG

Every relevant mutation must be recorded.

Examples:

User created
Connector added
Connector scanned
Asset discovered
Classification changed
Finding created
Finding assigned
Evidence uploaded
Control assessed
Task created
Task completed
Risk accepted
AI investigation run
Incident status changed
Data request changed

Display:

timestamp
actor
action
entity
metadata
51. DEMO ORGANIZATION

Create one completely fictional organization:

AsterLane Technologies Pvt. Ltd.

Industry:

SaaS / e-commerce infrastructure

Seed employees:

admin@asterlane.demo
privacy@asterlane.demo
security@asterlane.demo
engineer@asterlane.demo
auditor@asterlane.demo
viewer@asterlane.demo

Development-only password:

DemoPass123!

Clearly label demo credentials as development/demo only.

52. DEMO DATA SYSTEM

Create a second PostgreSQL database representing:

AsterLane customer platform

Tables:

customers
orders
support_tickets
marketing_preferences
employees

Example synthetic fields:

customers
id
first_name
last_name
email
phone
address
city
country
created_at
marketing_opt_in
orders
id
customer_id
order_total
payment_reference
created_at
support_tickets
id
customer_id
subject
description
created_at
marketing_preferences
customer_id
email_marketing
sms_marketing
updated_at
employees
id
name
email
department
joined_at

All records MUST be synthetic.

53. DEMO CSV

Create:

marketing_export.csv

containing synthetic:

customer_id
email
phone
campaign
created_at

Intentionally configure:

no documented retention

This creates a finding.

54. DEMO VENDOR

Create:

PulseMetrics Analytics

Country:

Singapore

Purpose:

product analytics

Seed a flow:

Customer DB
    ↓
Marketing ETL
    ↓
PulseMetrics Analytics

Containing:

email
customer_id
device_id

This creates a third-party data flow finding.

55. DEMO FAILURE SCENARIO

The initial seeded organization should NOT look perfectly compliant.

The dashboard must contain meaningful findings immediately.

Seed these situations:

Finding 1

Unmanaged customer export.

marketing_export.csv
contains personal data
retention not defined
Finding 2

Third-party analytics flow has incomplete processing-purpose mapping.

Finding 3

Customer deletion workflow exists but last execution failed.

Finding 4

Security logging evidence is stale.

Finding 5

Vendor processing agreement evidence is missing.

Finding 6

A future DPDP obligation is shown as:

UPCOMING

not failed.

This makes the dashboard meaningful on first launch.

56. DEMO SCAN

The user must be able to click:

Scan Now

and see:

Connecting
Inspecting schemas
Inspecting fields
Classifying data
Building inventory
Updating flows
Evaluating controls
Generating findings
Complete

Show progress.

The backend scan should run as a worker task.

57. SCAN JOB STATE

States:

QUEUED
RUNNING
COMPLETED
FAILED
CANCELLED

Frontend polls job status.

Do not fake progress.

Progress should correspond to real stages.

58. DEMO SCENARIO FLOW

The complete product demo should work as follows:

LOGIN
 ↓
DASHBOARD
 ↓
CLICK SCAN NOW
 ↓
SCAN COMPLETES
 ↓
NEW PERSONAL DATA ASSET DISCOVERED
 ↓
OPEN DATA MAP
 ↓
SEE CUSTOMER DB → MARKETING ETL → PULSEM​ETRICS
 ↓
OPEN FLOW
 ↓
SEE PERSONAL DATA CATEGORIES
 ↓
OPEN FINDING
 ↓
SEE CONTROL MAPPING
 ↓
VIEW EVIDENCE
 ↓
RUN AI INVESTIGATION
 ↓
SEE ROOT-CAUSE ANALYSIS
 ↓
CREATE REMEDIATION TASK
 ↓
ASSIGN TO ENGINEERING
 ↓
MARK REMEDIATED
 ↓
RE-RUN CONTROL
 ↓
CONTROL STATUS UPDATES
 ↓
AUDIT LOG SHOWS EVERYTHING
 ↓
GENERATE EXECUTIVE REPORT

This flow must work from a clean database.

59. CONTINUOUS MONITORING

Implement a simple scheduled scan capability.

Settings:

manual
daily
weekly

For local MVP, scheduled execution can run in the worker.

Do not introduce a separate scheduler service.

Use Celery beat only if cleanly supported.

The system should display:

Next scan
Last scan
Scan interval
60. NO FAKE DATA AFTER SEEDING

Frontend components must read from API endpoints.

Do not embed:

const findings = [...]

inside React components.

All production-facing dashboard data must come from backend APIs.

Seed data belongs in:

demo/seed/
61. SECURITY REQUIREMENTS

Implement:

Argon2 password hashing
HTTP-only cookies
RBAC
tenant isolation
audit logging
encrypted connector credentials
input validation
parameterized SQL
file type validation
file size limits
safe CSV parsing
safe JSON parsing
rate limiting on login
CORS restrictions
security headers
62. CONNECTOR SECURITY

Connector credentials must never be stored plaintext.

Use:

APP_ENCRYPTION_KEY

for authenticated encryption.

The database should only contain encrypted configuration blobs.

Do not log:

password
database URL
API key
secret
token

Mask credentials in logs.

63. FILE UPLOAD SECURITY

Allowed:

CSV
JSON
PDF
TXT

Set explicit file size limit:

25 MB

Validate MIME and extension.

Store uploaded files outside the source repository.

Use random storage IDs.

Never execute uploaded files.

Never trust filenames.

64. AI SECURITY

Never allow user-provided regulatory documents or arbitrary prompts to override system instructions.

Treat external text as untrusted data.

Do not allow the AI to:

execute shell commands
execute database writes
modify compliance state
delete data
send notifications

AI can recommend.

Humans and deterministic backend services execute.

65. OBSERVABILITY

The API must log:

request ID
method
path
status
duration
user ID
organization ID

Worker logs:

job ID
scan ID
connector ID
stage
duration
error

Do not log personal data.

Add /health.

Add:

/ready

for readiness.

66. ERROR HANDLING

API errors must return:

{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested asset was not found.",
    "request_id": "..."
  }
}

Do not leak stack traces to frontend.

Log stack traces server-side.

67. FRONTEND ERROR HANDLING

Implement:

loading states
empty states
error states
retry controls
success notifications
confirmation dialogs

Do not show blank white pages when an API fails.

68. UX DETAILS

Use skeleton loaders.

Use consistent:

buttons
badges
tables
breadcrumbs
tabs
drawers
modals
alerts
toasts

Status badges:

PASS
PARTIAL
FAIL
UPCOMING
OPEN
IN PROGRESS
RESOLVED

Severity badges:

CRITICAL
HIGH
MEDIUM
LOW
69. DATA VISUALIZATIONS

Implement:

Risk distribution

Bar/donut.

Findings over time

Line chart.

Control posture

Stacked bar.

Data categories

Bar chart.

Data-flow graph

React Flow.

Evidence freshness

Bar chart.

Vendor exposure

Table + visualization.

Do not use charts merely for decoration.

All values must come from API data.

70. SEARCH

Global search should search:

assets
fields
vendors
processing activities
controls
findings
evidence

Results should group by type.

71. FILTERING

All major tables require:

search
filter
sorting
pagination

Use server-side pagination for large lists.

72. AUDITOR VIEW

Implement a read-heavy auditor experience.

Auditor can:

view controls
view evidence
view findings
view audit log
generate reports

Auditor cannot:

change controls
delete evidence
change regulatory mappings
change organization membership
73. PRIVACY OFFICER VIEW

Privacy Officer can:

view data map
manage processing activities
manage vendors
review controls
assign findings
manage data requests
manage breach incidents
run AI investigations
74. ENGINEER VIEW

Engineer can:

view assigned findings
view affected assets
view data flows
upload evidence
update remediation tasks

Engineer must not modify regulatory definitions.

75. REGULATORY ADMIN

Admin can:

view regulatory framework
enable/disable frameworks
change assessment date

Do not allow arbitrary users to modify legal references.

76. CHANGE HISTORY

For:

regulations
obligations
controls
findings
assets
evidence
vendors
processing activities

maintain history where useful.

At minimum retain audit events.

77. DATABASE MIGRATIONS

All schema changes must use Alembic.

Never rely on:

create_all()

for production startup.

Startup sequence:

migrate
seed
start server

Seed operation must be idempotent.

Running it twice must not create duplicates.

78. TESTING STRATEGY

Implement:

Unit tests

For:

PII classifier
risk scoring
control evaluators
regulatory applicability
effective-date handling
data-flow graph
redaction engine
hashing
permissions
Integration tests

For:

database
scanner
connector
finding generation
evidence
AI investigator adapter
E2E tests

Use Playwright.

Test:

login
dashboard
scan
data map
finding workflow
evidence upload
AI investigation
remediation
report
logout
79. REQUIRED SECURITY TESTS

At minimum:

unauthorized API access
cross-organization data access
invalid JWT/session
wrong role
SQL injection input
path traversal filename
oversized file
malformed CSV
malformed JSON
secret leakage in logs
80. REQUIRED E2E TEST

Create one master E2E test:

demo_e2e.spec.ts

Flow:

login
→ dashboard
→ scan
→ wait for completion
→ inspect asset
→ inspect graph
→ open finding
→ inspect evidence
→ run investigation in deterministic mode
→ create task
→ resolve finding
→ verify audit entry
→ generate report

This test must pass in the final build.

81. DEVELOPMENT COMMANDS

Create:

make install
make dev
make build
make test
make lint
make typecheck
make migrate
make seed
make demo-reset
make e2e
make full-check

The most important command:

make full-check

must execute:

backend lint
backend typecheck
frontend lint
frontend typecheck
unit tests
integration tests
build
database migration test
E2E tests

and fail on any error.

82. FULL-CHECK SCRIPT

Create:

scripts/full-check.sh

It must:

start infrastructure
wait for services
run migrations
seed test data
run tests
build frontend
build backend
run E2E
print summary

Final output:

====================================
COMPLYGRAPH FULL SYSTEM CHECK
====================================

Database ............... PASS
Redis .................. PASS
API .................... PASS
Worker ................. PASS
Backend tests .......... PASS
Frontend tests ......... PASS
Type checks ............ PASS
Build .................. PASS
E2E .................... PASS
Demo scan .............. PASS
Report generation ...... PASS

SYSTEM READY
====================================
83. CI

Create GitHub Actions:

.github/workflows/ci.yml

Pipeline:

checkout
install dependencies
lint
typecheck
unit tests
integration tests
build

Do not make CI require external secrets.

The fallback AI mode must allow CI to run without an Anthropic key.

84. DOCUMENTATION

Create:

README.md
docs/architecture/system.md
docs/architecture/data-model.md
docs/architecture/control-engine.md
docs/architecture/scanner.md
docs/security/threat-model.md
docs/security/data-handling.md
docs/regulatory/dpdp-framework.md
docs/demo/demo-script.md
docs/api/api.md

README must contain:

What ComplyGraph is
Why it exists
Architecture
Features
Screenshots placeholders only if real screenshots unavailable
Quick start
Demo credentials
Demo workflow
Environment variables
Testing
Security model
Regulatory disclaimer

Do not claim certifications.

85. THREAT MODEL

Create a lightweight threat model covering:

data leakage
malicious file upload
credential leakage
cross-tenant access
privilege escalation
prompt injection
AI hallucination
malicious evidence
database compromise
insider misuse

For each:

threat
attack surface
mitigation
residual risk
86. AI THREAT MODEL

Explicitly document:

prompt injection
malicious regulatory text
malicious evidence descriptions
data exfiltration
AI hallucination
overconfident legal claims

Required mitigations:

structured prompts
input sanitization
schema validation
source-grounding
redaction
human approval
no privileged tool execution
87. REGULATORY DATA MODEL

Do NOT make regulations just long text blobs.

Represent them structurally:

Regulation
   ↓
Obligation
   ↓
Control
   ↓
Control evaluator
   ↓
Evidence

Example:

DPDP Act
  ↓
Security obligation
  ↓
Encryption control
  ↓
PostgreSQL inspection
  ↓
Evidence
  ↓
Assessment

This is one of the most important technical features.

88. EFFECTIVE-DATE ENGINE

Implement a reusable function:

is_control_active(
    control_effective_from,
    assessment_date
)

Return:

active
upcoming

Support future dates.

Example:

effective_from = 2027-05-13
assessment_date = 2026-09-19

status = UPCOMING

If:

assessment_date = 2027-06-01

then:

status = ACTIVE

Do not hardcode today's date into the evaluator.

89. REGULATORY SOURCE INTEGRITY

Every seeded legal item should have:

source_document
source_section
legal_reference
source_date
effective_from

Create a source manifest:

docs/regulatory/source-manifest.md

The source manifest must distinguish:

official primary source
secondary interpretation
internal product interpretation

Only official primary sources should be treated as the basis for regulatory facts.

90. NO LEGAL HALLUCINATIONS

When the user asks the AI:

"Are we legally compliant?"

the system should respond with a structured answer such as:

ComplyGraph does not provide a legal certification.

Current control assessment:

23 controls: PASS
7 controls: PARTIAL
4 controls: FAIL
6 controls: UPCOMING

Key evidence gaps:
...

Legal review recommended for:
...

Never:

"You are 87% legally compliant."
91. REPORT LANGUAGE

Use:

Control posture
Evidence coverage
Open findings
Risk exposure
Regulatory preparation

Avoid:

Official compliance certification
Guaranteed compliance
Legal approval
Government approved
92. GRAPH DATA MODEL

Nodes:

ASSET
APPLICATION
PROCESS
VENDOR
DATABASE
FILE
DATASET

Edges:

PROCESSES
STORES
READS
WRITES
EXPORTS
SHARES_WITH
BACKS_UP

Control graph nodes:

CONTROL
EVIDENCE
FINDING

Support a unified graph endpoint for future expansion.

93. FUTURE-READY ARCHITECTURE

Do not build these now:

Kubernetes
Kafka
AWS integrations
Azure integrations
Google Cloud integrations
Salesforce connector
Slack connector
Okta connector
full SaaS consent management
full DLP agent
mobile application

But create clean interfaces so they could be added later.

For example:

class BaseConnector:
    test_connection()
    discover()
    scan()

Implement:

PostgresConnector
CSVConnector
JSONConnector
DemoConnector

only.

94. BUSINESS MODEL UI

Add plan information internally, but do not build payment processing.

Plans:

STARTER
GROWTH
ENTERPRISE

Show feature limits conceptually:

data sources
users
scans
retention
reports
AI investigations

Do not implement Stripe overnight.

The purpose is to make the product architecture monetization-aware without introducing unnecessary integration risk.

95. SETTINGS

Settings pages:

Organization
Members
Roles
Connectors
Assessment Date
Regulatory Frameworks
Risk Model
AI Settings
Security
Audit Log
96. ORGANIZATION ONBOARDING

Create a simple onboarding flow:

Create organization
      ↓
Choose industry
      ↓
Select regulatory framework
      ↓
Connect first data source
      ↓
Run first scan
      ↓
View data map
      ↓
Review first findings

The demo should bypass this after login because the demo organization is already seeded.

97. FIRST-RUN EXPERIENCE

If no organization data exists:

show:

Welcome to ComplyGraph

Connect a data source to build your data inventory.

[Connect PostgreSQL]
[Upload CSV]
[Explore Demo]

"Explore Demo" should populate the fictional AsterLane organization.

98. EMPTY STATES

Every page needs a meaningful empty state.

Example:

No findings

Your current control assessment has no open findings.

[Run Scan]

Not:

No data
99. PERFORMANCE

Target:

dashboard API < 300ms
normal page load < 2s
asset list < 500ms
graph query < 1s for demo graph

Do not prematurely optimize.

Use:

pagination
indexes
selective joins
React query caching
100. DATA INTEGRITY

Use transactions where appropriate.

For a scan:

scan starts
↓
discover
↓
persist metadata
↓
evaluate controls
↓
generate findings
↓
commit transaction

If possible, do not leave partially updated scan state.

Update:

scan.status

on failure.

101. IDEMPOTENCY

Repeated scanning must not create:

duplicate assets
duplicate fields
duplicate controls
duplicate vendors

Use stable identifiers derived from:

connector
schema
table
field

For example:

sha256(
connector_id +
schema +
table +
column
)
102. FINDING DEDUPLICATION

If the same underlying problem is found again:

update the existing finding rather than creating a new duplicate.

Use a finding fingerprint.

Example:

hash(
control_id +
asset_id +
finding_type
)
103. AUDITABLE AI

Each AI investigation should show:

Investigation ID
Timestamp
Model
Input sanitized
Evidence used
Output
Human reviewer

AI output itself must be treated as an advisory artifact.

104. AI INVESTIGATION UI

Make it feel like a serious investigation console.

Example:

AI INVESTIGATION

Finding:
Unmanaged Customer Data Export

Evidence considered:
✓ scan-187
✓ asset-92
✓ control-RETENTION-001
✓ flow-42

Investigation:
████████████████████████ 100%

Conclusion:

The most likely cause is a marketing export
outside the documented retention workflow.

Confidence:
0.91

Recommended actions:

1. Identify export owner
2. Define retention rule
3. remove stale export
4. add recurring deletion verification

Legal review:
RECOMMENDED

Also provide:

View evidence

for every claim.

105. NO BLACK BOX AI

If AI says:

"Retention policy is missing"

the UI should show:

Evidence:
No retention policy attached to asset X.

Source:
control assessment #123

Do not present unsupported AI explanations.

106. SEARCHABLE REGULATORY LIBRARY

The user should be able to search:

retention
breach
consent
rights
security
children
vendor
cross-border

Each result:

Control code
Title
Framework
Effective date
Status
Legal reference
107. VENDOR RISK PAGE

Show:

Vendor
Country
Data categories
Purpose
Assets
Flows
Contract status
Risk level
Open findings

Example:

PulseMetrics Analytics

Personal-data flows:
3

Categories:
CONTACT
DEVICE
IDENTITY

Contract:
MISSING

Risk:
HIGH
108. PROCESSING ACTIVITY PAGE

Each activity:

Purpose
Owner
Data categories
Assets
Recipients
Vendors
Retention
Notice
Consent
Controls

This creates a bridge between business processes and technical systems.

109. DATA MAP FILTERS

Filters:

Personal data
High sensitivity
Third party
External
Cross border
Missing controls
High risk

Allow users to isolate:

"Show only personal data flowing to third-party vendors."

This should be a valuable demo moment.

110. CONTINUOUS CONTROL EVENT

Create a generic event:

ControlEvaluated

Data:

control_id
asset_id
status
score
evidence_ids
timestamp

This allows future streaming architecture.

111. DEMO SCENARIO 2

Implement a change scenario.

Initial state:

marketing_export.csv

Then the demo reset script can optionally add:

customer_address

to the export.

Re-run scan.

The system must show:

NEW PERSONAL DATA DETECTED

Field:
customer_address

Category:
LOCATION

Previous state:
Not present

Current state:
Detected

Create a finding automatically.

This demonstrates continuous governance.

112. DEMO SCENARIO 3

Retention failure.

Seed a failed cleanup state:

last_success:
2026-09-10

status:
FAILED

Control evaluator should detect:

RETENTION CONTROL FAILURE

AI investigator should explain:

The deletion process has not executed successfully.
113. DEMO SCENARIO 4

Evidence expiry.

Create:

security-review.pdf
expires_at = yesterday

Dashboard should show:

EXPIRED EVIDENCE

Control status becomes:

NEEDS_REVIEW
114. DEMO SCENARIO 5

Upcoming regulatory requirement.

Show a future control.

The dashboard should distinguish:

ACTIVE CONTROL GAP

from:

UPCOMING REQUIREMENT

This is mandatory.

115. REPORT DEMO

The report should show:

ASTERLANE TECHNOLOGIES

COMPLYGRAPH CONTROL ASSESSMENT

Assessment date:
2026-09-19

Data assets:
...

Personal-data assets:
...

Open findings:
...

Critical findings:
...

Evidence freshness:
...

Upcoming requirements:
...

Recommended next actions:
...

Footer:

Generated by ComplyGraph.
Internal governance/control assessment.
Not legal advice or certification.
116. CODE QUALITY

Use:

type hints
Pydantic models
clear service boundaries
small functions
meaningful names
error handling
tests
docstrings where logic is non-obvious

Avoid:

giant functions
global mutable state
duplicate business logic
magic numbers
frontend business logic duplicated from backend
117. NO PREMATURE ABSTRACTION

Do not build elaborate framework abstractions just to look enterprise-grade.

Build clear interfaces.

Keep the system understandable to another CSE student.

118. NO OVERENGINEERING

Do NOT introduce:

GraphQL
Kafka
Kubernetes
service mesh
event sourcing
CQRS framework
Elasticsearch
vector database

unless there is a concrete feature that requires it.

The overnight goal is:

depth > infrastructure theater
119. DEPLOYMENT

The application must run with:

docker compose up --build

Frontend:

http://localhost:3000

Backend:

http://localhost:8000

API docs:

http://localhost:8000/docs
120. ENVIRONMENT VARIABLES

Provide .env.example:

POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
DATABASE_URL
REDIS_URL

SECRET_KEY
APP_ENCRYPTION_KEY

ANTHROPIC_API_KEY
ANTHROPIC_MODEL
AI_MODE

NEXT_PUBLIC_API_URL

DEMO_MODE

Never commit .env.

121. API DOCUMENTATION

FastAPI OpenAPI must be complete.

Every endpoint needs:

description
request schema
response schema
status codes
auth requirement

Frontend should use typed API clients generated or manually typed from schemas.

122. TYPE SAFETY

Frontend:

strict TypeScript

Backend:

Python typing
Pydantic validation

No:

any

unless unavoidable and justified.

123. SEED SCRIPT

The seed script must:

create organization
create users
create roles
create regulations
create obligations
create controls
create connectors
create data assets
create fields
create vendors
create processing activities
create flows
create evidence
create assessments
create findings
create remediation tasks
create audit history
create demo incidents
create demo requests

It must be idempotent.

124. RESET SCRIPT

make demo-reset

must:

drop/recreate demo state
run migrations
seed demo data

and leave the system ready for demonstration.

125. SCREENSHOT QUALITY

The final UI must look complete without needing a custom branding exercise.

Use:

consistent spacing
meaningful typography
clear tables
good empty states
strong hover/focus states
responsive layout

Desktop must be excellent.

Mobile can be functional but desktop is priority.

126. LANDING PAGE

Create a polished public landing page.

Headline:

Know where your personal data goes.
Know which controls protect it.
Know what needs attention.

Subheading:

ComplyGraph continuously maps data assets, data flows,
controls and evidence so privacy and security teams
can identify and remediate governance gaps before they
become operational problems.

Do not use fake claims such as:

100% compliant
Government approved
Guaranteed DPDP compliance

Sections:

Data Discovery
Data Flow Mapping
Continuous Controls
Evidence
Risk & Findings
AI Investigation

CTA:

Explore Demo
127. PRODUCT BRANDING

Name:

ComplyGraph

Logo concept:

interconnected nodes forming a subtle shield / graph

Keep it professional.

No generic shield clip-art.

No excessive gradients.

128. ACCESSIBILITY

Implement:

keyboard navigation
ARIA labels
focus states
reasonable color contrast
semantic HTML

Charts need text summaries or accessible labels.

129. SECURITY HEADER BASELINE

Set:

Content-Security-Policy
X-Content-Type-Options
Referrer-Policy
Permissions-Policy

Use a sensible CSP that works with the application.

Do not disable security headers just to make development easier.

130. LOGGING POLICY

Logs may contain:

IDs
statuses
timestamps
durations
request IDs

Logs must not contain:

passwords
tokens
API keys
raw email
phone
address
full database credentials
raw evidence
131. DATA RETENTION INSIDE COMPLYGRAPH

This is an internal SaaS product, so define its own operational retention configuration.

Example:

audit logs:
365 days

scan history:
180 days

AI investigation artifacts:
90 days

Make these configurable.

Do not represent these defaults as legal requirements.

132. HEALTH CHECKS

API:

GET /health

Response:

{
  "status": "ok"
}

Readiness:

GET /ready

Check:

PostgreSQL
Redis
133. DATABASE BACKUP DEMO

Implement a manual database export command:

make db-backup

Use PostgreSQL's standard dump mechanism.

This is primarily a development/admin feature.

134. SEED DOCUMENT EVIDENCE

Generate synthetic evidence files:

privacy_policy.txt
security_policy.txt
retention_policy.txt
vendor_agreement.txt
incident_response_policy.txt
access_control_policy.txt

These are demo documents.

Do not copy legal text wholesale.

They should be generic fictional company documents.

135. EVIDENCE EXTRACTION

The overnight version does not need full document AI.

For seeded text evidence:

extract title
extract metadata
compute hash
associate with controls

If a PDF is uploaded:

store it
hash it
record metadata

Do not build a giant document OCR platform.

136. OPTIONAL AI DOCUMENT SUMMARY

If Anthropic is configured, allow:

Summarize evidence

But:

raw document contents

must be sanitized as appropriate.

The AI must never claim the document satisfies a legal requirement merely because a phrase appears.

137. CONTROL EVIDENCE MATRIX

Create an interface:

                 Evidence
Control      A      B      C      Status
-------------------------------------------
Security     ✓      ✓      -      PASS
Retention    ✓      -      -      PARTIAL
Vendor       -      -      -      NO EVIDENCE
Breach       ✓      ✓      ✓      PASS

This is a high-value auditor feature.

138. RISK HEATMAP

Create:

Sensitivity × Exposure

with findings plotted into cells.

Example:

             EXPOSURE
          1   2   3   4   5
       5  .   .   H   C   C
S      4  .   M   H   H   C
E      3  .   M   M   H   H
N      2  .   .   M   M   H
S      1  .   .   .   M   M

This is an internal risk visualization, not a legal classification.

139. DATA INVENTORY

Create an inventory table with:

Asset
Type
System
Owner
Data category
Sensitivity
Personal Data
Flows
Controls
Findings
Last Scan

Click asset → detail page.

140. PROCESSING PURPOSE LINKAGE

Allow a processing activity to link:

purpose
assets
vendors
flows
notice
consent
retention
controls

This is the business-to-technical bridge.

141. VENDOR FLOW ANALYSIS

A vendor with:

personal data flow
+
missing contract evidence

should automatically create:

vendor governance finding

The finding should show:

Vendor
Data categories
Source asset
Destination
Purpose
Evidence gap
142. CROSS-BORDER FLOW

If:

destination.country != organization.country

then:

cross_border = true

unless overridden.

Do not automatically label this illegal.

Create:

CROSS-BORDER REVIEW REQUIRED

when a relevant configured control applies.

143. CONTROL APPLICABILITY

Applicability can depend on:

asset contains personal data
organization industry
organization configuration
data category
vendor flow
assessment date
SDF status

Do not evaluate irrelevant controls against everything.

144. ASSESSMENT EXPLANATION

Every control assessment must provide a human-readable explanation.

Example:

FAIL

This control applies because the selected asset contains
personal data.

No retention policy was linked to the asset.
No successful deletion execution was recorded.

Evidence examined:
- asset-123
- scan-92

Action:
Define retention and attach verification evidence.
145. "WHY IS THIS A FINDING?" FEATURE

Every finding must have a "Why?" action.

Show:

Detection
Applicable control
Evidence
Calculation
Affected assets

This is critical for trust.

146. "WHAT CHANGED?" FEATURE

For findings created after a scan:

What changed?

Before:
No marketing export

After:
marketing_export.csv detected

Difference:
email + phone fields
147. "SHOW ME MY DATA" FEATURE

A user should be able to start from:

email

and see:

where it exists
what processes use it
what vendors receive it
what controls apply
what findings exist

This is one of the strongest graph capabilities.

148. DATA SUBJECT JOURNEY

For a synthetic user:

customer@example.com

show:

Customer DB
     ↓
Order system
     ↓
Marketing export
     ↓
Analytics vendor

Then:

Data categories:
CONTACT
IDENTITY
DEVICE

This makes the graph intuitive for non-technical privacy staff.

149. AUDIT PACKAGE

Add:

Generate audit package

The package should include:

control status
evidence metadata
finding list
asset inventory
vendor inventory
audit events

Export as ZIP containing CSV/JSON/PDF files.

150. DEMO STORY FOR FINAL PRESENTATION

The application should support the following 5-minute story.

Minute 1

Login.

Show dashboard.

327 personal-data assets
18 critical findings
11 stale evidence items
Minute 2

Open data map.

Show:

Customer DB
→ marketing ETL
→ CSV
→ analytics vendor

Click vendor.

Show personal data categories.

Minute 3

Open finding:

Unmanaged Customer Data Export

Show evidence and control.

Minute 4

Run:

AI Investigation

Show evidence-backed explanation and remediation.

Minute 5

Resolve issue.

Generate report.

Open audit log.

This is the target demo.

151. FINAL SYSTEM ACCEPTANCE CRITERIA

The project is NOT finished until all of the following are true.

Infrastructure
Docker Compose starts successfully.
PostgreSQL works.
Redis works.
API works.
Worker works.
Frontend works.
Authentication
Login works.
Logout works.
Role-based authorization works.
Cross-tenant authorization works.
Data Discovery
PostgreSQL scan works.
CSV scan works.
JSON scan works.
PII classification works.
Scan history works.
Scan changes are detected.
Graph
Data map works.
Node detail works.
Edge detail works.
Filters work.
Personal-data-only filtering works.
Regulatory
DPDP framework is seeded.
Obligations exist.
Controls exist.
Legal references exist.
Effective dates exist.
Upcoming controls are not treated as active failures.
Controls
Control evaluators work.
Evidence links work.
Assessments work.
Findings are created.
Findings
Findings list works.
Finding detail works.
Assignment works.
Remediation workflow works.
Risk acceptance works.
Resolution works.
Evidence
Upload works.
Hashing works.
Linking works.
Freshness works.
Evidence matrix works.
Vendors
Vendor management works.
Vendor flow mapping works.
Vendor findings work.
Data Requests
Request workflow works.
Assignment works.
Verification state works.
Completion works.
Breaches
Incident creation works.
Timeline works.
Notification state works.
Closure works.
AI
Anthropic integration works when configured.
Deterministic fallback works without API key.
AI output is schema validated.
AI requests are sanitized.
AI cannot directly change compliance state.
Investigation results are stored.
Evidence can be traced from AI output.
Reports
Executive report works.
Findings report works.
Evidence report works.
Audit report works.
PDF export works.
Audit
Mutations generate audit events.
Audit log is searchable/filterable.
Testing
Unit tests pass.
Integration tests pass.
E2E tests pass.
Security tests pass.
Full check passes.
152. NO PLACEHOLDER POLICY

Before declaring completion, search the repository for:

TODO
FIXME
coming soon
not implemented
placeholder
mock implementation
temporary
later
future work

Do not leave functional features with those markers.

Documentation can contain a "Future Roadmap" section, but application code must not rely on unfinished implementations.

153. NO DEAD BUTTONS

Every visible button must do something.

If an action is unavailable:

disable it
+
explain why

Do not create decorative buttons.

154. NO FAKE METRICS

Every metric on the dashboard must have a database/API origin.

No fake hardcoded dashboard statistics.

Demo seed data may produce meaningful numbers.

155. NO FAKE AI

When AI mode is enabled:

real Anthropic API call

When AI mode is disabled:

deterministic fallback

Clearly indicate which mode is being used.

156. FINAL OVERNIGHT EXECUTION ORDER

Follow this order.

PHASE 1 — FOUNDATION

Implement:

repo
Docker
Postgres
Redis
FastAPI
Next.js
Alembic
environment configuration
health checks

Then run.

Do not continue with broken infrastructure.

PHASE 2 — AUTH + TENANCY

Implement:

users
organization
memberships
roles
sessions
authorization

Add tests.

PHASE 3 — CORE DATA MODEL

Implement:

connectors
assets
fields
flows
vendors
processing activities

Add migration and repositories.

PHASE 4 — SCANNER

Implement:

Postgres scanner
CSV scanner
JSON scanner
PII classifier
scan jobs
change detection

Add integration tests.

PHASE 5 — REGULATORY ENGINE

Implement:

regulations
obligations
controls
effective dates
applicability
assessment engine

Seed DPDP data.

PHASE 6 — EVIDENCE

Implement:

evidence
control_evidence
freshness
hashing
upload
PHASE 7 — FINDINGS/RISK

Implement:

findings
risk score
deduplication
remediation
tasks
PHASE 8 — GRAPH

Implement:

unified graph endpoint
React Flow visualization
filters
asset detail
flow detail
PHASE 9 — DATA REQUESTS + BREACHES

Implement operational workflows.

PHASE 10 — AI

Implement:

Anthropic adapter
prompt
sanitization
Pydantic output schema
investigation storage
fallback
UI
PHASE 11 — REPORTING

Implement:

CSV
JSON
PDF
executive report
audit package
PHASE 12 — POLISH

Implement:

landing page
dashboard
loading states
empty states
error states
responsive layout
icons
navigation
search
filters
PHASE 13 — TESTING

Run:

unit
integration
security
E2E

Fix all failures.

PHASE 14 — FULL SYSTEM VALIDATION

Run:

make demo-reset
make full-check

Then manually verify the complete five-minute demo flow.

157. IF TIME BECOMES LIMITED

If execution time becomes constrained, prioritize in this order:

1. Working application startup
2. Authentication
3. Database
4. Scanner
5. PII classification
6. Regulatory/control engine
7. Findings
8. Data graph
9. Evidence
10. Dashboard
11. AI investigator
12. Reports
13. Secondary workflows
14. visual polish

Do NOT spend the final hour polishing the landing page while the scanner or control engine is broken.

158. FINAL QUALITY BAR

Before completion, ask yourself:

Can a new user start the application with one command?

Can they immediately understand what it does?

Can they connect a synthetic database?

Does the system actually discover personal-data fields?

Does it actually build a data map?

Does the map show personal data flows?

Does the system actually evaluate controls?

Are findings based on deterministic evidence?

Can the user inspect why each finding exists?

Can evidence be attached?

Can findings be remediated?

Can the same system show upcoming vs active obligations?

Can AI investigate a finding without receiving raw PII?

Can the complete workflow be demonstrated without external credentials?

Can the whole system be tested automatically?

Does another developer understand the architecture?

Does the UI look like a serious B2B security product?

Would a privacy officer understand it?

Would an engineer understand it?

Would a CISO understand the executive summary?

If any answer is "no", fix it before declaring completion.

159. FINAL REQUIRED OUTPUT FROM CLAUDE

When the build is genuinely finished, do not simply say:

Done.

Return a structured final report:

COMPLYGRAPH BUILD COMPLETE

Repository:
...

Architecture:
...

Services:
...

Implemented Features:
...

Database:
...

Regulatory Framework:
...

Scanner:
...

Data Graph:
...

Controls:
...

Evidence:
...

Findings:
...

AI:
...

Reports:
...

Security:
...

Tests:
...

E2E:
...

Demo Credentials:
...

Startup Command:
...

Known Limitations:
...

Verification:
PASS / FAIL

Also include:

Number of files created
Number of tests
Number of API endpoints
Number of database tables
Number of seeded controls
Number of seeded findings

Only claim numbers that you actually measured from the repository.

160. ABSOLUTE FINAL INSTRUCTION

Do not optimize for producing an impressive-looking repository.

Optimize for:

WORKING SYSTEM
+
REAL DATA FLOW
+
REAL CONTROL EVALUATION
+
REAL EVIDENCE
+
REAL FINDINGS
+
REAL GRAPH
+
REAL SECURITY
+
REAL TESTS
+
REAL AI INVESTIGATION

The final result should feel like a small but serious commercial privacy/data-governance product that happens to be implemented as a capstone project.

It must be possible to demonstrate the complete system locally without external infrastructure.

Build continuously until the acceptance criteria are satisfied.

Do not stop at scaffolding.

Do not ask what to implement next.

Do not replace difficult features with placeholder UI.

Do not invent regulatory requirements.

Do not expose raw personal data to the AI.

Do not claim legal compliance.

Finish the system.


A few design choices in that spec are deliberate. The **regulatory engine is date-aware** because the 2025 Rules have phased commencement; the Gazette explicitly puts Rule 4 one year after publication and Rules 3, 5–16, 22 and 23 eighteen months after publication. :contentReference[oaicite:1]{index=1} The security, breach, retention, children’s-data, SDF and rights modules are grounded in the actual Rules rather than invented feature requirements. :contentReference[oaicite:2]{index=2}

This is also why the project is more defensible commercially: existing platforms such as OneTrust already offer DPDPA compliance, consent, rights-request and compliance-automation functionality, so **ComplyGraph needs to differentiate around continuous technical data discovery → data-flow graph → deterministic control evaluation → evidence → remediation**, rather than becoming another checklist product. :contentReference[oaicite:3]{index=3}

**For the overnight run, paste the specification exactly as the master instruction, then let Claude execute 