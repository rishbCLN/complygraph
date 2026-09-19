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


class ControlStatus(str, Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    NO_EVIDENCE = "NO_EVIDENCE"
    UPCOMING = "UPCOMING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


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


class AIInvestigationStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class OwnerType(str, Enum):
    PRIVACY = "PRIVACY"
    SECURITY = "SECURITY"
    ENGINEERING = "ENGINEERING"
    LEGAL = "LEGAL"
    BUSINESS = "BUSINESS"
