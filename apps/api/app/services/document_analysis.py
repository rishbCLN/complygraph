"""Policy-document content analysis.

Closes the loop between "a policy document was uploaded" and "the document
actually contains the clauses DPDP requires". Extracts text from an uploaded
document (txt/markdown/PDF) and checks for the presence of key DPDP notice and
governance clauses. This is a keyword/heuristic check that surfaces coverage and
gaps for human review; it is not a legal determination of adequacy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- Text extraction ------------------------------------------------------------

_MAX_TEXT_CHARS = 2_000_000


def extract_text(content: bytes, filename: str) -> str:
    """Extract plain text from a supported document.

    txt/md are decoded directly. PDF uses pypdf when available and otherwise
    raises a clear error the caller can surface.
    """
    name = (filename or "").lower()
    if name.endswith((".txt", ".md", ".markdown", ".rst")):
        return content.decode("utf-8", errors="replace")[:_MAX_TEXT_CHARS]
    if name.endswith(".pdf"):
        return _extract_pdf_text(content)[:_MAX_TEXT_CHARS]
    # Fallback: best-effort decode (covers unknown text-like documents).
    return content.decode("utf-8", errors="replace")[:_MAX_TEXT_CHARS]


def _extract_pdf_text(content: bytes) -> str:
    try:
        import io  # noqa: PLC0415

        from pypdf import PdfReader  # noqa: PLC0415
    except ImportError as exc:
        raise DocumentExtractionError(
            "PDF text extraction requires the optional 'pypdf' dependency."
        ) from exc
    reader = PdfReader(io.BytesIO(content))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


class DocumentExtractionError(Exception):
    """Raised when a document's text cannot be extracted."""


# --- DPDP clause checks ---------------------------------------------------------


@dataclass
class ClauseCheck:
    key: str
    title: str
    required: bool
    patterns: list[re.Pattern[str]]


def _p(*words: str) -> list[re.Pattern[str]]:
    return [re.compile(w, re.IGNORECASE) for w in words]


# Clauses expected in a DPDP privacy notice / policy. Keyword-based presence check.
_CLAUSES: list[ClauseCheck] = [
    ClauseCheck("purpose", "Purpose of processing", True,
                _p(r"\bpurpose(s)?\b", r"\bwhy we (collect|process|use)\b")),
    ClauseCheck("categories", "Categories of personal data", True,
                _p(r"\bpersonal data\b", r"\bcategories of (personal )?data\b",
                   r"\binformation we collect\b")),
    ClauseCheck("consent", "Consent / lawful basis", True,
                _p(r"\bconsent\b", r"\blawful basis\b", r"\blegitimate use(s)?\b")),
    ClauseCheck("withdrawal", "Right to withdraw consent", True,
                _p(r"\bwithdraw(al)? (your )?consent\b", r"\bwithdraw consent\b")),
    ClauseCheck("rights", "Data principal rights", True,
                _p(r"\bright to (access|correction|erasure|deletion)\b",
                   r"\byour rights\b", r"\bdata principal rights\b",
                   r"\bnominat(e|ion)\b")),
    ClauseCheck("grievance", "Grievance officer / redressal", True,
                _p(r"\bgrievance\b", r"\bgrievance officer\b",
                   r"\bdata protection officer\b", r"\bredress(al)?\b")),
    ClauseCheck("contact", "Contact information", True,
                _p(r"\bcontact\b", r"\bemail us\b", r"\breach us\b",
                   r"@[a-z0-9.-]+\.[a-z]{2,}")),
    ClauseCheck("retention", "Retention / erasure period", True,
                _p(r"\bretention\b", r"\bretain\b", r"\bhow long\b",
                   r"\berasure\b", r"\bdelet(e|ion)\b")),
    ClauseCheck("cross_border", "Cross-border transfer", False,
                _p(r"\btransfer(red)? (outside|abroad|to another country)\b",
                   r"\bcross[- ]border\b", r"\boutside india\b")),
    ClauseCheck("children", "Children's data / parental consent", False,
                _p(r"\bchild(ren)?\b", r"\bparental consent\b",
                   r"\bage of eighteen\b", r"\bminor(s)?\b")),
    ClauseCheck("security", "Security safeguards", True,
                _p(r"\bsecurity\b", r"\bsafeguard(s)?\b", r"\bencrypt(ion|ed)?\b",
                   r"\breasonable security practices\b")),
    ClauseCheck("breach", "Breach notification", False,
                _p(r"\bbreach\b", r"\bdata breach\b", r"\bnotif(y|ication)\b")),
]


@dataclass
class PolicyAnalysis:
    found: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    present_optional: list[str] = field(default_factory=list)
    coverage: float = 0.0  # fraction of REQUIRED clauses present (0-1)
    clause_detail: dict[str, bool] = field(default_factory=dict)

    @property
    def is_adequate(self) -> bool:
        return not self.missing_required


def analyze_policy(text: str) -> PolicyAnalysis:
    """Check a policy document's text for the presence of DPDP clauses."""
    result = PolicyAnalysis()
    required_total = 0
    required_found = 0
    for clause in _CLAUSES:
        present = any(p.search(text) for p in clause.patterns)
        result.clause_detail[clause.key] = present
        if present:
            result.found.append(clause.key)
        if clause.required:
            required_total += 1
            if present:
                required_found += 1
            else:
                result.missing_required.append(clause.key)
        elif present:
            result.present_optional.append(clause.key)
    result.coverage = round(required_found / required_total, 3) if required_total else 0.0
    return result


def clause_titles() -> dict[str, str]:
    return {c.key: c.title for c in _CLAUSES}
