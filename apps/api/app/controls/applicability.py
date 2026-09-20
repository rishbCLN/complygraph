"""Control applicability engine.

Decides *whether* a control applies to an organization's AI systems before the
deterministic evaluator decides *how well* it is met. This is the core of the AI
Compliance Compiler: a control is scoped to sectors / AI-system types / declared
conditions via its ``applies_to`` map, and matched against the machine-readable
facts derived from each AI system's architecture.

Design rules:
  - Applicability is computed from explicitly declared or structurally derived
    facts only (see ai_system_service.derive_facts). Nothing is inferred.
  - A control with no ``applies_to`` (or an empty one) is *not* AI-scoped; it
    keeps the existing org-level behavior. Only controls that declare scoping
    are routed through the AI-system matcher.
  - When a control is AI-scoped but no system matches, it is NOT_APPLICABLE with
    an explicit reason (never a blanket NO_EVIDENCE).
"""

from __future__ import annotations

# Condition tokens used in control ``applies_to`` maps -> the fact key produced
# by ai_system_service.derive_facts. Keeps the pack vocabulary readable while
# the derived facts stay explicit.
_CONDITION_ALIASES = {
    "automated_decisions": "makes_automated_decisions",
    "processes_personal_data": "processes_personal_data",
    "makes_automated_decisions": "makes_automated_decisions",
    "high_risk": "high_risk",
    "has_vendors": "has_vendors",
    "has_external_components": "has_external_components",
    "has_external_inference": "has_external_inference",
    "uses_external_observability": "uses_external_observability",
    "has_cross_border_flow": "has_cross_border_flow",
    "is_production": "is_production",
}

_WILDCARDS = {"all", "any", "*"}


def _norm_set(values) -> set[str]:
    return {str(v).strip().lower() for v in (values or []) if str(v).strip()}


def is_ai_scoped(applies_to: dict | None) -> bool:
    """True when a control declares AI-system scoping worth routing through here.

    A control is AI-scoped if it names any sector, ai_type, or condition (even a
    wildcard sector/type). An entirely empty/absent map is org-level.
    """
    if not applies_to:
        return False
    return bool(
        applies_to.get("sectors")
        or applies_to.get("ai_types")
        or applies_to.get("conditions")
    )


def is_specific_scope(applies_to: dict | None) -> bool:
    """True when a control narrows to specific systems (named sector/type or any condition).

    A fully-wildcard scope (e.g. sectors=["all"], ai_types=["all"], conditions=[])
    is org-wide: it should run its evaluator regardless of whether any AI system is
    inventoried. A specific scope gates on a matching system (NOT_APPLICABLE if none).
    """
    if not applies_to:
        return False
    sectors = _norm_set(applies_to.get("sectors"))
    ai_types = _norm_set(applies_to.get("ai_types"))
    has_conditions = bool(applies_to.get("conditions"))
    named_sector = bool(sectors) and not (sectors & _WILDCARDS)
    named_type = bool(ai_types) and not (ai_types & _WILDCARDS)
    return named_sector or named_type or has_conditions


def _sector_matches(applies_to: dict, facts: dict) -> bool:
    sectors = _norm_set(applies_to.get("sectors"))
    if not sectors or sectors & _WILDCARDS:
        return True
    return (facts.get("sector") or "").strip().lower() in sectors


def _type_matches(applies_to: dict, facts: dict) -> bool:
    ai_types = _norm_set(applies_to.get("ai_types"))
    if not ai_types or ai_types & _WILDCARDS:
        return True
    return (facts.get("system_type") or "").strip().lower() in ai_types


def _conditions_match(applies_to: dict, facts: dict) -> bool:
    """Every declared condition must be a truthy fact on the system."""
    for cond in applies_to.get("conditions") or []:
        fact_key = _CONDITION_ALIASES.get(str(cond).strip().lower(), str(cond).strip().lower())
        if not facts.get(fact_key):
            return False
    return True


def system_matches(applies_to: dict, facts: dict) -> bool:
    """True when a single AI system (via its derived facts) is in scope."""
    return (
        _sector_matches(applies_to, facts)
        and _type_matches(applies_to, facts)
        and _conditions_match(applies_to, facts)
    )


def applicable_systems(applies_to: dict | None, systems_facts: list[dict]) -> list[dict]:
    """Return the subset of AI systems (fact dicts) a control applies to.

    ``systems_facts`` is the list of derived-fact dicts (one per AI system) carried
    on the ControlContext. Wildcard/absent scope matches every inventoried system;
    an empty inventory yields an empty list (the evaluator decides what that means).
    """
    ap = applies_to or {}
    return [f for f in systems_facts if system_matches(ap, f)]
