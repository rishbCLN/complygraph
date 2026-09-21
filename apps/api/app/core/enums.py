"""Shared enumerations used across models, schemas, and services.

Kept as plain string constants (str, Enum) so they serialize cleanly to JSON
and map directly to PostgreSQL string columns.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    PRIVACY_OFFICER = "PRIVACY_OFFICER"
    SECURITY_ANALYST = "SECURITY_ANALYST"
    ENGINEER = "ENGINEER"
    AUDITOR = "AUDITOR"
    VIEWER = "VIEWER"


class ConnectorType(str, Enum):
    POSTGRES = "POSTGRES"
    CSV = "CSV"
    JSON = "JSON"
    DEMO = "DEMO"
    CODEBASE = "CODEBASE"


class ConnectorStatus(str, Enum):
    CONFIGURED = "CONFIGURED"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"
    DISABLED = "DISABLED"


class AssetType(str, Enum):
    DATABASE = "DATABASE"
    TABLE = "TABLE"
    FILE = "FILE"
    API = "API"
    SAAS = "SAAS"
    BUCKET = "BUCKET"
    DATASET = "DATASET"
    APPLICATION = "APPLICATION"


class Classification(str, Enum):
    PERSONAL_DATA = "PERSONAL_DATA"
    SENSITIVE_PERSONAL_DATA = "SENSITIVE_PERSONAL_DATA"
    OPERATIONAL_METADATA = "OPERATIONAL_METADATA"
    NON_PERSONAL = "NON_PERSONAL"
    UNKNOWN = "UNKNOWN"


class DataCategory(str, Enum):
    IDENTITY = "IDENTITY"
    CONTACT = "CONTACT"
    LOCATION = "LOCATION"
    FINANCIAL = "FINANCIAL"
    HEALTH = "HEALTH"
    AUTHENTICATION = "AUTHENTICATION"
    DEVICE = "DEVICE"
    BEHAVIORAL = "BEHAVIORAL"
    PROFESSIONAL = "PROFESSIONAL"
    OTHER_PERSONAL = "OTHER_PERSONAL"
    NON_PERSONAL = "NON_PERSONAL"
    UNKNOWN = "UNKNOWN"


class ConfidenceBand(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FactConfidence(str, Enum):
    """Provenance of an applicability fact: HOW the engine knows it.

    An audit conclusion is only as trustworthy as the facts under it. A
    localisation FAIL built on a DECLARED region is far more defensible than a
    NO_EVIDENCE built on INFERRED absence of a component, which may just mean the
    architecture was never fully recorded. The engine reports this distinction so
    a reviewer can tell "we checked and it's true" from "we didn't find it".
    """

    DECLARED = "DECLARED"  # explicitly asserted on the system record (certain)
    OBSERVED = "OBSERVED"  # positively derived from a concrete component/flow
    INFERRED = "INFERRED"  # derived from ABSENCE of evidence (weaker)
    UNKNOWN = "UNKNOWN"  # no basis to determine (e.g. no architecture recorded)

    @property
    def band(self) -> "ConfidenceBand":
        return {
            "DECLARED": ConfidenceBand.HIGH,
            "OBSERVED": ConfidenceBand.HIGH,
            "INFERRED": ConfidenceBand.MEDIUM,
            "UNKNOWN": ConfidenceBand.LOW,
        }[self.value]


class FlowType(str, Enum):
    INTERNAL = "INTERNAL"
    PROCESSOR = "PROCESSOR"
    THIRD_PARTY = "THIRD_PARTY"
    ANALYTICS = "ANALYTICS"
    EXPORT = "EXPORT"
    BACKUP = "BACKUP"
    ARCHIVE = "ARCHIVE"


class RegulationStatus(str, Enum):
    IN_FORCE = "IN_FORCE"
    UPCOMING = "UPCOMING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    RETIRED = "RETIRED"


class LegalStatus(str, Enum):
    """The legal/institutional weight of an obligation.

    These MUST NOT be collapsed into a single generic "law" label. DPDP, RBI,
    CERT-In and MeitY materials carry different legal force and the product must
    represent that distinction honestly (see AI Compliance Compiler spec s.2).
    """

    BINDING_LAW = "BINDING_LAW"  # primary legislation (e.g. DPDP Act)
    BINDING_RULE = "BINDING_RULE"  # subordinate rules with legal force (e.g. DPDP Rules)
    REGULATORY_DIRECTION = "REGULATORY_DIRECTION"  # binding sectoral direction (e.g. RBI/CERT-In directions)
    REGULATOR_EXPECTATION = "REGULATOR_EXPECTATION"  # supervisory expectation, not codified
    FORMAL_FRAMEWORK = "FORMAL_FRAMEWORK"  # published committee/framework material (e.g. RBI FREE-AI report)
    GUIDANCE = "GUIDANCE"  # advisory guidance (e.g. MeitY AI governance guidelines)
    BEST_PRACTICE = "BEST_PRACTICE"  # industry best practice
    INTERNAL_POLICY = "INTERNAL_POLICY"  # organization's own policy


class CitationStatus(str, Enum):
    """Whether a requirement's source citation has been verified against source text."""

    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"  # surfaced as "HUMAN REVIEW REQUIRED" in the UI


