# M8 Apply Output: Production Readiness Architecture Design

```
artifact: apply-output
milestone: M8
phase: APPLY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Discover baseline:
  - `milestone_m8_discover_output.md`
- Human approval:
  - `APPROVED: M8 Apply mit Empfehlungen`
- Constraints and method:
  - DAD-M runtime profile `standard`
  - Apply phase only: architecture, rollout contracts, acceptance criteria (no implementation code)
  - Build on M3-M7 application feature baseline

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m8_apply_output.md` | M8 solution design baseline for Deploy | `immutable` after phase close | active draft in this turn |

---

## Recommended Decision Set (for M8 Deploy)

1. **Infrastructure recommendation: containerized app + managed data services (PostgreSQL + Redis)**
   Use containerized Flask-SocketIO app behind TLS reverse proxy; run PostgreSQL and Redis as managed services.

2. **Release recommendation: gated CI with manual production promotion**
   Every merge must pass tests/security gates; production rollout is manual approval with smoke-test and rollback path.

3. **Reliability recommendation: failover-first ops baseline (health checks, metrics, backups, runbooks)**
   Add readiness/liveness + metrics + structured logging + backup/restore + failover drill as mandatory M8 scope.

---

## Design Tradeoffs

| Topic | Option A | Option B | Selected | Reason |
|---|---|---|---|---|
| Runtime packaging | direct `python app.py` | container image per release | **B** | reproducible deploys, easier rollback |
| Data services | self-managed DB/Redis | managed PostgreSQL + managed Redis | **B** | lower ops risk, faster M8 delivery |
| Deploy strategy | auto deploy on merge | CI gate + manual prod approve | **B** | safer release control for first production |
| Recovery model | nightly dump only | PITR + encrypted dumps + restore drill | **B** | aligns with recovery target and auditability |
| Observability | logs-only | logs + metrics + health probes + alerts | **B** | actionable operations and incident response |

---

## Solution Design

### 1) Target Production Architecture

Production runtime topology:

- Reverse proxy (TLS termination, websocket pass-through, security headers)
- `vtt-app` container instances (Flask app + Socket.IO)
- Managed PostgreSQL (primary store)
- Managed Redis (Socket.IO message queue + shared rate-limit storage)
- Object storage bucket for encrypted backup exports

Traffic and state model:

- HTTPS -> reverse proxy -> app containers
- App containers use shared Redis queue for Socket.IO fanout
- App state persists in PostgreSQL only
- No SQLite in production

### 2) Runtime Process Model

- Replace Werkzeug runtime path with production server profile.
- Socket runtime configured for multiprocess-safe fanout via Redis message queue.
- App startup must fail fast if required production env vars are missing.

Production startup contract:

- `FLASK_ENV=production`
- `DEBUG=False`
- `allow_unsafe_werkzeug` disabled

### 3) Configuration and Secret Policy

Mandatory production env vars (no insecure defaults):

- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `DATABASE_URL` (PostgreSQL only)
- `REDIS_URL`
- `RATELIMIT_STORAGE_URL` (Redis)
- `CORS_ORIGINS` (explicit allow-list)
- `SESSION_COOKIE_SECURE=true`
- `JWT_COOKIE_SECURE=true`

Rules:

- production config raises startup error when critical secrets are missing
- `.env.example` remains sample-only; production values stored in secret manager

### 4) Migration and Schema Governance

- Introduce Alembic/Flask-Migrate.
- Remove reliance on runtime `db.create_all()` in production path.
- Schema changes are migration-only and versioned in repo.
- CI validates migration chain (`upgrade` on empty DB + current DB simulation).

### 5) Backup, Restore, and Recovery Design

Backup strategy:

- Continuous managed PostgreSQL PITR enabled
- Daily encrypted logical dump (`pg_dump`) to object storage
- Retention policy:
  - PITR window: 7-14 days
  - logical dumps: 30 days

Recovery strategy:

- documented restore runbook with exact command sequence
- quarterly restore drill (staging clone) with evidence artifact
- failover procedure for DB and app instances

Recovery targets:

- RPO target: <= 5 minutes (via PITR)
- RTO target: <= 5 minutes (via managed failover / warm standby + rehearsed runbook)

### 6) CI/CD and Release Architecture

Pipeline stages:

1. `ci` workflow on PR/push:
   - install deps
   - run test matrix (core + M8 critical suites)
   - run dependency audit (`pip-audit` or equivalent)
2. `build` workflow:
   - build tagged container image
   - push to image registry
3. `deploy` workflow:
   - manual approval gate for production
   - deploy image + run migrations
   - post-deploy smoke checks
   - automatic rollback trigger on failed smoke checks

Release policy:

- no production deploy without green CI
- immutable image tags per release
- one-command rollback to previous image tag

### 7) Observability and Operational Baseline

Mandatory M8 ops endpoints:

- `GET /health/live`
- `GET /health/ready`
- `GET /metrics` (Prometheus format or equivalent)

Telemetry:

