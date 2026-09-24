"""Assurance Contract v1 CLI for the ComplyGraph compliance pillar.

Invocation (identical surface across all six engines, Contract §3 / §2.2):

    complygraph-assurance run <target_ref> --seed <int> --out <dir> --framework <fw> [--json]
    python -m complygraph_assurance run <target_ref> --seed <int> --out <dir> --framework <fw> [--json]

Exit codes (Contract §2.2):
    0  ran & not blocked (PASS / PASS_WITH_CONDITIONS)
    1  ran & BLOCKED (gate)
    2  usage / input error
    3  crash / inconsistent (fail-closed)
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from typing import Sequence

from . import __version__

EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_USAGE = 2
EXIT_CRASH = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="complygraph-assurance",
        description=(
            "Emit a Contract v1 assurance.json for the ComplyGraph compliance pillar. "
            "Runs infra-free (no Postgres/Redis) over ComplyGraph's real deterministic "
            "control engine and a bundled framework + assessed-state fixture."
        ),
    )
    parser.add_argument("--version", action="version", version=f"complygraph-assurance {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser(
        "run",
        help="Evaluate a target against a framework and write <out>/assurance.json.",
    )
    run.add_argument(
        "target_ref",
        help="Positional target reference (e.g. reference-strong, reference-weak, or an org/target id).",
    )
    run.add_argument("--seed", type=int, required=True, help="Deterministic seed (recorded in the manifest).")
    run.add_argument("--out", required=True, help="Output directory; assurance.json is written here.")
    run.add_argument(
        "--framework",
        default="soc2",
        help="Compliance framework id (bundled: dpdp, soc2, gdpr). Default: soc2.",
    )
    run.add_argument("--json", action="store_true", help="Also print the proof pack to stdout.")
    return parser


def _cmd_run(args: argparse.Namespace) -> int:
    # Import lazily so that argument parsing / --help never triggers the engine
    # locator or any heavier import.
    from . import builder
    from . import engine_bridge

    try:
        result = engine_bridge.evaluate_compliance(args.target_ref, framework=args.framework)
        pack_path = builder.write_assurance(
            result,
            args.out,
            seed=args.seed,
            target_ref=args.target_ref,
            framework=args.framework,
        )
    except engine_bridge.InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except engine_bridge.EngineNotFoundError as exc:
        # Environment/deployment problem -> fail closed as a crash.
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_CRASH
    except Exception:  # noqa: BLE001 - any unexpected failure is fail-closed (exit 3)
        traceback.print_exc()
        return EXIT_CRASH

    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    release_status = pack.get("release_status")

    if args.json:
        print(json.dumps(pack, indent=2, sort_keys=False))
    else:
        headline = pack.get("headline", {})
        print(f"engine={pack.get('engine')} version={pack.get('engine_version')}")
        print(f"framework={args.framework} target_ref={args.target_ref}")
        print(f"release_status={release_status}")
        print(
            "controls: "
            f"passed={headline.get('controls_passed')} "
            f"failed={headline.get('controls_failed')} "
            f"applicable={headline.get('controls_applicable')} "
            f"coverage={headline.get('coverage')}"
        )
        print(f"open_findings_by_severity={headline.get('open_findings_by_severity')}")
        print(f"wrote {pack_path}")

    return EXIT_BLOCKED if release_status == "BLOCKED" else EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    # argparse raises SystemExit(2) on a usage error; let that propagate so the
    # process exits 2 per the contract.
    args = parser.parse_args(argv)
    if args.command == "run":
        return _cmd_run(args)
    parser.error("no command given")  # pragma: no cover - subparsers are required
    return EXIT_USAGE


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
