# M8 Discover Output: Production Readiness Baseline

```
artifact: discover-output
milestone: M8
phase: DISCOVER
status: complete
date: 2026-03-26
```

---

## Input Summary

- Prior milestone baseline:
  - `milestone_m7_deploy_output.md`
  - `milestone_m7_monitor_output.md`
- Runtime method:
  - `dadm-framework/runtime/AI_BIOS.md`
  - `dadm-framework/runtime/file-registry.yaml`
  - profile: `standard`
  - route card: `discover`
- M8 objective from plan:
  - Discover: data protection, backup, policy constraints
  - Apply: CI/CD, deployment, observability architecture
  - Deploy: production infra + SSL + monitoring
  - Monitor: load, failover, and recovery validation

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m8_discover_output.md` | M8 current-state evidence and boundary definition | `immutable` after phase close | active draft in this turn |
| terminal evidence (commands, probes) | support evidence for discovery | `mutable` | not canonical |

---

## Current-State Summary

- Relevant: application is modularized and functionally rich (auth, campaigns, maps/tokens, combat, community moderation).
- Relevant: cookie-based JWT auth + CSRF controls are implemented and tested.
- Relevant: core functional and regression test suites exist and pass.
- Relevant: app still boots with `db.create_all()` in app factory and has no migration framework.
- Relevant: runtime/deployment is local-dev oriented (`python app.py`, Werkzeug run path, no production server profile).
- Relevant: there is no CI/CD pipeline, no container/orchestration artifacts, and no infra-as-code in repo.
- Relevant: no health/readiness/metrics/tracing endpoints or monitoring integration are present.
- Relevant: backup/restore and disaster-recovery automation/docs are absent in project artifacts.
- Relevant: production hardening gaps remain (secret fallback defaults, memory-only rate-limit backend, single-process socket assumptions).
- Not relevant for M8 Discover boundary: feature expansion of gameplay/community behavior (M3-M7 scope already complete).

---

## Inventory

| # | Name | Description | Location | Status |
|---|---|---|---|---|
| I1 | App factory + blueprint modularity | Centralized app creation and module registration | `vtt_app/__init__.py` | present |
| I2 | Env-based config profiles | `development/testing/production` config classes | `vtt_app/config.py` | present |
| I3 | Auth hardening baseline | JWT cookie + CSRF + revocation | `vtt_app/auth/routes.py`, `vtt_app/config.py` | present |
| I4 | API rate limiting | Flask-Limiter attached to key endpoints | `vtt_app/extensions.py`, route modules | present |
| I5 | Realtime room boundaries | Campaign/session room model in active socket handlers | `vtt_app/socket_handlers.py` | present |
| I6 | Automated test suites | Auth/campaign/character/map/combat/community coverage | `tests/*` | present |
| I7 | CI pipeline | Automated test/lint/deploy workflow | `.github/workflows/*` | missing |
| I8 | Containerization assets | Dockerfile/compose runtime packaging | repo root | missing |
| I9 | Production process manager | gunicorn/uwsgi/waitress/supervisor config | repo + `requirements.txt` | missing |
| I10 | Reverse proxy + TLS config | Nginx/Caddy/SSL termination config | repo | missing |
| I11 | Health/readiness endpoints | Liveness/readiness probes for infra | API routes | missing |
| I12 | Observability stack | Metrics/tracing/log forwarding integrations | repo + dependencies | missing |
| I13 | Structured logging policy | Central logger config, correlation IDs, log levels | app modules | missing |
| I14 | DB migration workflow | Alembic/Flask-Migrate migration governance | repo + dependencies | missing |
| I15 | Backup/restore automation | Scheduled DB backups, restore scripts, verification | repo/docs | missing |
| I16 | DR/failover runbooks | RTO/RPO procedures and failover playbooks | repo/docs | missing |
| I17 | Load/performance harness | k6/Locust/benchmark suite for 200-user target | repo/dependencies | missing |
| I18 | Secret hard-fail policy | startup fail when prod secrets missing | `vtt_app/config.py`, `app.py` | missing |
| I19 | Horizontal socket backend | Redis message queue / multiprocess Socket.IO scaling | config/dependencies | missing |
| I20 | Legacy inactive modules | old API/socket code with insecure patterns not wired | `vtt_app/api.py`, `vtt_app/sockets.py` | present (not integrated) |

---

## Dependencies

| # | Dependency | Version | Status |
|---|---|---|---|
| D1 | Flask | 2.3.3 | present |
| D2 | Flask-SocketIO | 5.3.6 | present |
| D3 | Flask-SQLAlchemy | 3.0.5 | present |
| D4 | Flask-JWT-Extended | 4.5.2 | present |
| D5 | Flask-Limiter | 3.5.0 | present |
| D6 | psycopg2-binary | 2.9.9 | present |
| D7 | pytest + pytest-flask | 7.4.3 / 1.3.0 | present |
| D8 | Migration toolchain (Alembic/Flask-Migrate) | not configured | missing |
| D9 | Production app server (gunicorn/uwsgi/waitress) | not configured | missing |
| D10 | Monitoring/telemetry dependencies | not configured | missing |
| D11 | Redis/socket scaling backend | not configured | missing |

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | No CI/CD pipeline means no enforced quality gate before production deployment. | `high` | yes |
| R2 | No migration framework with runtime `db.create_all()` raises schema drift and rollout risk. | `high` | yes |
| R3 | No backup/restore automation blocks recovery target validation (`< 5 min`). | `high` | yes |
| R4 | No health/readiness/metrics/tracing prevents reliable ops monitoring and alerting. | `high` | yes |
| R5 | `app.py` uses Werkzeug with `allow_unsafe_werkzeug=True` and env-driven debug/run behavior unsuitable for production. | `high` | yes |
| R6 | Secret fallbacks in config (`JWT_SECRET_KEY` defaults) allow insecure startup if env is misconfigured. | `high` | yes |
| R7 | Rate-limit storage `memory://` is weak for multi-process or restart resilience. | `medium` | yes |
| R8 | No horizontal Socket.IO backend limits real concurrency headroom toward target scale. | `medium` | yes |
| R9 | Legacy inactive modules with global broadcast patterns may be accidentally reused. | `medium` | no |
| R10 | Existing technical-debt warnings (`Query.get()`, `datetime.utcnow()`) increase operational noise and maintenance risk. | `low` | no |

Assumption A1: M8 must prioritize operational reliability and recoverability over additional feature scope.

Assumption A2: Production target remains 200 concurrent accounts / 40 active campaigns with token event latency under 150ms.

---

## Open Questions

| # | Question | Priority | Owner |
|---|---|---|---|
| Q1 | What is the target hosting topology for M8 (single VM, managed container, Kubernetes)? | blocking | human |
| Q2 | Is PostgreSQL mandatory for M8 production acceptance, or is SQLite fallback allowed temporarily? | blocking | human |
| Q3 | What are required RPO/RTO values and backup cadence to satisfy project recovery target? | blocking | human |
| Q4 | Where is TLS terminated and how are certificates provisioned/rotated? | blocking | human + ops |
| Q5 | Which SLO/SLI set is mandatory at launch (availability, p95 latency, socket event latency)? | important | human + ops |
| Q6 | What release strategy is required (manual deploy, blue/green, canary, rollback policy)? | important | human + ops |
| Q7 | Which data protection requirements apply (retention windows, deletion/export rights, audit retention)? | blocking | human |
| Q8 | Should legacy inactive modules be removed in M8 deploy scope or deferred to a cleanup track? | important | human + backend |

---

## Next Step

Proceed to **M8 Apply** to design:

1. production deployment topology + runtime process model,
2. migration/backup/restore and recovery architecture,
3. CI/CD and release gating workflow,
4. observability and alerting baseline (logs/metrics/traces/health),
5. security hardening controls (secrets, TLS, runtime defaults, legacy cleanup boundary).
