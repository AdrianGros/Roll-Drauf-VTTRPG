Read-only independent Claude review; executed verification is recorded separately.

# C03 re-review: delta ec57273 → 166234b

**Verdict: ready_for_integration.** I found no Medium-or-higher regression in the M1/M2 delta or the cookie-path change. Nothing was run, and the expanded unit/browser/table/Discord suite is still pending on your side, so this is not a pass claim.

## What I checked
- **M1 – `issue_tokens`:**
  - The `exp` overrides are applied after the defaults in the installed flask-jwt-extended (`tokens.py:63–67`). `expires_delta=False` skips the library's own `now + delta` exp, so the override wins.
  - Refresh `exp = until` and access `exp = min(now + ttl, until)`, both from the integer anchor. The second-boundary overrun I raised before is closed.
- **M2 – `_current_refresh_jti_to_keep`:**
  - Only a concrete refresh JTI is spared, never an equal-`expires_at` group.
  - The refresh cookie must pass signature, expiry, type, user match, `check_payload` and revocation, and carry the same `(started, until)` as the access token.
  - A missing, garbage, foreign, wrong-anchor, access-typed or revoked cookie gets no exception.
  - The legacy branch requires both tokens to be legacy and their `iat` to be within 2 seconds. It registers the refresh row with `expires_at = original iat + 6h`, so there is no new anchor and the legacy logout cutoff no longer hits the current device.
  - The kept access JTI, and the contexts bound to it, are untouched. Reset and logout still call `_revoke_user_sessions` without keeps.
- **Cookie paths:**
  - `auth.js` reads `csrf_refresh_token` through `document.cookie` (`auth.js:90`). Without Path `/` for the CSRF cookie, a normal page could not refresh under CSRF protection.
  - The refresh JWT stays HttpOnly at `/api/auth`, so it now reaches `/api/auth/password/change`.
  - `expire_legacy_refresh_cookies` deletes both old `/api/auth/refresh` cookies using the configured name, domain, Secure and SameSite. This runs on login, register, Discord, legacy refresh migration and logout. The new-style refresh response deliberately sets and deletes nothing.

## Low findings (non-blocking)
- **L-a – `issue_tokens` / `_jti`:** a refresh in the final second of the window can return 500 instead of 401. Trigger: the request starts when `until - now_ts() == 1` and signing finishes after `until` has passed. `decode_token(token)["jti"]` in `_jti` then raises `ExpiredSignatureError`, which is not an `AuthLifetimeError`. Cheap fix: read the JTI from the created payload, or catch the expiry and return 401.
- **L-b – legacy keeper pairing:** a legacy device whose access token was minted by the old `/refresh` has `iat` more than 2 seconds away from its refresh token. It is not spared and re-logs in after its access expires. Only logins from before deploy within the legacy hour are affected, which matches the documented transition.
- **L-c – legacy cookie not presented:** a pre-C03 legacy refresh cookie sits on `/api/auth/refresh` and is not sent to `password/change`. That device is not spared. This is also the documented transition.
- **L-d – `refresh_token_cookie` is hard-coded in the keeper.** `lifetime.py` uses the configured cookie name. They are equal today.
- **L-e – concurrency:** two simultaneous password-change requests registering the same legacy JTI could hit the unique constraint, giving a 500 before any commit. Very narrow.
- **L-f – refresh CSRF cookie at `/`:** script on any page can now read it and trigger `/api/auth/refresh`. The refresh JWT stays HttpOnly and an XSS attacker already holds the access token for up to an hour, so this is a negligible increase.
- **L-g – earlier access JTIs of the same login:** table contexts issued under them die on password change. This matches the pre-C03 behaviour, so it is not a regression. Only the current JTI is guaranteed.
- **Pre-existing L2:** logout with an expired access cookie. It is tracked separately and not expanded here.

## Remaining verification gaps
- No pass results exist for the expanded suite: unit, Firefox and Chromium browser tests, table, Discord, and the earlier M1/M2 tests.
- No test covers a real wall-clock second boundary during signing. The test only shifts the helper clock back by 1 second, which is adequate for the claim bound.
- No production-style check of `Secure` and `SameSite` cookie deletion, behind HTTPS and with a proxy path, with a real domain.
- No live check of the migration. That means existing legacy browsers upgrading to the new cookies, any other client that sends refresh through a different path or proxy rule, and the real Discord callback.
- No evidence yet for rollback behavior of the new cookie paths with the previous image. I did not trace what the old image does with `/api/auth`-scoped refresh cookies; check this before release.
- No deployment or live delivery has occurred.
