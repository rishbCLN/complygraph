"""All ORM models. Importing this package registers every table on Base.metadata."""

from app.models.ai_systems import (
    AISystem,
    AISystemComponent,
    AISystemFlow,
    AISystemSnapshot,
)
from app.models.approval import ApprovalRequest
from app.models.campaign import AuditCampaign, CampaignResult
from app.models.consent import (
    ConsentEvent,
    ConsentNotice,
    ConsentPurpose,
    ConsentRecord,
)
from app.models.dsr import DSRTask
from app.models.evidence import ControlEvidence, Evidence
from app.models.findings import Finding, RemediationTask, Scan, ScanResult
from app.models.identity import (
    AuditEvent,
    Membership,
    Organization,
    Session,
    User,
)
from app.models.inventory import (
    AssetField,
    ClassificationOverride,
    Connector,
    DataAsset,
    DataFlow,
    ProcessingActivity,
    Vendor,
)
from app.models.operations import AIInvestigation, BreachIncident, DataSubjectRequest
from app.models.risk import Risk
from app.models.regulatory import (
    Control,
    ControlAssessment,
    ControlAssetScope,
    ControlMapping,
    Obligation,
    Regulation,
)

__all__ = [
    "AIInvestigation",
    "AISystem",
    "AISystemComponent",
    "AISystemFlow",
    "AISystemSnapshot",
    "ApprovalRequest",
    "AssetField",
    "AuditCampaign",
    "CampaignResult",
    "AuditEvent",
    "BreachIncident",
    "ClassificationOverride",
    "ConsentEvent",
    "ConsentNotice",
    "ConsentPurpose",
    "ConsentRecord",
    "Connector",
    "Control",
    "ControlAssessment",
    "ControlAssetScope",
    "ControlEvidence",
    "ControlMapping",
    "DataAsset",
    "DataFlow",
    "DataSubjectRequest",
    "DSRTask",
    "Evidence",
    "Finding",
    "Membership",
    "Obligation",
    "Organization",
    "ProcessingActivity",
    "Regulation",
    "RemediationTask",
    "Risk",
    "Scan",
    "ScanResult",
    "Session",
    "User",
    "Vendor",
]