class ApplicabilityStatus(str, Enum):
    APPLICABLE = "APPLICABLE"
    POTENTIALLY_APPLICABLE = "POTENTIALLY_APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ControlStatus(str, Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    NO_EVIDENCE = "NO_EVIDENCE"
    UPCOMING = "UPCOMING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class AISystemStage(str, Enum):
    """Lifecycle stage of an AI system (see AI Compliance Compiler spec s.8.2)."""

    IDEA = "IDEA"
    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING"
    PILOT = "PILOT"
    PRODUCTION = "PRODUCTION"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


class AISystemReviewStatus(str, Enum):
    """Whether an AI system's compliance posture has a documented human review.

    A PRODUCTION system with NOT_REVIEWED status is itself a governance gap
    (demo scenario: "Production system missing documented review state").
    """

    NOT_REVIEWED = "NOT_REVIEWED"
    IN_REVIEW = "IN_REVIEW"
    REVIEWED = "REVIEWED"
    NEEDS_RE_REVIEW = "NEEDS_RE_REVIEW"


class AISystemType(str, Enum):
    """Coarse system archetype used by the applicability engine (`ai_types`)."""

    ML_MODEL = "ML_MODEL"  # classical/predictive model (e.g. fraud scoring)
    LLM = "LLM"  # large-language-model application
    GENERATIVE = "GENERATIVE"  # broader generative (text/image/audio)
    RAG = "RAG"  # retrieval-augmented generation
    AGENTIC = "AGENTIC"  # tool-using agent that can act
    HYBRID = "HYBRID"  # combination of the above
    OTHER = "OTHER"


class ComponentType(str, Enum):
    """Architecture-graph node kinds for an AI system's components."""

    MODEL = "MODEL"
    AGENT = "AGENT"
    DATASET = "DATASET"
    DATA_STORE = "DATA_STORE"
    DATA_CATEGORY = "DATA_CATEGORY"
    API = "API"
    SERVICE = "SERVICE"
    VENDOR = "VENDOR"
    USER_GROUP = "USER_GROUP"
    ENDPOINT = "ENDPOINT"


class ArchEdgeRelation(str, Enum):
    """Directed relationships between AI-system components (architecture edges)."""

    PROCESSES = "PROCESSES"
    STORES = "STORES"
    SENDS_TO = "SENDS_TO"
    HOSTED_BY = "HOSTED_BY"
    OPERATED_BY = "OPERATED_BY"
    ACCESSED_BY = "ACCESSED_BY"
    GENERATES = "GENERATES"
    DEPENDS_ON = "DEPENDS_ON"


class EvidenceType(str, Enum):
    DOCUMENT = "DOCUMENT"
    CONFIGURATION = "CONFIGURATION"
    SCAN_RESULT = "SCAN_RESULT"
    LOG = "LOG"
    SCREENSHOT = "SCREENSHOT"
    POLICY = "POLICY"
    TICKET = "TICKET"
    API_RESPONSE = "API_RESPONSE"
    DATABASE_CHECK = "DATABASE_CHECK"
    MANUAL_ATTESTATION = "MANUAL_ATTESTATION"


