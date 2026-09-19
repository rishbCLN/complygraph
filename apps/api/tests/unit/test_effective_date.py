"""Unit tests for the effective-date engine.

Controls/regulations are active or upcoming relative to a configurable
assessment date. Today's date is never hard-coded into evaluators.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.controls.effective_date import (
    control_temporal_status,
    is_control_active,
    regulation_status,
)
from app.core.enums import RegulationStatus

ASSESSMENT = datetime(2026, 9, 19, tzinfo=timezone.utc)


def test_no_effective_date_is_always_active():
    assert is_control_active(None, ASSESSMENT) is True
    assert control_temporal_status(None, ASSESSMENT) == "active"


def test_past_effective_date_is_active():
    past = datetime(2023, 8, 11, tzinfo=timezone.utc)
    assert is_control_active(past, ASSESSMENT) is True
    assert control_temporal_status(past, ASSESSMENT) == "active"


def test_future_effective_date_is_upcoming():
    future = datetime(2027, 5, 13, tzinfo=timezone.utc)
    assert is_control_active(future, ASSESSMENT) is False
    assert control_temporal_status(future, ASSESSMENT) == "upcoming"


def test_same_day_is_active():
    assert is_control_active(ASSESSMENT, ASSESSMENT) is True


def test_naive_datetime_is_treated_as_utc():
    naive_past = datetime(2025, 1, 1)  # no tzinfo
    assert is_control_active(naive_past, ASSESSMENT) is True
    naive_future = datetime(2030, 1, 1)
    assert is_control_active(naive_future, ASSESSMENT) is False


def test_regulation_status_mapping():
    past = datetime(2023, 8, 11, tzinfo=timezone.utc)
    future = datetime(2027, 5, 13, tzinfo=timezone.utc)
    assert regulation_status(past, ASSESSMENT) == RegulationStatus.IN_FORCE.value
    assert regulation_status(future, ASSESSMENT) == RegulationStatus.UPCOMING.value
    assert regulation_status(None, ASSESSMENT) == RegulationStatus.IN_FORCE.value
