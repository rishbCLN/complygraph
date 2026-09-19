"""Unit tests for policy-document clause analysis."""

from __future__ import annotations

from app.services.document_analysis import (
    DocumentExtractionError,
    analyze_policy,
    extract_text,
)

_GOOD_POLICY = """
Privacy Notice

Purpose: We collect and process your personal data to provide our services.
Categories of personal data we collect include name, email, and phone.
We rely on your consent as the lawful basis for processing.
You may withdraw your consent at any time.
Your rights: you have the right to access, correction, and erasure of your data,
and the right to nominate another individual.
Grievance Officer: Our grievance officer handles redressal of complaints.
Contact: reach us at privacy@example.com.
Retention: we retain data only as long as necessary and then delete it.
Security: we apply reasonable security practices including encryption.
"""

_THIN_POLICY = """
We are a company. We like data. Trust us. We do stuff with information.
"""


def test_full_policy_is_adequate():
    analysis = analyze_policy(_GOOD_POLICY)
    assert analysis.is_adequate
    assert analysis.coverage == 1.0
    assert analysis.missing_required == []


def test_thin_policy_flags_missing_required_clauses():
    analysis = analyze_policy(_THIN_POLICY)
    assert not analysis.is_adequate
    assert analysis.coverage < 1.0
    # Should be missing consent, grievance, retention, rights, etc.
    assert "grievance" in analysis.missing_required
    assert "consent" in analysis.missing_required


def test_optional_clauses_reported_separately():
    text = _GOOD_POLICY + "\nWe may transfer data outside India. We do not process children's data beyond age of eighteen."
    analysis = analyze_policy(text)
    assert "cross_border" in analysis.present_optional
    assert "children" in analysis.present_optional
    assert analysis.is_adequate


def test_extract_text_from_txt():
    text = extract_text(b"Purpose and consent are described here.", "notice.txt")
    assert "consent" in text


def test_extract_text_pdf_without_pypdf_is_graceful():
    # If pypdf is unavailable, a clear DocumentExtractionError is raised (not a crash).
    try:
        import pypdf  # noqa: F401
    except ImportError:
        try:
            extract_text(b"%PDF-1.4 fake", "policy.pdf")
        except DocumentExtractionError:
            return
        raise AssertionError("Expected DocumentExtractionError without pypdf")
    # If pypdf IS installed, extraction should not raise for our purposes here.


def test_analyze_document_endpoint(admin_client):
    files = {"file": ("privacy.txt", _GOOD_POLICY.encode("utf-8"), "text/plain")}
    resp = admin_client.post("/api/v1/documents/analyze", files=files)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["is_adequate"] is True
    assert body["coverage"] == 1.0
    assert body["evidence_id"]


def test_analyze_thin_document_endpoint_reports_gaps(admin_client):
    files = {"file": ("weak.txt", _THIN_POLICY.encode("utf-8"), "text/plain")}
    resp = admin_client.post("/api/v1/documents/analyze", files=files)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["is_adequate"] is False
    assert "grievance" in body["missing_required"]
