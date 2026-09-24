# ComplyGraph — Production Readiness Runbook

**Package:** full-stack app (`apps/api` FastAPI + `apps/web` Next.js)
**Role in the ecosystem:** Compliance engine (the `compliance` pillar). A
multi-tenant compliance / data-governance platform: findings, controls, data
assets, AI investigations (advisory only), tickets, and audit logging, with cookie
sessions, MFA, and per-organization scoping.

> Maturity today: **The most production-shaped infrastructure** of the six (real
> CI, Dockerfiles, `docker-compose`, Alembic migrations, Postgres + Redis + Celery),
> but it is architecturally **divergent**: it is a long-running SaaS, not a batch
> tool that emits a release proof pack. To join the assurance ecosystem it needs a
> dedicated **assurance-export** path, plus standard SaaS production hardening.

See `D:\assura\PRODUCTION_READINESS.md` §2 for the canonical **Assurance Contract v1**.

---

## 0. Definition of Done

- [ ] A non-interactive **assurance-export** (CLI command or authenticated endpoint) emits a schema-valid `assurance.json` for a target org/framework.
- [ ] `complygraph.db` (SQLite artifact) is no longer tracked; Postgres is the source of truth.
- [ ] No secrets/credentials are hardcoded; all come from env / a secret manager.
- [ ] A production deployment manifest exists (compose/Helm) with TLS, managed Postgres, Redis auth, health/readiness probes, and migrations-on-deploy.
- [ ] CI is extended with a coverage gate + dependency/secret scanning + SAST + image build.
- [ ] Structured logging, metrics, and tracing are wired across api / worker / web.
- [ ] The Keystone `compliance` pillar can consume the export (coordinate with `D:\assura` §5).

---

## 1. Ecosystem integration (synchronization) — the key design decision

ComplyGraph cannot participate the way the other engines do: it needs Postgres +
Redis and runs continuously, so the control plane **must not** import it in-process.
Instead, expose a **batch assurance-export** that produces the Contract v1 proof
pack, invoked by Keystone's `compliance` pillar over **subprocess or HTTP**.

**Tasks**
1. Add one of (prefer both):
   - **CLI:** `python -m app.assurance export --org <id> --framework <soc2|gdpr|...> --seed N --out DIR --json`
     (runs inside the api container where DB/Redis are reachable), writing
     `DIR/assurance.json`.
   - **Endpoint:** `POST /api/v1/assurance/export` (authenticated, org-scoped)
     returning the same proof pack.
2. Map ComplyGraph's domain to Contract v1:
   - Derive `release_status` from the assessment: any open **CRITICAL/hard-blocker**
     finding → `BLOCKED`; open high/medium with compensating controls →
     `PASS_WITH_CONDITIONS`; otherwise `PASS`.
   - Map each compliance `Finding` (`apps/api/app/models/findings.py`) to the shared
     Finding schema (title, severity, is_hard_blocker, what_happened, expected,
     actual, remediation, evidence, source_ref). Note the internal severity/status
     vocabulary (e.g., `contract_status="MISSING"` drives findings in
     `apps/api/scripts/seed.py`) — normalize it to `critical|high|medium|low|info`.
   - `headline`: control coverage %, open-findings-by-severity counts, framework id,
     assessment timestamp.
   - `manifest.content_hash`: a stable hash over the assessed state + seed.
3. Add a thin discovery package `complygraph_assurance` exposing `__version__` so
   Keystone discovery can detect the pillar (§2.5 of the contract).
4. Add a test that validates the exported `assurance.json` against
   `assurance_contract`.

> Alternative, if compliance should stay out of the automated release gate: document
> ComplyGraph as an **adjacent** product rather than a gated pillar, and drop the
> `compliance` pillar from Keystone. Pick one explicitly so the ecosystem story is
> coherent.

---

## 2. Repo hygiene

1. **Stop tracking `apps/api/complygraph.db`.** The app uses Postgres in
   `docker-compose.yml`; SQLite is for tests only (redirected in `conftest.py`).
   Untrack it and ignore:
   ```powershell
   git rm --cached apps/api/complygraph.db
   ```
   ```gitignore
   *.db
   *.sqlite3
   ```
