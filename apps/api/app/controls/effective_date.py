"""Effective-date engine.

Determines whether a control/obligation is active or upcoming relative to a
configurable assessment date. Today's date is never hard-coded into evaluators.
"""

from __future__ import annotations

from datetime import datetime, timezone


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def is_control_active(control_effective_from: datetime | None, assessment_date: datetime) -> bool:
    """Return True when the control is in force at the assessment date."""
    if control_effective_from is None:
        return True
    return _aware(control_effective_from) <= _aware(assessment_date)


def control_temporal_status(
    control_effective_from: datetime | None, assessment_date: datetime
) -> str:
    """Return 'active' or 'upcoming'."""
    return "active" if is_control_active(control_effective_from, assessment_date) else "upcoming"


def regulation_status(effective_from: datetime | None, assessment_date: datetime) -> str:
    """Map to IN_FORCE / UPCOMING for display."""
    from app.core.enums import RegulationStatus

    if effective_from is None:
        return RegulationStatus.IN_FORCE.value
    return (
        RegulationStatus.IN_FORCE.value
        if is_control_active(effective_from, assessment_date)
        else RegulationStatus.UPCOMING.value
    )
