"""Architecture ingestion adapters.

Turns real infrastructure artifacts into the canonical architecture-import body
that :func:`ai_system_service.import_architecture` consumes
(``{"system": ..., "components": [...], "flows": [...]}``).

Design rules (mirror the fact-derivation contract):
  - Adapters only translate what is *observably present* in the artifact into
    components/flows. They never invent a legal conclusion or a fact the source
    does not support. Where residency/externality cannot be determined, the field
    is left unset so :func:`derive_facts_with_provenance` reports it as INFERRED /
    UNKNOWN rather than a confident value.
  - Every produced component carries a ``config.source`` breadcrumb naming the
    artifact and the original resource address, so an auditor can trace each node
    back to the infrastructure that produced it.

Supported sources:
  - ``terraform``: a ``terraform show -json`` state document (or plan). Managed
    resources become components; region and provider are read from attributes.
  - ``openapi``: an OpenAPI 3.x document. The API itself becomes a SERVICE
    component and each declared server/external host becomes a component with a
    flow from the API to it.
"""

from __future__ import annotations

from urllib.parse import urlparse

# Terraform resource type -> (component_type, external?) mapping. Anything not
# listed is still ingested as a generic SERVICE so nothing is silently dropped.
_TF_TYPE_MAP: dict[str, tuple[str, bool]] = {
    # Compute / inference hosts
    "aws_sagemaker_endpoint": ("MODEL", False),
    "aws_sagemaker_model": ("MODEL", False),
    "google_vertex_ai_endpoint": ("MODEL", False),
    "azurerm_machine_learning_inference_cluster": ("MODEL", False),
    "aws_lambda_function": ("SERVICE", False),
    "aws_instance": ("SERVICE", False),
    "aws_ecs_service": ("SERVICE", False),
    # Data stores
    "aws_db_instance": ("DATA_STORE", False),
    "aws_rds_cluster": ("DATA_STORE", False),
    "aws_dynamodb_table": ("DATA_STORE", False),
    "aws_s3_bucket": ("DATA_STORE", False),
    "aws_elasticache_cluster": ("DATA_STORE", False),
    "google_sql_database_instance": ("DATA_STORE", False),
    "azurerm_storage_account": ("DATA_STORE", False),
    # APIs / gateways
    "aws_api_gateway_rest_api": ("API", True),
    "aws_apigatewayv2_api": ("API", True),
    # Endpoints out
    "aws_sns_topic": ("ENDPOINT", False),
    "aws_sqs_queue": ("ENDPOINT", False),
}

# Region attribute keys that may appear on a Terraform resource's values.
_TF_REGION_KEYS = ("region", "location", "availability_zone", "az")

# AWS region prefix -> coarse residency tag used by the applicability engine.
_AWS_REGION_COUNTRY = {
    "ap-south-1": "India",
    "ap-south-2": "India",
}


class IngestError(ValueError):
    """Raised when an artifact cannot be parsed into an architecture body."""


def _region_to_tag(raw: str | None) -> str | None:
    if not raw:
        return None
    r = str(raw).strip()
    low = r.lower()
    # Direct AWS region ids.
    for prefix, tag in _AWS_REGION_COUNTRY.items():
        if low.startswith(prefix):
            return tag
    # An availability zone is the region id plus a trailing letter (ap-south-1a).
    for prefix, tag in _AWS_REGION_COUNTRY.items():
        if low.startswith(prefix.rstrip("0123456789")):
            return tag
    return r  # pass through unknown regions verbatim (reported as non-India)


def _iter_tf_resources(state: dict):
    """Yield (address, type, name, values) for every managed resource.

    Supports both ``terraform show -json`` state (values.root_module...) and the
    flatter ``resources`` list some tooling emits.
    """
    values = state.get("values")
    if isinstance(values, dict):
        root = values.get("root_module", {})

        def walk(module):
            for res in module.get("resources", []) or []:
                yield res
            for child in module.get("child_modules", []) or []:
                yield from walk(child)

        for res in walk(root):
            if res.get("mode") and res["mode"] != "managed":
                continue
            yield (
                res.get("address") or res.get("name"),
                res.get("type"),
                res.get("name"),
                res.get("values", {}) or {},
            )
        return

    # Fallback: raw state file with top-level "resources".
    for res in state.get("resources", []) or []:
        if res.get("mode") and res["mode"] != "managed":
            continue
        rtype = res.get("type")
        rname = res.get("name")
        for inst in res.get("instances", []) or []:
            attrs = inst.get("attributes", {}) or {}
            yield (f"{rtype}.{rname}", rtype, rname, attrs)