2. Ensure `apps/web` build artifacts (`.next/`, `tsconfig.tsbuildinfo`,
   `node_modules/`) are ignored.

---

## 3. Security hardening (SaaS)

ComplyGraph already has cookie sessions, MFA, and org scoping (good). Harden for
production:
1. **Secrets management.** `docker-compose.yml` hardcodes
   `POSTGRES_PASSWORD=complygraph_dev_pw`. Move all secrets (DB, Redis, session
   signing keys, `ANTHROPIC_API_KEY`) to env / a secret manager; never commit them.
   Provide a production `.env` template distinct from the dev one.
2. **Transport & headers.** Terminate TLS at a reverse proxy; add HSTS, CSP,
   `X-Content-Type-Options`, `X-Frame-Options`, and secure/HttpOnly/SameSite cookie
   attributes (verify the session cookie flags).
3. **CORS** locked to known web origins (the web client sends `credentials: include`
   and an `x-organization-id` header — keep the allowlist tight).
4. **Rate limiting** on auth, MFA, and the AI-investigation endpoints.
5. **AI safety.** Investigations are advisory with PII sanitization + legal-review
   notices (`apps/web/app/(app)/findings/[id]/page.tsx`) — keep AI in
   `deterministic`/advisory posture by default; never let AI output mutate an
   audited compliance verdict without human action.
6. **Authorization tests.** Add tests asserting cross-org access is impossible for
   every endpoint (multi-tenant isolation is the highest-risk area).

---

## 4. Production infrastructure

The current `docker-compose.yml` is dev-oriented (bundled Postgres/Redis, no TLS).
Add a production deployment path:
1. Managed/external Postgres and Redis (with auth/TLS) via env, not bundled
   containers.
2. A reverse proxy / ingress with TLS for `web` and `api`.
3. **Migrations-on-deploy:** run Alembic (`apps/api/alembic/`) as an init/job step
   before api/worker start; don't auto-create schema at runtime in prod.
4. Health/readiness probes for api, worker, and web; Celery worker concurrency +
   autoscaling guidance; a defined broker/result backend retention policy.
5. Harden images: non-root user, pinned base image digests, `.dockerignore` review,
   minimal runtime layers.

---

## 5. CI/CD (extend what exists)

Current CI (`.github/workflows/ci.yml`) runs API pytest and web build/typecheck/lint.
Add:
1. **Coverage gate** on the API test job.
2. **Dependency scanning:** `pip-audit` (API) and `npm audit --audit-level=high`
   (web).
3. **SAST / secret scanning:** CodeQL or semgrep + a secret scanner (e.g.,
   gitleaks) on PRs.
4. **Container build + scan** (e.g., Trivy) for the api and web images, pushing on
   tagged releases.
5. A migration check that fails if models drift from Alembic revisions.

---

## 6. Observability

- **Structured logging** (JSON) across api, worker, and web with request/trace ids
  and org id (never log PII or secrets).
- **Metrics** (request latency/error rates, Celery queue depth/latency, DB pool
  usage) and **tracing** across the api → worker → external-connector path.
- Alerting on auth failures, MFA anomalies, and worker backlog.

---

## 7. Frontend (apps/web)

- Production build hardening; environment-driven `NEXT_PUBLIC_API_URL`.
- Error boundaries and graceful handling of `ApiError` (`apps/web/lib/api.ts`).
- Accessibility pass (semantic markup, keyboard nav, contrast) on the findings /
  investigation / audit views.

---

## 8. Suggested execution order

1. §2 hygiene (untrack `complygraph.db`).
2. §1 assurance-export (decide gated pillar vs adjacent product; build the export).
3. §3 security hardening (secrets, TLS/headers, CORS, rate limiting, authz tests).
4. §4 production deployment manifest + migrations-on-deploy.
5. §5–§6 CI scanning + observability.
6. §7 frontend hardening; add the `assurance_contract` export test; tag a release.
