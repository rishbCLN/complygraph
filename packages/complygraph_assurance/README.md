# complygraph-assurance

Thin, **infra-free** [Assurance Contract v1](../../ASSURANCE_CONTRACT.md) export for the
ComplyGraph **compliance** pillar.

ComplyGraph proper is a long-running SaaS (FastAPI + Postgres + Redis + Celery) and
cannot be imported into the Keystone control plane in-process. This package is the
dedicated **batch assurance-export** the control plane invokes over subprocess: it
produces a schema-valid `assurance.json` proof pack **without** Postgres, Redis, or the
web framework.

## What it reuses

The compliance verdict is produced by ComplyGraph's **real deterministic control
engine** (`app.controls.engine`, `app.controls.applicability`,
`app.controls.effective_date`, `app.controls.risk`). Those modules are standard-library
only, so they run with no infrastructure. This package locates them inside the
ComplyGraph repo at runtime (never at import time) and drives them over a bundled
control-library + assessed-state fixture — the same `ControlContext` shape the SaaS
builds from Postgres.

## CLI (Contract v1)

```
complygraph-assurance run <target_ref> --seed <int> --out <dir> --framework <fw> [--json]
python -m complygraph_assurance run <target_ref> --seed <int> --out <dir> --framework <fw> [--json]
```

Exit codes: `0` ran & not blocked · `1` ran & BLOCKED · `2` usage/input error ·
`3` crash (fail-closed).

Bundled frameworks: `dpdp` (ComplyGraph's real DPDP Act 2023 / DPDP Rules 2025 control
library), `soc2`, `gdpr`. Bundled reference targets: `reference-strong` (compliant →
PASS) and `reference-weak` (materially non-compliant → BLOCKED with critical findings).

## Library API

```python
from complygraph_assurance import evaluate_compliance, build_assurance_pack, write_assurance

result = evaluate_compliance("reference-strong", framework="soc2")
pack = build_assurance_pack(result, seed=1729, target_ref="reference-strong", framework="soc2")
path = write_assurance(result, "out/", seed=1729, target_ref="reference-strong", framework="soc2")
```

The proof pack is engineering signal, **not** a legal certification.
