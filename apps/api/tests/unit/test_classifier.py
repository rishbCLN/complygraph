"""Unit tests for the deterministic PII classifier.

Verifies the confidence formula (0.45*name + 0.45*pattern + 0.10*type), the
HIGH/MEDIUM/LOW bands, sensitive-category classification, operational-metadata
override, masking, and needs_review flagging.
"""

from __future__ import annotations

import pytest

from app.core.enums import Classification, ConfidenceBand, DataCategory
from app.scanners.classifier import (
    FieldSample,
    classify_field,
    mask_value,
)


def test_email_field_is_high_confidence_contact_personal_data():
    result = classify_field(
        FieldSample(
            name="email",
            values=["aarav@example.com", "diya@example.com", "kabir@example.com"],
        )
    )
    # name_signal 1.0, pattern_signal 1.0, type_signal 0 -> 0.45 + 0.45 = 0.9
    assert result.confidence == pytest.approx(0.9)
    assert result.confidence_band == ConfidenceBand.HIGH.value
    assert result.category == DataCategory.CONTACT.value
    assert result.classification == Classification.PERSONAL_DATA.value
    assert result.needs_review is False
    assert "name" in result.detection_method and "pattern" in result.detection_method


def test_credit_card_field_is_sensitive_personal_data():
    result = classify_field(
        FieldSample(
            name="credit_card",
            values=["4111 1111 1111 1111", "4222 2222 2222 2222"],
        )
    )
    assert result.category == DataCategory.FINANCIAL.value
    assert result.classification == Classification.SENSITIVE_PERSONAL_DATA.value
    assert result.confidence_band == ConfidenceBand.HIGH.value
    assert result.sensitive_count == 2


def test_confidence_formula_weights_type_signal():
    # A name-only identity match with a text type: no pattern hits.
    result = classify_field(
        FieldSample(name="full_name", data_type="varchar", values=["masked"])
    )
    # name_signal 1.0 (exact "full_name"), pattern 0, type 1.0
    # 0.45*1 + 0.45*0 + 0.10*1 = 0.55
    assert result.confidence == pytest.approx(0.55)
    assert result.confidence_band == ConfidenceBand.LOW.value
    # Strong name category still classifies as personal data despite LOW band.
    assert result.classification == Classification.PERSONAL_DATA.value
    assert result.category == DataCategory.IDENTITY.value
    # Below HIGH and could-matter -> flagged for review.
    assert result.needs_review is True


def test_bands_thresholds_high_medium_low():
    # HIGH boundary is >= 0.85, MEDIUM 0.65-0.849, LOW < 0.65.
    high = classify_field(FieldSample(name="email", values=["a@b.com"]))
    assert high.confidence >= 0.85
    assert high.confidence_band == ConfidenceBand.HIGH.value

    low = classify_field(FieldSample(name="notes", values=["free text here"]))
    assert low.confidence < 0.65
    assert low.confidence_band == ConfidenceBand.LOW.value


def test_operational_metadata_override():
    result = classify_field(
        FieldSample(name="order_total", data_type="numeric", values=["100", "250"])
    )
    assert result.classification == Classification.OPERATIONAL_METADATA.value
    assert result.category == DataCategory.NON_PERSONAL.value
    assert result.needs_review is False


def test_unknown_field_needs_review():
    result = classify_field(FieldSample(name="misc_column", values=[]))
    assert result.classification == Classification.UNKNOWN.value
    assert result.confidence_band == ConfidenceBand.LOW.value
    assert result.needs_review is True


def test_masked_examples_never_expose_raw_values():
    result = classify_field(
        FieldSample(name="email", values=["aarav@example.com"])
    )
    assert result.masked_examples
    for m in result.masked_examples:
        assert "aarav@example.com" not in m
        assert m.startswith("a***@") or "*" in m


def test_mask_value_email_and_generic():
    assert mask_value("aarav@example.com", DataCategory.CONTACT.value) == "a***@example.com"
    # generic masking keeps head + last two chars only
    masked = mask_value("SENSITIVE", DataCategory.IDENTITY.value)
    assert masked.startswith("S")
    assert masked.endswith("VE")
    assert "*" in masked
    # short values fully masked
    assert mask_value("ab", None) == "**"
