# ComplyGraph

Continuous Data Governance & Compliance infrastructure for the Digital Personal
Data Protection Act, 2023 and the DPDP Rules, 2025.

ComplyGraph discovers where personal data lives, maps how it flows, evaluates
deterministic controls against a real regulatory library, produces prioritized
findings with an internal risk score, and lets an AI assistant *investigate*
findings using only sanitized, non-identifying evidence.

> ComplyGraph is software for governance, evidence collection, and internal
> control assessment. It is **not** a law firm and does **not** provide legal
> certification of compliance. Every AI output is advisory and flagged for human
> legal review.

## Design principles

- **Deterministic first, AI advisory only.** Control status is decided by a
  deterministic engine. The AI never determines compliance; it explains and
  investigates evidence the platform already collected.
- **Never persist raw PII.** Scans classify data in-memory and store only masked
  examples and redacted evidence. AI inputs are sanitized (emails, phone numbers,
  tokens, and secrets are redacted) before they ever leave the platform.
- **Effective dates, never "today".** Controls are evaluated against the
  organization's configurable `assessment_date`. Controls not yet in force are
  surfaced as `UPCOMING`, never as present failures.
- **Idempotent + explainable.** Scans dedupe by fingerprint; every finding and
  control assessment carries a human-readable reason.

## Architecture

Modular monolith:

- **`apps/api`** — FastAPI backend (19 routers), SQLAlchemy models, deterministic
  scanner/classifier, regulatory + control engine, risk scoring, findings, AI
  investigation service, reporting (JSON/CSV/PDF), Celery workers.
- **`apps/web`** — Next.js frontend (dashboard, data map, findings, reports).

### Formulas

- **PII confidence** = `0.45*name + 0.45*pattern + 0.10*type`
  (bands: HIGH ≥ 0.85, MEDIUM ≥ 0.65, LOW < 0.65).
- **Risk score** = `round((0.35*sensitivity + 0.25*exposure + 0.25*control_gap + 0.15*volume) / 5 * 100)`
  (severity: CRITICAL ≥ 80, HIGH ≥ 60, MEDIUM ≥ 35, else LOW).

## Running with Docker Compose

Requires Docker. Brings up PostgreSQL, Redis, the API (with migrations + demo
seed), a Celery worker, and the web frontend.

```bash
cp .env.example .env
docker compose up --build
```

- API:  http://localhost:8000  (docs at `/docs`)
- Web:  http://localhost:3000

## Running locally (no Docker)

The app runs with **zero external services**: SQLite for storage, Celery in eager
mode when Redis is absent, and the synthetic `DemoConnector` for AsterLane data.

Requires **Python 3.12.x** (3.14 is too new for the pinned `pydantic-core` wheel)
and Node 20+ with pnpm for the frontend.

PowerShell (Windows):

```powershell
# 1. Create a local virtualenv + install deps (or set VENV_PYTHON to reuse one)
pwsh scripts\setup.ps1

# 2. Seed the DPDP control library + AsterLane demo org (idempotent)
pwsh scripts\seed.ps1

# 3. Run the API with hot reload (migrates + seeds, then serves)
pwsh scripts\dev-api.ps1
```

To reuse an existing interpreter instead of creating `.venv`:

```powershell
$env:VENV_PYTHON = "E:\complygraph-venv\Scripts\python.exe"
pwsh scripts\seed.ps1
```

The default `DATABASE_URL` is `sqlite:///./complygraph.db` and `DEMO_DATABASE_URL`
is empty, so the DemoConnector uses synthetic in-memory data.

## Demo login (development only)

Fixed assessment date: **2026-09-19**. All six demo users share one password.

| Email                       | Role             |
| --------------------------- | ---------------- |
| admin@asterlane.demo        | ADMIN            |
| privacy@asterlane.demo      | PRIVACY_OFFICER  |
| security@asterlane.demo     | SECURITY_ANALYST |
| engineer@asterlane.demo     | ENGINEER         |
| auditor@asterlane.demo      | AUDITOR          |
| viewer@asterlane.demo       | VIEWER           |

Password: `DemoPass123!`

## Testing

```powershell
pwsh scripts\test.ps1            # full suite
pwsh scripts\test.ps1 tests/unit # a subset
```

Tests run against a throwaway SQLite database created by the fixtures, so the
local `complygraph.db` is never touched. Coverage includes:

- **Unit** — classifier confidence/bands, risk scoring/severity, control
  evaluators, effective-date engine, AI input sanitization.
- **Security** — tenant isolation via the `x-organization-id` header.
- **E2E** — auth, findings, inventory, dashboard, graph, AI investigation, and
  report generation against the seeded demo org.

## AI configuration

Set `ANTHROPIC_API_KEY` and `AI_MODE=anthropic` to enable the Anthropic adapter;
otherwise the platform runs in `deterministic` mode and still produces useful
investigation output offline. Model name is centralized via `ANTHROPIC_MODEL`.
