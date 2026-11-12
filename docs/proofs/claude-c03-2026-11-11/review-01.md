Unabhängiger Claude-Quellreview, keine vom Reviewer ausgeführten Tests. Geschätzte Häufigkeiten sind ungemessene Reviewerannahmen. Umsetzung/Nacharbeit und Live-Status werden separat geführt.

# C03 review: rework_required

I found two Medium issues and a few Low points. Nothing here was run. I read the diff, the Apply contract, and the live code in `auth/routes.py`, `contexts.py` and `socket_handlers.py`. For the `exp`/`iat` question I read the installed flask-jwt-extended `tokens.py`.

## Findings

**M1 – `vtt/auth/lifetime.py` `issue_tokens` / `check_payload`: a second-boundary race can mint an unusable token.**
- **Trigger:** `until` and `remaining` come from `now_ts()`, which is the helper's own integer clock. The flask-jwt-extended library sets `exp = datetime.now() + expires_delta` from the real sub-second clock and PyJWT floors it (`tokens.py:38,64`). If the wall clock crosses a second boundary between `now_ts()` and token creation, the refresh token gets `exp = until + 1`. An access token minted with fewer than 3600 seconds left gets the same.
- **Expected:** `exp <= until`, as the contract says ("nie über das absolute Ende").
- **Actual:** `check_payload` raises `claims_implausible` on `exp > until`. A login whose refresh token lands on `until + 1` works for up to an hour, then every refresh returns 401 and the user must log in again. The odds are roughly the gap between `now_ts()` and the signing calls divided by one second, so about 0.1–0.5% of logins. The near-end access tokens that `/refresh` mints are exposed to the same race.
- **Acceptance impact:** a rare, hard-to-reproduce failure in the six-hour acceptance. The tests assert `refresh["exp"] == until` exactly, so they can also flake.
- **Smallest rework:** pass an explicit `exp` through `additional_claims`. The library applies `claim_overrides` after the defaults (`tokens.py:67`). Alternatively, clamp `exp` to `until` and allow 1–2 seconds of tolerance in the `exp > until` check. Add a test that mocks the real clock one second later than the helper clock.

**M2 – `vtt/auth/routes.py` `change_password` with `_revoke_user_sessions(keep_jti=access jti)`: it now kills the current device's refresh token.**
- **Trigger:** a logged-in user changes their password (`routes.py:732`). Refresh JTIs used to be unregistered. They are now registered in `sessions`, and only the access JTI is kept.
- **Expected:** "Andere Sitzungen wurden beendet" (other sessions ended). The current login stays valid, including its refresh path.
- **Actual:** the current login's refresh row gets `revoked_at`. After the access token's 1-hour exp, `/refresh` returns 401 from the blocklist seam. Table contexts survive only because they are tied to the kept access JTI. This is a regression of an existing live feature caused by registering refresh JTIs.
- **Acceptance impact:** the contract says existing features must stay intact. Nothing in the changed tests covers password change.
- **Smallest rework:** also keep the current refresh JTI. For example, decode the validated `refresh_token_cookie` JTI in that route. Alternatively, keep rows of the same user whose `expires_at` equals the current `vtt_auth_until`. Add a test: log in, change password, expire access, refresh → 200, while a second device is revoked.

**L1 – Legacy-refresh cutoff in `check_payload` is coarse but fails closed.** It treats any revoked row for the user as a logout. That includes other-device or password-change revocations and the `revoked_at >= iat` same-second case. This only affects the one-time migration, and the Apply document documents it. Keep it and mention it in the pre-release notice.

**L2 – `logout` uses `jwt_required(optional=True)` with an expired access cookie (pre-existing).** The expired-token error is not swallowed by `optional=True`, so logout returns 401. No JTIs are revoked and the cookies are not cleared. This is not introduced by C03, but with 6-hour cookie Max-Age it is easier to hit. Track it separately; do not block C03 on it.

**L3 – Legacy table contexts now die with the issuing session row.** For example, a context issued under a legacy access token stops validating at that token's 1-hour row `expires_at`. That is the contract's stated effect. The pre-release notice must say so, because Player and DM users will need to re-enter the table.

## Checked and looks correct
- **Issuing paths:** register, password, Discord and refresh all go through `issue_tokens`. The `started` anchor is server-side only; no client value reaches it.
- **Refresh:** a non-legacy refresh keeps the same anchor and refresh token and mints only a bounded access token. Legacy refresh uses its signed `iat`, never "now".
- **Expiry and revocation:** `until <= now` is refused, and absent or partial claims have no legacy fallback. Registered rows are checked for user match, revocation and an overlong `expires_at`. Cookie Max-Age is bounded by the remaining login time.
- **Same-second re-login:** registered rows decide for new tokens, so a new login in the same second as a logout stays valid.
- **Socket:** a pure `decode_token` now passes through `check_payload`. A revoked token also fails on the delegation path. `allow_expired` waives only the access `exp`, and the sub/context identity match is kept.
- **Contexts and outbound:** there is no DM fallback. The context deadline is `min(8h, until)`, or the access `exp` for legacy tokens. `validate` honours the issuing row's `expires_at`, so outbound pruning also applies to it.

## Verification gaps
- Nothing was run. The 82-passed count is the coordinator's local-SQLite result, and I did not reproduce it.
- No test covers M1 or M2.
- No browser, real-cookie, csrf-cookie Max-Age, multi-worker or live evidence exists. This includes the Player/DM tab reconnect and resync journey, the 59/61-minute transition in a real browser, and a real Discord callback.
- There is no check of other JWT cookie consumers in the frontend, such as refresh scheduling that assumed a 7-day or 30-day refresh cookie.
- No deployment or rollback evidence exists. Rolling back would drop the six-hour policy, which the Apply document already says.

**Verdict: rework_required.** Fix M1 and M2 and add their tests, then re-review. Not a deployment approval.
