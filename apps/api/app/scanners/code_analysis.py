"""Static code risk analysis: PII-in-logs detection and lightweight taint.

This is a heuristic, single-file static analyzer (no execution, no full AST). It
answers two DPDP-relevant questions from source text:

  1. Is personal data written to logs?  e.g. logger.info(user.email)
  2. Does a personal-data field plausibly reach a third-party SDK call?
     e.g.  email = user.email ;  stripe.Customer.create(email=email)

Both are deliberately conservative: matches are reported as CodeRiskFinding with
a confidence and a redacted line, so they inform (not decide) compliance
findings. False positives are possible; that is why confidence < 1.0 and the
control layer treats these as review signals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# PII-ish attribute/variable name hints (aligned with the classifier categories).
_PII_HINTS = (
    "email", "e_mail", "mail", "phone", "mobile", "telephone", "contact",
    "first_name", "last_name", "full_name", "fullname", "dob",
    "date_of_birth", "birth", "gender", "aadhaar", "aadhar", "pan", "passport",
    "national_id", "ssn", "address", "street", "city", "pincode", "postal",
    "latitude", "longitude", "bank", "account_number", "iban",
    "ifsc", "card", "credit_card", "debit_card", "cvv", "salary", "income",
    "upi", "vpa", "health", "medical", "diagnosis", "blood_group", "password",
    "passwd", "pwd", "secret", "otp", "ip_address", "device_id",
    "imei", "customer", "user",
)
_PII_RE = re.compile(
    r"\b(" + "|".join(sorted(set(_PII_HINTS), key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# Logging call patterns across Python / JS-TS / Go / Java.
_LOG_CALL = re.compile(
    r"""(?ix)
    \b(
        log(?:ger|ging)? \s*\. \s*(?:debug|info|warn|warning|error|exception|critical|log|trace) |
        console \s*\. \s*(?:log|info|warn|error|debug) |
        print |
        fmt \s*\. \s*(?:Print|Printf|Println) |
        System \s*\. \s*out \s*\. \s*print(?:ln)?
    )
    \s*\(
    """
)

# Known third-party SDK roots used as taint sinks.
_SDK_SINK_TOKENS = (
    "stripe", "razorpay", "paypal", "braintree", "mixpanel", "amplitude",
    "posthog", "segment", "analytics", "sendgrid", "twilio", "mailgun",
    "mailchimp", "postmark", "boto3", "cloudinary", "auth0", "firebase",
    "okta", "sentry", "datadog", "newrelic", "hubspot", "intercom", "zendesk",
    "salesforce", "openai", "anthropic", "cohere",
)
_SINK_CALL = re.compile(
    r"\b(" + "|".join(_SDK_SINK_TOKENS) + r")\b[\w.]*\s*\(", re.IGNORECASE
)

_ASSIGN = re.compile(r"^\s*(?:const\s+|let\s+|var\s+)?([a-zA-Z_]\w*)\s*(?::[^=]+)?=\s*(.+)$")


@dataclass
class CodeRiskFinding:
    kind: str  # "pii_in_logs" | "pii_to_third_party"
    line_no: int
    snippet: str
    detail: str
    confidence: float


def _looks_like_pii(expr: str) -> bool:
    return bool(_PII_RE.search(expr))


def _redact(line: str, max_len: int = 160) -> str:
    """Trim and redact string literals so we never emit hardcoded PII/secrets."""
    no_strings = re.sub(r"""(['"]).*?\1""", r"\1[...]\1", line).strip()
    return no_strings[:max_len]


def _split_args(fragment: str) -> set[str]:
    """Rough tokenization of identifiers inside a call fragment."""
    return set(re.findall(r"[a-zA-Z_]\w*", fragment))


def analyze_source(text: str, *, max_lines: int = 20_000) -> list[CodeRiskFinding]:
    """Analyze one source file's text for PII logging and PII->SDK taint."""
    findings: list[CodeRiskFinding] = []
    lines = text.splitlines()[:max_lines]

    # Track variables assigned from a PII-looking expression (single-file taint).
    tainted: set[str] = set()

    for idx, raw in enumerate(lines, start=1):
        line = raw.rstrip()
        if not line or len(line) > 2000:
            continue

        m = _ASSIGN.match(line)
        if m:
            var, rhs = m.group(1), m.group(2)
            if _looks_like_pii(rhs):
                tainted.add(var)

        log_m = _LOG_CALL.search(line)
        if log_m:
            after = line[log_m.end() - 1 :]
            if _looks_like_pii(after) or (tainted & _split_args(after)):
                findings.append(
                    CodeRiskFinding(
                        kind="pii_in_logs",
                        line_no=idx,
                        snippet=_redact(line),
                        detail="Personal-data reference passed to a logging call.",
                        confidence=0.6,
                    )
                )

        sink_m = _SINK_CALL.search(line)
        if sink_m:
            after = line[sink_m.end() - 1 :]
            args = _split_args(after)
            if _looks_like_pii(after) or (tainted & args):
                vendor_token = sink_m.group(1).lower()
                findings.append(
                    CodeRiskFinding(
                        kind="pii_to_third_party",
                        line_no=idx,
                        snippet=_redact(line),
                        detail=(
                            f"Personal-data reference plausibly passed to third-party "
                            f"SDK '{vendor_token}'."
                        ),
                        confidence=0.55,
                    )
                )

    return findings