def from_terraform(state: dict, system: dict) -> dict:
    """Build an architecture-import body from a Terraform state/plan document.

    ``system`` is the system-level metadata dict (name, sector, ...) supplied by
    the caller; the adapter only fills in components. No flows are inferred from
    Terraform (dependency edges are not reliably data-flow edges); flows are left
    to explicit modelling or the OpenAPI adapter.
    """
    if not isinstance(state, dict):
        raise IngestError("Terraform artifact must be a JSON object.")

    components: list[dict] = []
    seen: set[str] = set()
    for address, rtype, rname, values in _iter_tf_resources(state):
        if not rtype:
            continue
        comp_type, external = _TF_TYPE_MAP.get(rtype, ("SERVICE", False))
        region_raw = None
        for key in _TF_REGION_KEYS:
            if values.get(key):
                region_raw = values[key]
                break
        key = address or f"{rtype}.{rname}"
        if key in seen:
            continue
        seen.add(key)
        name = values.get("name") or values.get("function_name") or rname or key
        components.append(
            {
                "key": key,
                "name": str(name),
                "component_type": comp_type,
                "external": external,
                "region": _region_to_tag(region_raw),
                "provider": rtype.split("_", 1)[0] if "_" in rtype else rtype,
                "config": {"source": "terraform", "resource": key, "tf_type": rtype},
            }
        )

    if not components:
        raise IngestError(
            "No managed resources found in the Terraform artifact. Provide the "
            "output of `terraform show -json` for an applied state."
        )
    return {"system": system, "components": components, "flows": []}


def _openapi_host(url: str) -> str | None:
    try:
        parsed = urlparse(url if "//" in url else f"//{url}")
        return parsed.hostname
    except (ValueError, AttributeError):
        return None


def _host_is_external(host: str | None) -> bool:
    """A host is treated as external unless it is clearly loopback/internal."""
    if not host:
        return False
    low = host.lower()
    if low in {"localhost", "127.0.0.1", "::1"}:
        return False
    # Internal cluster DNS suffixes.
    if low.endswith(".local") or low.endswith(".svc") or low.endswith(".internal"):
        return False
    return True


def from_openapi(spec: dict, system: dict) -> dict:
    """Build an architecture-import body from an OpenAPI 3.x document.

    The API surface becomes a SERVICE component; each distinct server host and
    each external host referenced by an operation's ``servers`` override becomes
    a component with a flow from the API to it. Personal-data categories are not
    inferred from the schema (that would be a guess); they are left unset.
    """
    if not isinstance(spec, dict) or "openapi" not in spec:
        raise IngestError("OpenAPI artifact must be a JSON object with an 'openapi' field.")

    info = spec.get("info", {}) or {}
    api_name = info.get("title") or system.get("name") or "API"
    api_key = "api"
    components: list[dict] = [
        {
            "key": api_key,
            "name": str(api_name),
            "component_type": "API",
            "external": False,
            "config": {"source": "openapi", "version": info.get("version")},
        }
    ]
    flows: list[dict] = []
    host_keys: dict[str, str] = {}

    def ensure_host(url: str) -> str | None:
        host = _openapi_host(url)
        if not host:
            return None
        if host in host_keys:
            return host_keys[host]
        key = f"host:{host}"
        host_keys[host] = key
        components.append(
            {
                "key": key,
                "name": host,
                "component_type": "SERVICE",
                "external": _host_is_external(host),
                "config": {"source": "openapi", "host": host},
            }
        )
        flows.append(
            {
                "from": api_key,
                "to": key,
                "relation": "DEPENDS_ON",
                "purpose": f"Server declared for {api_name}",
            }
        )
        return key

    for server in spec.get("servers", []) or []:
        if isinstance(server, dict) and server.get("url"):
            ensure_host(server["url"])

    # Operation-level server overrides (often point at external dependencies).
    for path_item in (spec.get("paths", {}) or {}).values():
        if not isinstance(path_item, dict):
            continue
        for op in path_item.values():
            if not isinstance(op, dict):
                continue
            for server in op.get("servers", []) or []:
                if isinstance(server, dict) and server.get("url"):
                    ensure_host(server["url"])

    return {"system": system, "components": components, "flows": flows}


def build_import_body(source: str, artifact: dict, system: dict) -> dict:
    """Dispatch to the adapter for ``source`` and return an import body."""
    source_norm = (source or "").strip().lower()
    if source_norm == "terraform":
        return from_terraform(artifact, system)
    if source_norm == "openapi":
        return from_openapi(artifact, system)
    raise IngestError(
        f"Unsupported ingestion source '{source}'. Supported: terraform, openapi."
    )