- structured JSON logs (request_id, user_id when available, endpoint, status, latency)
- key metrics:
  - HTTP error rate
  - p95 endpoint latency
  - websocket connection count
  - token event processing latency
  - DB and Redis connectivity status

Alerting baseline:

- readiness failure
- elevated 5xx rate
- p95 latency breach (>150ms token event objective)
- DB/Redis unavailable

### 8) Security Hardening Boundary (M8)

- strict secure headers via reverse proxy/app middleware
- TLS-only public ingress
- cookie security flags hardened in production
- explicit CORS allow-list (no broad wildcard in prod)
- remove/disable legacy inactive modules (`vtt_app/api.py`, `vtt_app/sockets.py`) from deploy surface
- dependency vulnerability checks as CI gate

### 9) Data Protection Policy Baseline (M8)

Retention defaults (recommended):

- auth sessions (`sessions`): 30 days post-expiry/revocation
- invite tokens: 30 days after expiry/use
- chat messages: 180 days (unless campaign policy overrides)
- moderation actions/reports: 365+ days for audit trail

Operational requirement:

- documented data export/delete procedure for user data requests

### 10) Verification Strategy (M8 Deploy target)

New validation suites/artifacts:

- infra smoke tests (health/ready/metrics)
- migration smoke test
- backup creation + restore test script
- load test profile for 200 concurrent users and 40 active campaigns
- failover simulation checklist

Regression suites to keep green:

- `tests/test_auth.py`
- `tests/test_campaigns.py`
- `tests/test_characters.py`
- `tests/test_combat_api.py`
- `tests/test_tokens_realtime.py`
- `tests/test_chat_api.py`
- `tests/test_reports_api.py`
- `tests/test_moderation_actions.py`
- `tests/test_community_realtime.py`

---

## Acceptance Criteria (for M8 Deploy)

AC-M8-01: Production runtime uses containerized app instances and does not use Werkzeug unsafe mode.  
AC-M8-02: PostgreSQL and Redis are configured as production backends (`DATABASE_URL`, `REDIS_URL`, `RATELIMIT_STORAGE_URL`).  
AC-M8-03: CI pipeline enforces tests and security checks before deploy promotion.  
AC-M8-04: Deploy pipeline supports migration execution and rollback to last known good release.  
AC-M8-05: Health/readiness/metrics endpoints are implemented and operationally usable.  
AC-M8-06: Structured logging with correlation fields is enabled for production logs.  
AC-M8-07: Backup strategy (PITR + encrypted dump) is operational and documented.  
AC-M8-08: Restore drill succeeds in non-prod and evidence is captured.  
AC-M8-09: Production config fails fast when critical secrets/env vars are missing.  
AC-M8-10: Legacy inactive socket/api modules are removed from production path or explicitly quarantined.  
AC-M8-11: Load/failover validation is executed against M8 targets (200 users / 40 campaigns / latency objective).  
AC-M8-12: Core functional regression suites remain green after M8 deploy changes.

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Recovery target (<5 min) may require managed HA tier decisions beyond base VPS hosting. | `high` | yes |
| R2 | Introducing migration tooling late can surface schema-compatibility edge cases. | `high` | yes |
| R3 | Observability stack expansion can increase deployment complexity if done in one large cut. | `medium` | yes |
| R4 | Redis + multiprocess Socket.IO behavior requires careful config parity across envs. | `medium` | yes |
| R5 | Existing technical-debt warnings (`Query.get`, `utcnow`) remain and may pollute ops signals. | `low` | no |

Assumption A1: M8 accepts managed infrastructure components to meet timeline and reliability goals.

Assumption A2: No new gameplay features are added in M8 deploy scope; focus is operational hardening only.

---

## Planned Deploy Artifacts

- `.github/workflows/ci.yml` (new)
- `.github/workflows/deploy.yml` (new)
- `Dockerfile` (new)
- `docker-compose.prod.yml` (new)
- `ops/nginx/nginx.conf` (new)
- `ops/runbooks/backup_restore.md` (new)
- `ops/runbooks/failover.md` (new)
- `ops/scripts/backup_db.ps1` (new)
- `ops/scripts/restore_db.ps1` (new)
- `ops/load/k6_smoke.js` (new)
- `migrations/` (new migration framework directory)
- `vtt_app/ops/__init__.py` (new)
- `vtt_app/ops/routes.py` (new: `/health/live`, `/health/ready`, `/metrics`)
- `vtt_app/__init__.py` (register ops blueprint, production startup policy adjustments)
- `vtt_app/config.py` (strict production env validation + Redis-backed rate limit config)
- `vtt_app/extensions.py` (Socket.IO message queue + limiter backend wiring)
- `app.py` (production-safe run path update)
- `README.md` / `QUICKSTART.md` (production runbook updates)
- `milestone_m8_deploy_output.md` (new)

---

## Next Step

Start **M8 Deploy** and implement the approved design in one pass:

1. add production runtime packaging and CI/CD workflows,
2. introduce migration framework and startup hardening,
3. add ops endpoints + logging/metrics baseline,
4. implement backup/restore scripts and runbooks,
5. execute deploy validation (smoke, regression, load/failover evidence).
