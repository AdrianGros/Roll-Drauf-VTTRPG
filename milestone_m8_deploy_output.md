# M8 Deploy Output: Production Readiness Baseline

```
artifact: deploy-output
milestone: M8
phase: DEPLOY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Approved design baseline:
  - `milestone_m8_apply_output.md`
- Human approval:
  - `APPROVED: M8 Deploy`
- Deployment scope:
  - production runtime hardening (config + startup policy)
  - migration framework wiring
  - ops endpoints and basic metrics/logging
  - CI/CD baseline workflows
  - container/proxy production artifacts
  - backup/restore/failover runbooks and scripts
  - deploy validation against full regression suite

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m8_deploy_output.md` | M8 deployment execution + proof record | `immutable` after phase close | active draft in this turn |

---

## Implementation Summary

Implemented the M8 production-readiness baseline end-to-end:

- App/runtime hardening:
  - added production config validation (required env vars, unsafe defaults blocked, SQLite blocked in production)
  - made schema auto-create configurable and disabled by default for production
  - blocked direct `python app.py` production startup path
  - added JSON logging baseline and ops metric counters
- Migration/readiness foundation:
  - wired `Flask-Migrate` into app extensions and app factory
  - added `migrations/README.md` workflow guidance
- Ops and observability surface:
  - new ops blueprint with:
    - `GET /health/live`
    - `GET /health/ready` (DB + optional Redis checks)
    - `GET /metrics` (Prometheus-style text)
- Production deployment artifacts:
  - added `Dockerfile`, `docker-compose.prod.yml`, `gunicorn.conf.py`, nginx reverse-proxy config
  - added CI workflow (tests + dependency audit) and deploy workflow scaffold
- Recovery operations baseline:
  - added backup/restore/failover runbooks
  - added PowerShell scripts for migrate, backup, restore
  - added k6 smoke/load baseline script
- Legacy surface reduction:
  - quarantined legacy `vtt_app/api.py` and `vtt_app/sockets.py` from production import path

---

## Files Changed

- `vtt_app/extensions.py`
- `vtt_app/config.py`
- `vtt_app/__init__.py`
- `vtt_app/ops/__init__.py` (new)
- `vtt_app/ops/routes.py` (new)
- `vtt_app/api.py`
- `vtt_app/sockets.py`
- `app.py`
- `.github/workflows/ci.yml` (new)
- `.github/workflows/deploy.yml` (new)
- `Dockerfile` (new)
- `docker-compose.prod.yml` (new)
- `gunicorn.conf.py` (new)
- `ops/nginx/nginx.conf` (new)
- `ops/runbooks/backup_restore.md` (new)
- `ops/runbooks/failover.md` (new)
- `ops/scripts/migrate_db.ps1` (new)
- `ops/scripts/backup_db.ps1` (new)
- `ops/scripts/restore_db.ps1` (new)
- `ops/load/k6_smoke.js` (new)
- `migrations/README.md` (new)
- `tests/test_ops_endpoints.py` (new)
- `.env.example`
- `README.md`
- `QUICKSTART.md`
- `requirements.txt`
- `milestone_m8_deploy_output.md` (new)

---

## Proofs

Executed command:

`.\.venv\Scripts\python -m pytest -q`

Result:

- `91 passed`
- warnings only (legacy technical-debt warnings already known: `datetime.utcnow()`, `Query.get()`, mapper/drop-order warnings in SQLite tests)

Executed command:

`.\.venv\Scripts\python -m pytest tests/test_ops_endpoints.py tests/test_auth.py tests/test_campaigns.py tests/test_tokens_realtime.py tests/test_chat_api.py -q`

Result:

- `44 passed`

---

## Acceptance Checklist

- [x] AC-M8-01: Production runtime uses containerized app instances and does not use Werkzeug unsafe mode.
- [x] AC-M8-02: PostgreSQL and Redis are configured as production backends (`DATABASE_URL`, `REDIS_URL`, `RATELIMIT_STORAGE_URL`).
- [x] AC-M8-03: CI pipeline enforces tests and security checks before deploy promotion.
- [ ] AC-M8-04: Deploy pipeline supports migration execution and rollback to last known good release.
- [x] AC-M8-05: Health/readiness/metrics endpoints are implemented and operationally usable.
- [ ] AC-M8-06: Structured logging with full correlation fields (request_id/user_id) is enabled.
- [ ] AC-M8-07: Backup strategy (PITR + encrypted dump) is operational and documented.
- [ ] AC-M8-08: Restore drill succeeds in non-prod and evidence is captured.
- [x] AC-M8-09: Production config fails fast when critical secrets/env vars are missing.
- [x] AC-M8-10: Legacy inactive socket/api modules are quarantined from production path.
- [ ] AC-M8-11: Load/failover validation executed against M8 targets (200 users / 40 campaigns / latency objective).
- [x] AC-M8-12: Core functional regression suites remain green after M8 deploy changes.

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Deploy workflow is still scaffold-level; migration + rollback automation needs environment-specific implementation. | `high` | yes |
| R2 | Recovery controls are documented but not yet proven by recorded restore/failover drills. | `high` | yes |
| R3 | M8 load validation against full target concurrency is not yet executed with evidence. | `high` | yes |
| R4 | Structured logs are present, but correlation enrichment is not complete. | `medium` | no |
| R5 | Existing repository-wide datetime/SQLAlchemy legacy warnings remain and increase ops noise. | `low` | no |

Assumption A1: Outstanding ACs move to M8 Monitor execution scope (validation + operational proof).

---

## Next Step

Proceed to **M8 Monitor**:

1. execute restore drill in non-prod and store evidence artifact,
2. run load/failover validation against M8 scale targets,
3. finalize deploy automation (migrations + rollback) and correlation logging fields,
4. close remaining AC-M8-04/06/07/08/11.
