"""Role-based access control matrix.

Permissions are coarse-grained capability strings. Each role maps to a set of
capabilities. Endpoints declare a required capability via the require_capability
dependency.
"""

from __future__ import annotations

from app.core.enums import Role

# Capability constants
VIEW = "view"
MANAGE_INVENTORY = "manage_inventory"  # assets, flows, vendors, processing activities
MANAGE_CONNECTORS = "manage_connectors"
RUN_SCAN = "run_scan"
MANAGE_FINDINGS = "manage_findings"  # assign, resolve, accept risk
MANAGE_EVIDENCE = "manage_evidence"  # upload/link
DELETE_EVIDENCE = "delete_evidence"
ASSESS_CONTROLS = "assess_controls"
MANAGE_REGULATORY = "manage_regulatory"  # enable frameworks, change legal mappings
MANAGE_MEMBERS = "manage_members"
MANAGE_ORG = "manage_org"  # org settings, assessment date
MANAGE_DSR = "manage_dsr"
MANAGE_BREACH = "manage_breach"
RUN_AI = "run_ai"
GENERATE_REPORTS = "generate_reports"
MANAGE_TASKS = "manage_tasks"

_ALL = {
    VIEW,
    MANAGE_INVENTORY,
    MANAGE_CONNECTORS,
    RUN_SCAN,
    MANAGE_FINDINGS,
    MANAGE_EVIDENCE,
    DELETE_EVIDENCE,
    ASSESS_CONTROLS,
    MANAGE_REGULATORY,
    MANAGE_MEMBERS,
    MANAGE_ORG,
    MANAGE_DSR,
    MANAGE_BREACH,
    RUN_AI,
    GENERATE_REPORTS,
    MANAGE_TASKS,
}

ROLE_CAPABILITIES: dict[str, set[str]] = {
    Role.OWNER.value: set(_ALL),
    Role.ADMIN.value: set(_ALL),
    Role.PRIVACY_OFFICER.value: {
        VIEW,
        MANAGE_INVENTORY,
        MANAGE_CONNECTORS,
        RUN_SCAN,
        MANAGE_FINDINGS,
        MANAGE_EVIDENCE,
        ASSESS_CONTROLS,
        MANAGE_DSR,
        MANAGE_BREACH,
        RUN_AI,
        GENERATE_REPORTS,
        MANAGE_TASKS,
    },
    Role.SECURITY_ANALYST.value: {
        VIEW,
        RUN_SCAN,
        MANAGE_FINDINGS,
        MANAGE_EVIDENCE,
        ASSESS_CONTROLS,
        MANAGE_BREACH,
        RUN_AI,
        GENERATE_REPORTS,
        MANAGE_TASKS,
    },
    Role.ENGINEER.value: {
        VIEW,
        MANAGE_EVIDENCE,
        MANAGE_TASKS,
    },
    Role.AUDITOR.value: {
        VIEW,
        GENERATE_REPORTS,
    },
    Role.VIEWER.value: {VIEW},
}


def has_capability(role: str, capability: str) -> bool:
    return capability in ROLE_CAPABILITIES.get(role, set())
