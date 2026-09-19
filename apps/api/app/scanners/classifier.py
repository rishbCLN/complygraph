"""Deterministic hybrid PII classifier.

Baseline classification never uses an LLM. It combines three signals:
  - name_signal:    column/field-name keyword rules
  - pattern_signal: regex over masked sample values
  - type_signal:    data-type hints

    confidence = 0.45*name + 0.45*pattern + 0.10*type

Bands: >=0.85 HIGH, 0.65-0.849 MEDIUM, <0.65 LOW.
Fields below HIGH that could matter are flagged needs_review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.enums import Classification, ConfidenceBand, DataCategory

# --- Column-name keyword rules --------------------------------------------------
# Maps a category to the substrings that suggest it (checked against normalized name).
_NAME_RULES: dict[str, list[str]] = {
    DataCategory.CONTACT.value: [
        "email", "e_mail", "mail", "phone", "mobile", "telephone", "contact",
        "fax", "whatsapp",
    ],
    DataCategory.IDENTITY.value: [
        "first_name", "last_name", "full_name", "fname", "lname", "name",
        "dob", "date_of_birth", "birth", "gender", "aadhaar", "aadhar", "pan",
        "passport", "national_id", "ssn", "uid", "customer_name",
    ],
    DataCategory.LOCATION.value: [
        "address", "street", "city", "state", "pincode", "postal", "zip",
        "country", "location", "latitude", "longitude", "geo",
    ],
    DataCategory.FINANCIAL.value: [
        "bank", "account_number", "acct", "iban", "ifsc", "card", "credit_card",
        "debit_card", "cvv", "salary", "income", "payment", "upi", "vpa",
    ],
    DataCategory.HEALTH.value: [
        "health", "medical", "diagnosis", "blood_group", "disability",
        "prescription", "insurance",
    ],
    DataCategory.AUTHENTICATION.value: [
        "password", "passwd", "pwd", "secret", "token", "api_key", "otp",
        "pin", "security_answer", "mfa",
    ],
    DataCategory.DEVICE.value: [
        "ip_address", "ip", "device_id", "device", "mac_address", "imei",
        "user_agent", "cookie", "session_id", "fingerprint",
    ],
    DataCategory.BEHAVIORAL.value: [
        "preference", "opt_in", "opt_out", "marketing", "consent", "clickstream",
        "browsing", "activity",
    ],
    DataCategory.PROFESSIONAL.value: [
        "department", "designation", "employee", "employer", "job_title",
        "occupation", "company",
    ],
}

# Categories considered sensitive/high-risk personal data.
_SENSITIVE_CATEGORIES = {
    DataCategory.FINANCIAL.value,
    DataCategory.HEALTH.value,
    DataCategory.AUTHENTICATION.value,
}

# Operational metadata name hints (not personal data).
_METADATA_HINTS = [
    "created_at", "updated_at", "deleted_at", "timestamp", "version",
    "status", "is_active", "count", "total", "order_total", "quantity",
    "price", "amount", "sku", "index", "sequence",
]

# --- Regex pattern rules --------------------------------------------------------
_PATTERNS: dict[str, re.Pattern[str]] = {
    DataCategory.CONTACT.value: re.compile(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$"  # email
    ),
    "phone": re.compile(r"^(\+?91[\-\s]?)?[6-9]\d{9}$"),  # Indian phone-like
    "ip": re.compile(r"^(\d{1,3}\.){3}\d{1,3}$"),
    "dob": re.compile(r"^\d{4}-\d{2}-\d{2}$|^\d{2}[/-]\d{2}[/-]\d{4}$"),
    "card": re.compile(r"^\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}$"),
}

_TYPE_PERSONAL_HINTS = {"varchar", "text", "char", "string", "citext"}


@dataclass
class FieldSample:
    """Input to the classifier. Values are RAW only in-memory during scan and are
    never persisted; only masked examples derived from them are stored."""

    name: str
    data_type: str | None = None
    field_path: str | None = None
    values: list[str] = field(default_factory=list)


@dataclass
class ClassificationResult:
    classification: str
    category: str
    confidence: float
    confidence_band: str
    detection_method: str
    needs_review: bool
    name_signal: float
    pattern_signal: float
    type_signal: float
    sample_count: int
    sensitive_count: int
    masked_examples: list[str]


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _name_signal(name: str, path: str | None) -> tuple[float, str | None]:
    norm = _normalize(name)
    full = _normalize(f"{path}_{name}") if path else norm
    best_cat: str | None = None
    best_score = 0.0
    for category, keywords in _NAME_RULES.items():
        for kw in keywords:
            if norm == kw:
                score = 1.0
            elif norm.startswith(kw) or norm.endswith(kw) or kw in norm:
                score = 0.85
            elif kw in full:
                score = 0.7
            else:
                continue
            if score > best_score:
                best_score = score
                best_cat = category
    return best_score, best_cat


def _is_metadata_name(name: str) -> bool:
    norm = _normalize(name)
    return any(norm == h or norm.endswith(h) for h in _METADATA_HINTS)


def _pattern_signal(values: list[str]) -> tuple[float, str | None, int]:
    if not values:
        return 0.0, None, 0
    matches: dict[str, int] = {}
    sensitive_hits = 0
    checked = 0
    for raw in values:
        v = (raw or "").strip()
        if not v:
            continue
        checked += 1
        for label, pattern in _PATTERNS.items():
            if pattern.match(v):
                matches[label] = matches.get(label, 0) + 1
                if label in {"card"}:
                    sensitive_hits += 1
    if checked == 0:
        return 0.0, None, 0
    best_label = max(matches, key=lambda k: matches[k]) if matches else None
    if not best_label:
        return 0.0, None, sensitive_hits
    ratio = matches[best_label] / checked
    label_to_category = {
        DataCategory.CONTACT.value: DataCategory.CONTACT.value,
        "phone": DataCategory.CONTACT.value,
        "ip": DataCategory.DEVICE.value,
        "dob": DataCategory.IDENTITY.value,
        "card": DataCategory.FINANCIAL.value,
    }
    category = label_to_category.get(best_label)
    if best_label == "card":
        sensitive_hits = matches[best_label]
    return round(ratio, 3), category, sensitive_hits


def _type_signal(data_type: str | None) -> float:
    if not data_type:
        return 0.0
    dt = data_type.lower()
    return 1.0 if any(h in dt for h in _TYPE_PERSONAL_HINTS) else 0.2


def mask_value(value: str, category: str | None) -> str:
    """Produce a masked example. Raw PII is never stored or displayed in full."""
    v = (value or "").strip()
    if not v:
        return ""
    if category == DataCategory.CONTACT.value and "@" in v:
        local, _, domain = v.partition("@")
        head = local[0] if local else "*"
        return f"{head}***@{domain}"
    if len(v) <= 4:
        return "*" * len(v)
    return v[0] + "*" * (len(v) - 3) + v[-2:]


def classify_field(sample: FieldSample) -> ClassificationResult:
    name_score, name_cat = _name_signal(sample.name, sample.field_path)
    pattern_score, pattern_cat, sensitive_count = _pattern_signal(sample.values)
    type_score = _type_signal(sample.data_type)

    confidence = round(0.45 * name_score + 0.45 * pattern_score + 0.10 * type_score, 3)

    # Prefer pattern-detected category (evidence-backed), else name-based.
    category = pattern_cat or name_cat or DataCategory.UNKNOWN.value

    # Operational metadata override: strong metadata name + weak personal signals.
    if _is_metadata_name(sample.name) and pattern_score < 0.5 and name_score < 0.7:
        classification = Classification.OPERATIONAL_METADATA.value
        category = DataCategory.NON_PERSONAL.value
        confidence = max(confidence, round(0.10 * type_score + 0.8, 3)) if False else max(confidence, 0.6)
    elif confidence >= 0.65 or (name_cat and name_score >= 0.85):
        if category in _SENSITIVE_CATEGORIES:
            classification = Classification.SENSITIVE_PERSONAL_DATA.value
        elif category == DataCategory.NON_PERSONAL.value:
            classification = Classification.NON_PERSONAL.value
        else:
            classification = Classification.PERSONAL_DATA.value
    else:
        classification = Classification.UNKNOWN.value

    band = (
        ConfidenceBand.HIGH.value
        if confidence >= 0.85
        else ConfidenceBand.MEDIUM.value
        if confidence >= 0.65
        else ConfidenceBand.LOW.value
    )

    could_matter = classification in {
        Classification.PERSONAL_DATA.value,
        Classification.SENSITIVE_PERSONAL_DATA.value,
        Classification.UNKNOWN.value,
    }
    needs_review = band != ConfidenceBand.HIGH.value and could_matter

    method_parts = []
    if name_score > 0:
        method_parts.append("name")
    if pattern_score > 0:
        method_parts.append("pattern")
    if type_score >= 1.0:
        method_parts.append("type")
    detection_method = "+".join(method_parts) or "none"

    masked = [mask_value(v, category) for v in sample.values[:3] if (v or "").strip()]

    return ClassificationResult(
        classification=classification,
        category=category,
        confidence=confidence,
        confidence_band=band,
        detection_method=detection_method,
        needs_review=needs_review,
        name_signal=round(name_score, 3),
        pattern_signal=round(pattern_score, 3),
        type_signal=round(type_score, 3),
        sample_count=len([v for v in sample.values if (v or "").strip()]),
        sensitive_count=sensitive_count,
        masked_examples=masked,
    )
