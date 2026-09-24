"""Contract-conformance test (Assurance Contract v1).

Proves complygraph-assurance emits a Contract-v1-valid ``assurance.json``. If the
CLI surface or output shape drifts from the shared contract, this goes red.

Requires the shared package:  pip install -e D:\\orch_bench\\assurance_contract
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from assurance_contract import CONTRACT_VERSION, validate_proof_pack

from complygraph_assurance import evaluate_compliance, write_assurance

ENGINE = "complygraph"


def test_emits_valid_assurance_proof_pack(tmp_path: Path):
    # Library API (fast, no subprocess): evaluate + write <out>/assurance.json.
    result = evaluate_compliance("reference-strong", framework="soc2")
    pack_path = write_assurance(
        result, tmp_path, seed=1729, target_ref="reference-strong", framework="soc2"
    )

    assert pack_path.exists(), "engine did not write <out>/assurance.json"
    pack = json.loads(pack_path.read_text(encoding="utf-8"))

    # Full structural validation - raises with a precise message on any drift.
    validate_proof_pack(pack, raise_on_error=True)

    assert pack["engine"] == ENGINE
    assert pack["contract_version"].split(".")[0] == CONTRACT_VERSION.split(".")[0]
    # Drift guard: emitted contract_version must EXACTLY equal the shared source
    # of truth so an engine's hardcoded constant cannot silently diverge (even
    # within a major). Any drift fails this test, keeping the stack in sync.
    assert pack["contract_version"] == CONTRACT_VERSION, (
        f"{ENGINE} contract_version {pack['contract_version']!r} != "
        f"assurance_contract.CONTRACT_VERSION {CONTRACT_VERSION!r} (contract drift)"
    )


def test_cli_writes_valid_pack_and_honors_exit_codes(tmp_path: Path):
    # Exercises the real Contract v1 CLI surface via `python -m complygraph_assurance`.
    proc = subprocess.run(
        [
            sys.executable, "-m", "complygraph_assurance", "run", "reference-strong",
            "--seed", "1729", "--out", str(tmp_path), "--framework", "soc2", "--json",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1), f"unexpected exit {proc.returncode}: {proc.stderr}"

    pack_path = tmp_path / "assurance.json"
    assert pack_path.exists(), "CLI did not write <out>/assurance.json"
    validate_proof_pack(json.loads(pack_path.read_text(encoding="utf-8")), raise_on_error=True)

    # --json prints the machine-readable pack to stdout too.
    stdout_pack = json.loads(proc.stdout)
    assert stdout_pack["engine"] == ENGINE
