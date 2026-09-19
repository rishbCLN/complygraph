"""Codebase scanner connector.

Reads an application's source code (uploaded as a .zip of the repository) and
statically extracts *data-model definitions* — the places where personal data
is declared and persisted — so the same discovery -> classification -> control
-> findings -> graph pipeline that runs on databases can run on code.

This is a static, read-only, dependency-free scanner. It never executes the
scanned code. Extraction is regex/heuristic based (no per-language toolchains),
which keeps it safe and portable. Each detected data model (SQL table,
SQLAlchemy/Django model, Prisma model, TypeScript interface/type) becomes a
DiscoveredAsset; each of its columns/fields becomes a DiscoveredField that the
existing PII classifier evaluates by name and type.

Source code has no runtime rows, so no sample values are produced: the
classifier's pattern_signal is 0 and classification relies on the name and type
signals — which is exactly the design the classifier already supports.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from dataclasses import dataclass

from app.core.enums import AssetType, FlowType
from app.scanners.base import (
    BaseConnector,
    DiscoveredAsset,
    DiscoveredCodeRisk,
    DiscoveredField,
    DiscoveredIntegration,
)
from app.scanners.code_analysis import analyze_source

# Cap total code-risk findings emitted per scan to keep output bounded.
_MAX_CODE_RISKS = 500

# --- Safety bounds (guard against huge repos and zip bombs) ---------------------
_MAX_FILES = 5_000
_MAX_FILE_BYTES = 1_000_000  # skip individual source files larger than 1 MB
_MAX_TOTAL_UNCOMPRESSED = 200 * 1024 * 1024  # 200 MB total uncompressed cap
_MAX_MODELS = 3_000

# Directories that never contain first-party data models.
_SKIP_DIR_PARTS = {
    ".git", "node_modules", "dist", "build", ".next", "out", "coverage",
    "venv", ".venv", "env", "__pycache__", ".mypy_cache", ".pytest_cache",
    "vendor", "target", ".idea", ".vscode", "site-packages", ".terraform",
}

# Extension -> model-extractor key.
_EXT_LANG = {
    ".sql": "sql",
    ".py": "python",
    ".prisma": "prisma",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
}

# Extensions we scan for third-party imports (superset of model languages).
_IMPORT_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}

# --- Third-party integration (vendor) registry ---------------------------------
_ANALYTICS = FlowType.ANALYTICS.value
_THIRD = FlowType.THIRD_PARTY.value
_PROC = FlowType.PROCESSOR.value

# package token -> (vendor_name, service_type, flow_type, country)
_INTEGRATIONS: dict[str, tuple[str, str, str, str | None]] = {
    # Payments
    "stripe": ("Stripe", "Payments", _PROC, "United States"),
    "razorpay": ("Razorpay", "Payments", _PROC, "India"),
    "paypal": ("PayPal", "Payments", _PROC, "United States"),
    "paypalrestsdk": ("PayPal", "Payments", _PROC, "United States"),
    "braintree": ("Braintree", "Payments", _PROC, "United States"),
    # Analytics / CDP
    "mixpanel": ("Mixpanel", "Product analytics", _ANALYTICS, "United States"),
    "amplitude": ("Amplitude", "Product analytics", _ANALYTICS, "United States"),
    "posthog": ("PostHog", "Product analytics", _ANALYTICS, "United States"),
    "heap": ("Heap", "Product analytics", _ANALYTICS, "United States"),
    "analytics-node": ("Segment", "Customer data platform", _ANALYTICS, "United States"),
    "segment": ("Segment", "Customer data platform", _ANALYTICS, "United States"),
    # Email / SMS
    "sendgrid": ("SendGrid", "Email delivery", _PROC, "United States"),
    "twilio": ("Twilio", "SMS / communications", _PROC, "United States"),
    "mailgun": ("Mailgun", "Email delivery", _PROC, "United States"),
    "mailchimp": ("Mailchimp", "Email marketing", _THIRD, "United States"),
    "postmark": ("Postmark", "Email delivery", _PROC, "United States"),
    # Cloud storage / infrastructure
    "boto3": ("Amazon Web Services", "Cloud storage / infrastructure", _PROC, "United States"),
    "botocore": ("Amazon Web Services", "Cloud storage / infrastructure", _PROC, "United States"),
    "cloudinary": ("Cloudinary", "Media storage", _PROC, "United States"),
    # Auth / identity / backend
    "auth0": ("Auth0", "Identity / authentication", _PROC, "United States"),
    "firebase": ("Google Firebase", "Backend / auth / analytics", _PROC, "United States"),
    "firebase-admin": ("Google Firebase", "Backend / auth / analytics", _PROC, "United States"),
    "okta": ("Okta", "Identity / authentication", _PROC, "United States"),
    # Monitoring / logging
    "sentry": ("Sentry", "Error monitoring", _THIRD, "United States"),
    "sentry_sdk": ("Sentry", "Error monitoring", _THIRD, "United States"),
    "datadog": ("Datadog", "Monitoring / logging", _THIRD, "United States"),
    "ddtrace": ("Datadog", "Monitoring / logging", _THIRD, "United States"),
    "newrelic": ("New Relic", "Monitoring / logging", _THIRD, "United States"),
    # CRM / support / marketing
    "hubspot": ("HubSpot", "CRM / marketing", _THIRD, "United States"),
    "intercom": ("Intercom", "Customer messaging", _THIRD, "United States"),
    "zendesk": ("Zendesk", "Customer support", _THIRD, "United States"),
    "salesforce": ("Salesforce", "CRM", _THIRD, "United States"),
    "simple_salesforce": ("Salesforce", "CRM", _THIRD, "United States"),
    # AI / LLM
    "openai": ("OpenAI", "AI / LLM", _THIRD, "United States"),
    "anthropic": ("Anthropic", "AI / LLM", _THIRD, "United States"),
    "cohere": ("Cohere", "AI / LLM", _THIRD, "United States"),
}

# npm scope -> vendor entry (for @scope/pkg imports and deps)
_NPM_SCOPE: dict[str, tuple[str, str, str, str | None] | None] = {
    "@aws-sdk": ("Amazon Web Services", "Cloud storage / infrastructure", _PROC, "United States"),
    "@google-cloud": ("Google Cloud", "Cloud storage / infrastructure", _PROC, "United States"),
    "@azure": ("Microsoft Azure", "Cloud storage / infrastructure", _PROC, "United States"),
    "@sentry": ("Sentry", "Error monitoring", _THIRD, "United States"),
    "@segment": ("Segment", "Customer data platform", _ANALYTICS, "United States"),
    "@stripe": ("Stripe", "Payments", _PROC, "United States"),
    "@twilio": ("Twilio", "SMS / communications", _PROC, "United States"),
    "@prisma": None,  # first-party ORM, not a data recipient
}


def _resolve_package(name: str) -> tuple[str, str, str, str | None] | None:
    """Map a package/module token to a vendor entry, or None if not a known SDK."""
    n = name.strip().strip("'\"").lower()
    if not n or n.startswith((".", "/")):  # local/relative import
        return None
    if n.startswith("@"):
        return _NPM_SCOPE.get(n.split("/", 1)[0])
    head = re.split(r"[./]", n)[0]
    return _INTEGRATIONS.get(n) or _INTEGRATIONS.get(head)


# Import statement patterns.
_PY_IMPORT = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE)
_JS_IMPORT = re.compile(r"""(?:from|require\()\s*['"]([^'"]+)['"]""")
# requirements.txt token (strip version/extras/markers)
_REQ_TOKEN = re.compile(r"^\s*([A-Za-z0-9_.\-]+)")


@dataclass
class _Model:
    name: str
    fields: list[tuple[str, str | None]]  # (field_name, data_type)


# --- Small helpers --------------------------------------------------------------

def _balanced(text: str, open_pos: int, open_ch: str, close_ch: str) -> tuple[str, int]:
    """Return (inner_text, end_pos) for the balanced block starting at open_pos.

    open_pos must point at the opening delimiter. end_pos is the index just after
    the matching close delimiter. If unbalanced, returns the remainder.
    """
    depth = 0
    i = open_pos
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[open_pos + 1 : i], i + 1
        i += 1
    return text[open_pos + 1 :], n


# --- SQL DDL --------------------------------------------------------------------
_SQL_TABLE = re.compile(
    r"create\s+table\s+(?:if\s+not\s+exists\s+)?[`\"\[]?([A-Za-z_][\w.]*)[`\"\]]?\s*\(",
    re.IGNORECASE,
)
_SQL_CONSTRAINT_KW = (
    "primary", "foreign", "constraint", "unique", "check", "key", "index",
    "exclude", "like", "partition",
)


def _split_top_level(body: str) -> list[str]:
    parts, depth, cur = [], 0, []
    for ch in body:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return parts


def _extract_sql(text: str) -> list[_Model]:
    models: list[_Model] = []
    for m in _SQL_TABLE.finditer(text):
        table = m.group(1).split(".")[-1]
        body, _ = _balanced(text, m.end() - 1, "(", ")")
        fields: list[tuple[str, str | None]] = []
        for raw in _split_top_level(body):
            col = raw.strip()
            if not col:
                continue
            first = col.split()[0].strip("`\"[]").lower()
            if first in _SQL_CONSTRAINT_KW:
                continue
            tokens = col.replace("`", "").replace('"', "").split()
            name = tokens[0].strip("[]")
            dtype = tokens[1] if len(tokens) > 1 else None
            if name:
                fields.append((name, dtype))
        if fields:
            models.append(_Model(table, fields))
    return models


# --- Python ORM / dataclass / pydantic -----------------------------------------
_PY_CLASS = re.compile(r"^(\s*)class\s+([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?\s*:")
_PY_TABLENAME = re.compile(r"""^\s*__tablename__\s*=\s*['"]([^'"]+)['"]""")
# name = models.EmailField(...) | Column(...) | db.Column(...) | mapped_column(...)
_PY_ASSIGN_CALL = re.compile(
    r"^\s*([a-zA-Z_]\w*)\s*(?::\s*[^=]+?)?=\s*(?:[\w.]*\.)?(\w+)\s*\("
)
# name: str = ... | name: Optional[int]
_PY_ANNOTATION = re.compile(r"^\s*([a-zA-Z_]\w*)\s*:\s*([A-Za-z_][\w\[\], .\"']*?)\s*(?:=|$)")

# Base-class hints that mark a class as a persisted data model.
_PY_MODEL_BASE_HINTS = (
    "Model", "Base", "BaseModel", "SQLModel", "Document", "Schema", "Table",
)
_PY_SKIP_CALLS = {"Manager", "Meta", "Config", "property", "classmethod", "staticmethod"}


def _py_is_model_class(bases: str | None, decorated: bool) -> bool:
    if decorated:  # @dataclass / @pydantic.dataclass etc.
        return True
    if not bases:
        return False
    return any(hint in bases for hint in _PY_MODEL_BASE_HINTS)


def _py_field(line: str) -> tuple[str, str | None] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith(("#", "@", "def ", "async def ", "class ")):
        return None
    call = _PY_ASSIGN_CALL.match(line)
    if call:
        name, ctype = call.group(1), call.group(2)
        if name.startswith("_") or ctype in _PY_SKIP_CALLS:
            return None
        return name, ctype
    ann = _PY_ANNOTATION.match(line)
    if ann:
        name, atype = ann.group(1), ann.group(2).strip()
        if name.startswith("_"):
            return None
        return name, atype
    return None


def _extract_python(text: str) -> list[_Model]:
    models: list[_Model] = []
    lines = text.splitlines()
    n = len(lines)
    i = 0
    pending_decorator = False
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("@"):
            pending_decorator = "dataclass" in stripped or "pydantic" in stripped
            i += 1
            continue
        m = _PY_CLASS.match(line)
        if not m:
            if stripped:
                pending_decorator = False
            i += 1
            continue

        indent = len(m.group(1))
        class_name = m.group(2)
        bases = m.group(3)
        is_model = _py_is_model_class(bases, pending_decorator)
        pending_decorator = False
        i += 1

        tablename: str | None = None
        fields: list[tuple[str, str | None]] = []
        while i < n:
            body_line = lines[i]
            if not body_line.strip():
                i += 1
                continue
            cur_indent = len(body_line) - len(body_line.lstrip())
            if cur_indent <= indent:
                break  # dedent -> class body ended
            tn = _PY_TABLENAME.match(body_line)
            if tn:
                tablename = tn.group(1)
                i += 1
                continue
            fld = _py_field(body_line)
            if fld:
                fields.append(fld)
            i += 1

        if is_model and fields:
            models.append(_Model(tablename or class_name, fields))
    return models


# --- Prisma schema --------------------------------------------------------------
_PRISMA_MODEL = re.compile(r"model\s+([A-Za-z_]\w*)\s*\{")
_PRISMA_FIELD = re.compile(r"^\s*([a-zA-Z_]\w*)\s+([A-Za-z_]\w*)")


def _extract_prisma(text: str) -> list[_Model]:
    models: list[_Model] = []
    for m in _PRISMA_MODEL.finditer(text):
        body, _ = _balanced(text, m.end() - 1, "{", "}")
        fields: list[tuple[str, str | None]] = []
        for raw in body.splitlines():
            line = raw.strip()
            if not line or line.startswith(("@@", "//")):
                continue
            fm = _PRISMA_FIELD.match(line)
            if fm:
                fields.append((fm.group(1), fm.group(2)))
        if fields:
            models.append(_Model(m.group(1), fields))
    return models


# --- TypeScript interfaces / type aliases --------------------------------------
_TS_INTERFACE = re.compile(r"(?:export\s+)?interface\s+([A-Za-z_]\w*)\s*(?:extends\s+[^{]+)?\{")
_TS_TYPE = re.compile(r"(?:export\s+)?type\s+([A-Za-z_]\w*)\s*=\s*\{")
_TS_FIELD = re.compile(r"^\s*(?:readonly\s+)?([a-zA-Z_]\w*)\s*\??\s*:\s*([^;{}\n]+)")


def _extract_typescript(text: str) -> list[_Model]:
    models: list[_Model] = []
    for pattern in (_TS_INTERFACE, _TS_TYPE):
        for m in pattern.finditer(text):
            brace = text.find("{", m.start())
            if brace == -1:
                continue
            body, _ = _balanced(text, brace, "{", "}")
            fields: list[tuple[str, str | None]] = []
            for raw in body.splitlines():
                line = raw.strip()
                if not line or line.startswith(("//", "*", "/*")):
                    continue
                if "(" in line.split(":", 1)[0]:  # method signature
                    continue
                fm = _TS_FIELD.match(line)
                if fm:
                    fields.append((fm.group(1), fm.group(2).strip()))
            if fields:
                models.append(_Model(m.group(1), fields))
    return models


# --- Go structs -----------------------------------------------------------------
_GO_STRUCT = re.compile(r"type\s+([A-Za-z_]\w*)\s+struct\s*\{")
_GO_FIELD = re.compile(r"^\s*([A-Z]\w*)\s+[\w./*\[\]]+")
_GO_JSON_TAG = re.compile(r'json:"([^",]+)"')


def _extract_go(text: str) -> list[_Model]:
    models: list[_Model] = []
    for m in _GO_STRUCT.finditer(text):
        body, _ = _balanced(text, m.end() - 1, "{", "}")
        fields: list[tuple[str, str | None]] = []
        for raw in body.splitlines():
            line = raw.strip()
            if not line or line.startswith("//"):
                continue
            fm = _GO_FIELD.match(line)
            if not fm:
                continue
            name = fm.group(1)
            tag = _GO_JSON_TAG.search(line)
            if tag and tag.group(1) != "-":
                name = tag.group(1)
            # data type is the second whitespace-delimited token
            parts = line.split()
            dtype = parts[1] if len(parts) > 1 else None
            fields.append((name, dtype))
        if fields:
            models.append(_Model(m.group(1), fields))
    return models


# --- Mongoose schemas (JS/TS) ---------------------------------------------------
_MONGOOSE_ASSIGN = re.compile(
    r"([A-Za-z_]\w*)\s*=\s*(?:new\s+)?(?:mongoose\.)?Schema\s*\(\s*\{"
)
_MONGOOSE_FIELD = re.compile(r"^\s*([a-zA-Z_]\w*)\s*:")


def _extract_mongoose(text: str) -> list[_Model]:
    models: list[_Model] = []
    for m in _MONGOOSE_ASSIGN.finditer(text):
        brace = text.find("{", m.start())
        if brace == -1:
            continue
        body, _ = _balanced(text, brace, "{", "}")
        fields: list[tuple[str, str | None]] = []
        depth = 0
        for raw in body.splitlines():
            line = raw.strip()
            # only capture top-level keys of the schema object
            if depth == 0 and (fm := _MONGOOSE_FIELD.match(line)):
                fields.append((fm.group(1), None))
            depth += line.count("{") - line.count("}")
        raw_name = re.sub(r"(?i)schema$", "", m.group(1)) or m.group(1)
        name = raw_name[:1].upper() + raw_name[1:]
        if fields:
            models.append(_Model(name, fields))
    return models


def _extract_javascript(text: str) -> list[_Model]:
    return _extract_mongoose(text)


def _extract_typescript_all(text: str) -> list[_Model]:
    return _extract_typescript(text) + _extract_mongoose(text)


_EXTRACTORS = {
    "sql": _extract_sql,
    "python": _extract_python,
    "prisma": _extract_prisma,
    "typescript": _extract_typescript_all,
    "javascript": _extract_javascript,
    "go": _extract_go,
}


def extract_models(text: str, lang: str) -> list[_Model]:
    """Public helper (used by tests): extract data models from source text."""
    extractor = _EXTRACTORS.get(lang)
    return extractor(text) if extractor else []


def _tokens_from_source(text: str, ext: str) -> set[str]:
    """Package/module tokens imported by a source file."""
    tokens: set[str] = set()
    if ext == ".py":
        for m in _PY_IMPORT.finditer(text):
            tokens.add(m.group(1) or m.group(2))
    else:  # JS/TS family
        for m in _JS_IMPORT.finditer(text):
            tokens.add(m.group(1))
    return {t for t in tokens if t}


def _tokens_from_manifest(text: str, filename: str) -> set[str]:
    """Dependency names declared in a manifest file (strongest signal)."""
    name = filename.rsplit("/", 1)[-1].lower()
    tokens: set[str] = set()
    if name == "package.json":
        try:
            data = json.loads(text)
        except ValueError:
            return tokens
        for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            deps = data.get(key)
            if isinstance(deps, dict):
                tokens.update(deps.keys())
    elif name in {"requirements.txt", "requirements-dev.txt"} or name.endswith(".txt") and "require" in name:
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "-")):
                continue
            m = _REQ_TOKEN.match(line)
            if m:
                tokens.add(m.group(1))
    elif name == "pyproject.toml":
        # Lightweight: pull quoted/bare dependency names without a TOML parser.
        for m in re.finditer(r"""["']?([A-Za-z0-9_.\-]+)["']?\s*(?:[<>=~!]=?|,|$)""", text):
            tokens.add(m.group(1))
    return {t for t in tokens if t}


_MANIFEST_NAMES = {"package.json", "requirements.txt", "requirements-dev.txt", "pyproject.toml"}


class CodebaseConnector(BaseConnector):
    """Static source-code scanner over an uploaded repository zip.

    Read-only and never executes scanned code. Emits one DiscoveredAsset per
    detected data model, with fields the classifier evaluates by name/type.
    """

    def __init__(self, content: bytes, filename: str = "repository.zip"):
        self._content = content
        self._filename = filename
        self._integrations: list[DiscoveredIntegration] = []
        self._code_risks: list[DiscoveredCodeRisk] = []
        self._scanned = False

    @property
    def app_name(self) -> str:
        """Human label for the scanned application (derived from the archive name)."""
        base = self._filename.replace("\\", "/").rsplit("/", 1)[-1]
        return re.sub(r"\.zip$", "", base, flags=re.IGNORECASE) or "application"

    def test_connection(self) -> tuple[bool, str]:
        try:
            with zipfile.ZipFile(io.BytesIO(self._content)) as zf:
                bad = zf.testzip()
            if bad is not None:
                return False, "Archive is corrupted."
            return True, "Repository archive read successfully."
        except zipfile.BadZipFile:
            return False, "Uploaded file is not a valid .zip archive."
        except Exception as exc:  # noqa: BLE001
            return False, f"Archive read failed: {type(exc).__name__}"

    @staticmethod
    def _should_skip(path: str) -> bool:
        parts = path.replace("\\", "/").split("/")
        return any(p in _SKIP_DIR_PARTS for p in parts)

    def discover(self) -> list[DiscoveredAsset]:
        """Single pass: extract data models (assets) and detect third-party SDKs.

        Also emits one APPLICATION asset representing the codebase itself, which
        acts as the source node for outbound flows to detected vendors.
        """
        assets: list[DiscoveredAsset] = []
        # vendor_name -> (integration entry, evidence)
        found: dict[str, DiscoveredIntegration] = {}
        code_risks: list[DiscoveredCodeRisk] = []
        total_uncompressed = 0
        files_scanned = 0

        def _register(token: str, where: str) -> None:
            entry = _resolve_package(token)
            if not entry:
                return
            vendor_name, service_type, flow_type, country = entry
            if vendor_name not in found:
                found[vendor_name] = DiscoveredIntegration(
                    vendor_name=vendor_name,
                    service_type=service_type,
                    flow_type=flow_type,
                    country=country,
                    evidence=f"{token} in {where}",
                )

        with zipfile.ZipFile(io.BytesIO(self._content)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if files_scanned >= _MAX_FILES or len(assets) >= _MAX_MODELS:
                    break
                path = info.filename
                if self._should_skip(path):
                    continue
                rel = path.replace("\\", "/")
                base = rel.rsplit("/", 1)[-1].lower()
                ext = "." + rel.rsplit(".", 1)[-1].lower() if "." in base else ""
                is_manifest = base in _MANIFEST_NAMES
                lang = _EXT_LANG.get(ext)
                scan_imports = ext in _IMPORT_EXTS
                if not (lang or is_manifest or scan_imports):
                    continue
                if info.file_size > _MAX_FILE_BYTES:
                    continue
                total_uncompressed += info.file_size
                if total_uncompressed > _MAX_TOTAL_UNCOMPRESSED:
                    break
                try:
                    raw = zf.read(info)
                except Exception:  # noqa: BLE001
                    continue
                text = raw.decode("utf-8", errors="replace")
                files_scanned += 1

                # 1) Model extraction -> DATASET assets.
                if lang:
                    for model in extract_models(text, lang):
                        if len(assets) >= _MAX_MODELS:
                            break
                        fields = [
                            DiscoveredField(name=fname, data_type=dtype)
                            for fname, dtype in model.fields
                        ]
                        if not fields:
                            continue
                        assets.append(
                            DiscoveredAsset(
                                name=f"{rel}::{model.name}",
                                display_name=model.name,
                                asset_type=AssetType.DATASET.value,
                                system_name=lang,
                                environment="codebase",
                                row_count=None,
                                fields=fields,
                            )
                        )

                # 2) Third-party SDK detection (imports + dependency manifests).
                if scan_imports:
                    for token in _tokens_from_source(text, ext):
                        _register(token, rel)
                if is_manifest:
                    for token in _tokens_from_manifest(text, rel):
                        _register(token, rel)

                # 3) Static privacy risk analysis (PII in logs, PII -> SDK).
                if scan_imports and len(code_risks) < _MAX_CODE_RISKS:
                    for risk in analyze_source(text):
                        if len(code_risks) >= _MAX_CODE_RISKS:
                            break
                        code_risks.append(
                            DiscoveredCodeRisk(
                                kind=risk.kind,
                                file_path=rel,
                                line_no=risk.line_no,
                                snippet=risk.snippet,
                                detail=risk.detail,
                                confidence=risk.confidence,
                            )
                        )

        self._integrations = list(found.values())
        self._code_risks = code_risks
        self._scanned = True

        # Application node representing the scanned codebase (source of outbound flows).
        assets.insert(
            0,
            DiscoveredAsset(
                name=f"{self.app_name}::__application__",
                display_name=self.app_name,
                asset_type=AssetType.APPLICATION.value,
                system_name="codebase",
                environment="codebase",
                row_count=None,
                fields=[],
            ),
        )
        return assets

    def discover_integrations(self) -> list[DiscoveredIntegration]:
        """Third-party services detected during discover(). Runs discover() if needed."""
        if not self._scanned:
            self.discover()
        return self._integrations

    def discover_code_risks(self) -> list[DiscoveredCodeRisk]:
        """Static privacy risks detected during discover(). Runs discover() if needed."""
        if not self._scanned:
            self.discover()
        return self._code_risks