class EvidenceStatus(str, Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class EvidenceRelation(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    PARTIAL = "PARTIAL"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    ACCEPTED_RISK = "ACCEPTED_RISK"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    DONE = "DONE"


class Priority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ScanStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DSRType(str, Enum):
    ACCESS = "ACCESS"
    CORRECTION = "CORRECTION"
    ERASURE = "ERASURE"
    NOMINATION = "NOMINATION"
    GRIEVANCE = "GRIEVANCE"
    WITHDRAW_CONSENT = "WITHDRAW_CONSENT"


class DSRStatus(str, Enum):
    REQUESTED = "REQUESTED"
    IDENTITY_VERIFICATION = "IDENTITY_VERIFICATION"
    IN_PROGRESS = "IN_PROGRESS"
    FULFILLED = "FULFILLED"
    REJECTED = "REJECTED"


class ConsentStatus(str, Enum):
    """Current state of a data principal's consent for one purpose."""

    GRANTED = "GRANTED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"


class ConsentMethod(str, Enum):
    """How a consent action was captured (DPDP requires a clear affirmative act)."""

    PRIVACY_CENTER = "PRIVACY_CENTER"  # data principal self-service portal
    STAFF_RECORDED = "STAFF_RECORDED"  # entered by an operator on the principal's behalf
    IMPORT = "IMPORT"  # migrated from an external system
    API = "API"  # captured via integration


class ConsentEventType(str, Enum):
    """Append-only ledger event kinds."""

    GRANTED = "GRANTED"
    WITHDRAWN = "WITHDRAWN"
    RENEWED = "RENEWED"
    EXPIRED = "EXPIRED"


class PurposeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class BreachStatus(str, Enum):
    DETECTED = "DETECTED"
    INVESTIGATING = "INVESTIGATING"
    CONTAINED = "CONTAINED"
    NOTIFICATION_PENDING = "NOTIFICATION_PENDING"
    NOTIFIED = "NOTIFIED"
    CLOSED = "CLOSED"


class NotificationStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class NotificationState(str, Enum):
    """Lifecycle of an in-app notification."""

    UNREAD = "UNREAD"
    READ = "READ"
    DISMISSED = "DISMISSED"


class NotificationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class NotificationKind(str, Enum):
    """What produced a notification (drives icon/grouping and dedupe keys)."""

    EVIDENCE_EXPIRING = "EVIDENCE_EXPIRING"
    EVIDENCE_EXPIRED = "EVIDENCE_EXPIRED"
    FINDING_OVERDUE = "FINDING_OVERDUE"
    TASK_OVERDUE = "TASK_OVERDUE"
    DSR_DUE = "DSR_DUE"
    DSR_OVERDUE = "DSR_OVERDUE"
    RISK_REVIEW_DUE = "RISK_REVIEW_DUE"
    CONTROL_REASSESS_DUE = "CONTROL_REASSESS_DUE"
    REASSESSMENT_COMPLETE = "REASSESSMENT_COMPLETE"
    ASSESSMENT_REGRESSED = "ASSESSMENT_REGRESSED"


class AIInvestigationStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WebhookEvent(str, Enum):
    """Domain events an outbound webhook endpoint can subscribe to."""

    FINDING_CREATED = "finding.created"
    FINDING_RESOLVED = "finding.resolved"
    RISK_CREATED = "risk.created"
    RISK_STATUS_CHANGED = "risk.status_changed"
    DSR_CREATED = "dsr.created"
    DSR_FULFILLED = "dsr.fulfilled"
    BREACH_CREATED = "breach.created"
    ASSESSMENT_REGRESSED = "assessment.regressed"
    CONTROL_REASSESSED = "control.reassessed"


class WebhookDeliveryStatus(str, Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class TicketProvider(str, Enum):
    JIRA = "JIRA"
    SERVICENOW = "SERVICENOW"


class TicketStatus(str, Enum):
    """Local mirror of an external ticket's lifecycle (best-effort, not authoritative)."""

    OPEN = "OPEN"
    CREATED = "CREATED"
    FAILED = "FAILED"


class SSOProtocol(str, Enum):
    OIDC = "OIDC"
    SAML = "SAML"


class OwnerType(str, Enum):
    PRIVACY = "PRIVACY"
    SECURITY = "SECURITY"
    ENGINEERING = "ENGINEERING"
    LEGAL = "LEGAL"
    BUSINESS = "BUSINESS"


class RiskStatus(str, Enum):
    IDENTIFIED = "IDENTIFIED"
    ASSESSED = "ASSESSED"
    TREATING = "TREATING"
    ACCEPTED = "ACCEPTED"
    MITIGATED = "MITIGATED"
    CLOSED = "CLOSED"


class RiskCategory(str, Enum):
    PRIVACY = "PRIVACY"
    SECURITY = "SECURITY"
    OPERATIONAL = "OPERATIONAL"
    COMPLIANCE = "COMPLIANCE"
    VENDOR = "VENDOR"
    AI = "AI"
    FINANCIAL = "FINANCIAL"
    REPUTATIONAL = "REPUTATIONAL"


class TreatmentStrategy(str, Enum):
    """ISO 31000-style risk treatment options."""

    MITIGATE = "MITIGATE"  # reduce likelihood/impact via controls
    ACCEPT = "ACCEPT"  # tolerate with documented rationale
    TRANSFER = "TRANSFER"  # insure / contractually shift
    AVOID = "AVOID"  # stop the activity


def risk_severity(score: int) -> str:
    """Map a 1..25 likelihood*impact score to a severity band."""
    if score >= 20:
        return "CRITICAL"
    if score >= 12:
        return "HIGH"
    if score >= 6:
        return "MEDIUM"
    return "LOW"


class MappingRelation(str, Enum):
    """How a source control relates to a target control in another framework.

    Direction matters for evidence reuse: evidence proving the SOURCE control can
    be *reused* to help satisfy the TARGET control only when the source fully
    covers the target (EQUIVALENT or SUPERSET). RELATED / SUBSET mappings are
    informational and always require human review before reuse.
    """

    EQUIVALENT = "EQUIVALENT"  # source and target require the same thing
    SUPERSET = "SUPERSET"  # source is broader; satisfying it satisfies the target
    SUBSET = "SUBSET"  # source is narrower; only partially covers the target
    RELATED = "RELATED"  # thematically related, no coverage claim

    @property
    def source_covers_target(self) -> bool:
        """Whether satisfying the source control can, subject to review, satisfy the target."""
        return self in (MappingRelation.EQUIVALENT, MappingRelation.SUPERSET)
