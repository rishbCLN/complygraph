"""Behavioral tests: verdicts, determinism, per-framework validity, exit codes.

These lock in the mapping from ComplyGraph's real deterministic control engine to
the frozen Assurance Contract v1 proof pack.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from assurance_contract import validate_proof_pack

from complygraph_assurance import (
    available_frameworks,
    build_assurance_pack,
    evaluate_compliance,
    write_assurance,
)
from complygraph_assurance.engine_bridge import InputError

FRAMEWORKS = ("dpdp", "soc2", "gdpr")


def _pack(target: str, framework: str, seed: int = 1729) -> dict:
    result = evaluate_compliance(target, framework=framework)
    return build_assurance_pack(result, seed=seed, target_ref=target, framework=framework)


# --------------------------------------------------------------------------- #
# Verdicts
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_reference_strong_passes(framework: str):
    pack = _pack("reference-strong", framework)
    assert pack["release_status"] == "PASS"
    assert pack["findings"] == []
    assert pack["headline"]["open_findings_total"] == 0


@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_reference_weak_is_blocked_with_critical_hard_blocker(framework: str):
    pack = _pack("reference-weak", framework)
    assert pack["release_status"] == "BLOCKED"
    assert pack["findings"], "weak target must produce findings"
    criticals = [f for f in pack["findings"] if f["severity"] == "critical"]
    assert criticals, "weak target must yield at least one critical finding"
    assert all(f["is_hard_blocker"] for f in criticals)
    # BLOCKED requires at least one hard blocker.
    assert any(f["is_hard_blocker"] for f in pack["findings"])


# --------------------------------------------------------------------------- #
# Contract validity across the full matrix
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("framework", FRAMEWORKS)
@pytest.mark.parametrize("target", ["reference-strong", "reference-weak"])
def test_every_pack_is_contract_valid(framework: str, target: str):
    validate_proof_pack(_pack(target, framework), raise_on_error=True)


def test_available_frameworks_matches_expected():
    assert set(available_frameworks()) == set(FRAMEWORKS)


# --------------------------------------------------------------------------- #
# Headline (Contract §6: complygraph)
# --------------------------------------------------------------------------- #
def test_headline_has_contract_recommended_keys():
    headline = _pack("reference-weak", "soc2")["headline"]
    for key in ("control_coverage", "open_findings_by_severity", "framework", "assessed_at"):
        assert key in headline, f"missing recommended headline key {key!r}"
    assert set(headline["open_findings_by_severity"]) == {
        "critical", "high", "medium", "low", "info"
    }
    assert 0.0 <= headline["control_coverage"] <= 1.0


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
def test_content_hash_is_stable_across_runs():
    a = _pack("reference-weak", "dpdp")
    b = _pack("reference-weak", "dpdp")
    assert a["manifest"]["content_hash"] == b["manifest"]["content_hash"]
    # Everything except the wall-clock created_at must be identical.
    a["manifest"].pop("created_at")
    b["manifest"].pop("created_at")
    assert a == b


def test_seed_is_recorded_and_changes_the_hash():
    a = _pack("reference-weak", "dpdp", seed=1)
    b = _pack("reference-weak", "dpdp", seed=2)
    assert a["manifest"]["seed"] == 1
    assert b["manifest"]["seed"] == 2
    assert a["manifest"]["content_hash"] != b["manifest"]["content_hash"]


def test_findings_sorted_by_severity_then_title():
    findings = _pack("reference-weak", "dpdp")["findings"]
    rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    keys = [(rank[f["severity"]], f["title"]) for f in findings]
    assert keys == sorted(keys)


# --------------------------------------------------------------------------- #
# Arbitrary target refs still produce a valid pack (ref preserved in manifest)
# --------------------------------------------------------------------------- #
def test_arbitrary_target_ref_is_preserved_and_valid():
    pack = _pack("org-12345", "soc2")
    validate_proof_pack(pack, raise_on_error=True)
    assert pack["manifest"]["target_ref"] == "org-12345"


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #
def test_unknown_framework_raises_input_error():
    with pytest.raises(InputError):
        evaluate_compliance("reference-strong", framework="hipaa")


def test_empty_target_raises_input_error():
    with pytest.raises(InputError):
        evaluate_compliance("   ", framework="soc2")


# --------------------------------------------------------------------------- #
# CLI exit codes (Contract §2.2): 0 pass, 1 blocked, 2 usage error
# --------------------------------------------------------------------------- #
def _cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "complygraph_assurance", *args],
        capture_output=True,
        text=True,
    )


def test_cli_exit_0_on_pass(tmp_path: Path):
    proc = _cli(tmp_path, "run", "reference-strong", "--seed", "7", "--out", str(tmp_path),
                "--framework", "soc2")
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "assurance.json").exists()


def test_cli_exit_1_on_blocked(tmp_path: Path):
    proc = _cli(tmp_path, "run", "reference-weak", "--seed", "7", "--out", str(tmp_path),
                "--framework", "soc2")
    assert proc.returncode == 1, proc.stderr
    pack = json.loads((tmp_path / "assurance.json").read_text(encoding="utf-8"))
    assert pack["release_status"] == "BLOCKED"


def test_cli_exit_2_on_unknown_framework(tmp_path: Path):
    proc = _cli(tmp_path, "run", "reference-strong", "--seed", "7", "--out", str(tmp_path),
                "--framework", "nope")
    assert proc.returncode == 2, (proc.returncode, proc.stderr)


def test_cli_exit_2_on_missing_required_arg(tmp_path: Path):
    # Missing --seed / --out -> argparse usage error -> exit 2.
    proc = _cli(tmp_path, "run", "reference-strong")
    assert proc.returncode == 2


def test_written_native_report_accompanies_pack(tmp_path: Path):
    result = evaluate_compliance("reference-weak", framework="gdpr")
    write_assurance(result, tmp_path, seed=99, target_ref="reference-weak", framework="gdpr")
    assert (tmp_path / "assurance.json").exists()
    assert (tmp_path / "complygraph.report.json").exists()
