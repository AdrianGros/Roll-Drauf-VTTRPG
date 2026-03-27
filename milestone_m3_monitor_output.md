# M3 Monitor Output: Auth v2 (Cookie + CSRF)

```
artifact: monitor-output
milestone: M3
phase: MONITOR
status: complete
date: 2026-03-26
```

---

## Input Summary

- Scope: M3 Auth hardening follow-up after cookie migration
- Focus: Monitor `register -> login -> /auth/check -> protected routes -> refresh -> logout` and remove header fallback
- Environment: Flask testing config + pytest in local `.venv`

---

## What Was Verified

### 1. Cookie-only auth contract

- `JWT_TOKEN_LOCATION` is now cookies-only (`['cookies']`).
- Login no longer returns raw JWTs in JSON body.
- Refresh no longer returns access token in JSON body.
- Protected endpoints continue to work through cookie session state.

### 2. CSRF behavior for mutating requests

- Added dedicated tests with CSRF protection enabled at runtime.
- Verified POST request without CSRF token is rejected (`401`).
- Verified POST request with `X-CSRF-TOKEN` + CSRF cookie is accepted.

### 3. Regression coverage after migration

- Campaign and character test suites migrated off `Authorization` header usage.
- Auth smoke path remains stable with cookie-based flow.

---

## Test Execution Summary

Command:

```bash
.\.venv\Scripts\python.exe -m pytest -q tests/test_auth.py tests/test_campaigns.py tests/test_characters.py
```

Result:

- Total: 34
- Passed: 34
- Failed: 0
- Skipped: 0

---

## Key Changes Monitored

- [vtt_app/config.py](vtt_app/config.py)
  - `JWT_TOKEN_LOCATION = ['cookies']`
- [vtt_app/auth/routes.py](vtt_app/auth/routes.py)
  - Login/refresh JSON token payloads removed
  - Cookie-based login/refresh/logout contract remains active
- [tests/test_auth.py](tests/test_auth.py)
  - Added CSRF enforcement tests
- [tests/test_campaigns.py](tests/test_campaigns.py)
  - Migrated to authenticated cookie client fixtures
- [tests/test_characters.py](tests/test_characters.py)
  - Migrated to authenticated cookie client fixtures

---

## Observed Non-Blocking Warnings

- SQLAlchemy relationship overlap warnings in campaign relations
- Legacy SQLAlchemy `Query.get()` warnings
- `datetime.utcnow()` deprecation warnings
- Test JWT secret length warning (testing config only)

These are technical debt items and do not block M3 auth behavior.

---

## Monitor Verdict

M3 Auth v2 migration objective is met:

- Cookie + CSRF model is active and tested
- Header-token fallback removed
- End-to-end auth-critical tests are green

Recommended next focus: cleanup sprint for SQLAlchemy warnings + legacy auth module removal (`vtt_app/auth.py`).

