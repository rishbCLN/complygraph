"""Architecture ingestion adapter tests (Feature #3).

These verify the adapters translate real infrastructure artifacts into the
canonical import body without inventing facts: observable residency/externality
is mapped, and anything the artifact does not state is left unset so the analysis
engine reports it as inferred rather than assumed.
"""

from __future__ import annotations

import pytest

from app.services import arch_ingest


# --- Terraform ------------------------------------------------------------------


def _tf_state() -> dict:
    """A minimal `terraform show -json` state with a mix of resources."""
    return {
        "values": {
            "root_module": {
                "resources": [
                    {
                        "address": "aws_sagemaker_endpoint.scorer",
                        "mode": "managed",
                        "type": "aws_sagemaker_endpoint",
                        "name": "scorer",
                        "values": {"name": "credit-scorer", "region": "us-east-1"},
                    },
                    {
                        "address": "aws_db_instance.features",
                        "mode": "managed",
                        "type": "aws_db_instance",
                        "name": "features",
                        "values": {"identifier": "feature-store", "region": "ap-south-1"},
                    },
                    {
                        "address": "data.aws_ami.base",
                        "mode": "data",
                        "type": "aws_ami",
                        "name": "base",
                        "values": {},
                    },
                ],
                "child_modules": [
                    {
                        "resources": [
                            {
                                "address": "module.net.aws_api_gateway_rest_api.gw",
                                "mode": "managed",
                                "type": "aws_api_gateway_rest_api",
                                "name": "gw",
                                "values": {"name": "public-api", "region": "ap-south-1"},
                            }
                        ]
                    }
                ],
            }
        }
    }


def test_terraform_maps_resources_to_components():
    body = arch_ingest.from_terraform(_tf_state(), {"name": "TF System", "sector": "bfsi"})
    comps = {c["key"]: c for c in body["components"]}

    # Data-only resource is skipped; three managed resources ingested.
    assert "data.aws_ami.base" not in comps
    assert len(comps) == 3

    scorer = comps["aws_sagemaker_endpoint.scorer"]
    assert scorer["component_type"] == "MODEL"
    assert scorer["name"] == "credit-scorer"
    assert scorer["region"] == "us-east-1"  # non-India region passed through
    assert scorer["config"]["source"] == "terraform"

    store = comps["aws_db_instance.features"]
    assert store["component_type"] == "DATA_STORE"
    assert store["region"] == "India"  # ap-south-1 normalized to India

    gw = comps["module.net.aws_api_gateway_rest_api.gw"]
    assert gw["component_type"] == "API"
    assert gw["external"] is True


def test_terraform_supports_raw_state_resources_shape():
    raw = {
        "resources": [
            {
                "mode": "managed",
                "type": "aws_s3_bucket",
                "name": "docs",
                "instances": [{"attributes": {"bucket": "docs-bkt", "region": "ap-south-1a"}}],
            }
        ]
    }
    body = arch_ingest.from_terraform(raw, {"name": "Raw"})
    assert len(body["components"]) == 1
    comp = body["components"][0]
    assert comp["component_type"] == "DATA_STORE"
    assert comp["region"] == "India"  # availability zone normalized


def test_terraform_empty_raises():
    with pytest.raises(arch_ingest.IngestError):
        arch_ingest.from_terraform({"values": {"root_module": {}}}, {"name": "Empty"})


# --- OpenAPI --------------------------------------------------------------------


def _openapi_spec() -> dict:
    return {
        "openapi": "3.0.1",
        "info": {"title": "Scoring API", "version": "1.2.0"},
        "servers": [{"url": "https://api.internal.svc/v1"}],
        "paths": {
            "/score": {
                "post": {
                    "servers": [{"url": "https://api.openai.com/v1"}],
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }


def test_openapi_builds_api_and_hosts():
    body = arch_ingest.from_openapi(_openapi_spec(), {"name": "OAS System", "sector": "bfsi"})
    comps = {c["key"]: c for c in body["components"]}

    assert "api" in comps
    assert comps["api"]["component_type"] == "API"

    internal = comps["host:api.internal.svc"]
    assert internal["external"] is False  # .svc suffix treated as internal

    external = comps["host:api.openai.com"]
    assert external["external"] is True

    # A flow links the API to each host.
    targets = {f["to"] for f in body["flows"]}
    assert "host:api.internal.svc" in targets
    assert "host:api.openai.com" in targets


def test_openapi_requires_openapi_field():
    with pytest.raises(arch_ingest.IngestError):
        arch_ingest.from_openapi({"swagger": "2.0"}, {"name": "Old"})


# --- Dispatch -------------------------------------------------------------------


def test_build_import_body_dispatch_and_unknown_source():
    tf = arch_ingest.build_import_body("terraform", _tf_state(), {"name": "X"})
    assert tf["components"]
    with pytest.raises(arch_ingest.IngestError):
        arch_ingest.build_import_body("cloudformation", {}, {"name": "X"})
