"""Unit tests for the internal risk scoring model.

    weighted = 0.35*sensitivity + 0.25*exposure + 0.25*control_gap + 0.15*volume
    risk_score = round(weighted / 5 * 100)

Severity bands: >=80 CRITICAL, >=60 HIGH, >=35 MEDIUM, else LOW.
"""

from __future__ import annotations

import pytest

from app.controls.risk import RiskInputs, compute_risk, severity_for_score, volume_band
from app.core.enums import Severity


def test_max_inputs_score_100_critical():
    result = compute_risk(RiskInputs(sensitivity=5, exposure=5, control_gap=5, volume=5))
    assert result.score == 100
    assert result.severity == Severity.CRITICAL.value


def test_min_inputs_low_severity():
    result = compute_risk(RiskInputs(sensitivity=1, exposure=1, control_gap=0, volume=1))
    # weighted = 0.35 + 0.25 + 0 + 0.15 = 0.75 -> round(15) = 15
    assert result.score == 15
    assert result.severity == Severity.LOW.value


def test_mid_inputs_high_severity():
    result = compute_risk(RiskInputs(sensitivity=3, exposure=3, control_gap=3, volume=3))
    # weighted = 3.0 -> round(60) = 60 -> HIGH
    assert result.score == 60
    assert result.severity == Severity.HIGH.value


def test_medium_severity():
    result = compute_risk(RiskInputs(sensitivity=2, exposure=2, control_gap=2, volume=2))
    # weighted = 2.0 -> 40 -> MEDIUM
    assert result.score == 40
    assert result.severity == Severity.MEDIUM.value


@pytest.mark.parametrize(
    "score,expected",
    [
        (100, Severity.CRITICAL.value),
        (80, Severity.CRITICAL.value),
        (79, Severity.HIGH.value),
        (60, Severity.HIGH.value),
        (59, Severity.MEDIUM.value),
        (35, Severity.MEDIUM.value),
        (34, Severity.LOW.value),
        (0, Severity.LOW.value),
    ],
)
def test_severity_band_boundaries(score, expected):
    assert severity_for_score(score) == expected


def test_inputs_are_clamped_into_range():
    clamped = RiskInputs(sensitivity=99, exposure=-5, control_gap=-3, volume=0).clamp()
    assert clamped.sensitivity == 5
    assert clamped.exposure == 1
    assert clamped.control_gap == 0
    assert clamped.volume == 1


def test_compute_risk_reports_breakdown():
    result = compute_risk(RiskInputs(sensitivity=4, exposure=3, control_gap=2, volume=5))
    assert set(result.breakdown) == {"sensitivity", "exposure", "control_gap", "volume"}
    assert result.breakdown["sensitivity"] == 4


@pytest.mark.parametrize(
    "row_count,expected",
    [
        (None, 1),
        (0, 1),
        (-10, 1),
        (500, 2),
        (999, 2),
        (50_000, 3),
        (500_000, 4),
        (2_000_000, 5),
    ],
)
def test_volume_band(row_count, expected):
    assert volume_band(row_count) == expected
