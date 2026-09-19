"""Data sensitivity model.

Internal risk model (1-5). This is NOT a legal classification.
  1 = non-personal
  2 = ordinary personal
  3 = sensitive operational
  4 = high-risk personal
  5 = critical
"""

from __future__ import annotations

from app.core.enums import Classification, DataCategory

_CATEGORY_SENSITIVITY = {
    DataCategory.AUTHENTICATION.value: 5,
    DataCategory.FINANCIAL.value: 5,
    DataCategory.HEALTH.value: 5,
    DataCategory.IDENTITY.value: 4,
    DataCategory.LOCATION.value: 4,
    DataCategory.CONTACT.value: 3,
    DataCategory.DEVICE.value: 3,
    DataCategory.BEHAVIORAL.value: 3,
    DataCategory.PROFESSIONAL.value: 2,
    DataCategory.OTHER_PERSONAL.value: 2,
    DataCategory.NON_PERSONAL.value: 1,
    DataCategory.UNKNOWN.value: 1,
}


def field_sensitivity(classification: str, category: str) -> int:
    if classification == Classification.NON_PERSONAL.value:
        return 1
    if classification == Classification.OPERATIONAL_METADATA.value:
        return max(1, _CATEGORY_SENSITIVITY.get(category, 1))
    return _CATEGORY_SENSITIVITY.get(category, 2)


def asset_sensitivity(field_levels: list[int]) -> int:
    """An asset's sensitivity is the maximum of its fields (worst-case)."""
    return max(field_levels) if field_levels else 1
