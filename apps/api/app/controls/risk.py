"""Internal risk scoring.

Product risk score 0-100. This is an internal risk model, NOT a statutory score.

Inputs (each 1-5 except control_gap which is 0-5):
    sensitivity, exposure, control_gap, volume

    weighted = 0.35*sensitivity + 0.25*exposure + 0.25*control_gap + 0.15*volume
    risk_score = round(weighted / 5 * 100)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.core.enums import Severity


@dataclass
class RiskInputs:
    sensitivity: int  # 1-5
    exposure: int  # 1-5
    control_gap: int  # 0-5
    volume: int  # 1-5

    def clamp(self) -> "RiskInputs":
        return RiskInputs(
            sensitivity=_clamp(self.sensitivity, 1, 5),
            exposure=_clamp(self.exposure, 1, 5),
            control_gap=_clamp(self.control_gap, 0, 5),
            volume=_clamp(self.volume, 1, 5),
        )


@dataclass
class RiskResult:
    score: int
    severity: str
    breakdown: dict


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def compute_risk(inputs: RiskInputs) -> RiskResult:
    ci = inputs.clamp()
    weighted = 0.35 * ci.sensitivity + 0.25 * ci.exposure + 0.25 * ci.control_gap + 0.15 * ci.volume
    score = round(weighted / 5 * 100)
    return RiskResult(score=score, severity=severity_for_score(score), breakdown=asdict(ci))


def severity_for_score(score: int) -> str:
    if score >= 80:
        return Severity.CRITICAL.value
    if score >= 60:
        return Severity.HIGH.value
    if score >= 35:
        return Severity.MEDIUM.value
    return Severity.LOW.value


def volume_band(row_count: int | None) -> int:
    """Map a raw row count to a 1-5 volume band."""
    if not row_count or row_count <= 0:
        return 1
    if row_count < 1_000:
        return 2
    if row_count < 100_000:
        return 3
    if row_count < 1_000_000:
        return 4
    return 5
