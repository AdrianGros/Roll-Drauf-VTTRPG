# Deploy Output

```
artifact: deploy-output
milestone: TRACK-B-DISCORD-LOGIN-BOT-SSOT-2026-03-30
phase: DEPLOY
status: complete
date: 2026-03-30
```

## Input Summary

This Deploy pass worked from:

- `docs/DADM_APPLY_TRACK_B_DISCORD_LOGIN_BOT_SSOT_2026-03-30.md`
- `docs/DADM_MONITOR_TRACK_A_CLOSURE_2026-03-30.md`
- the current Track B file state in:
  - `vtt_app/auth/routes.py`
  - `vtt_app/templates/login.html`

## Implementation Summary

Track B was deployed as a bounded repo-local continuation without reopening Track A layout scope.

Implemented outcome:

- the login page now has a minimal Discord re-entry section again
- the Discord CTA is hidden unless the backend reports Discord login as ready
- callback-driven `discord_error` messages are surfaced again on the login page in a bounded Discord-specific area
- the Discord start route now fails with a user-facing redirect instead of an unhandled configuration error
- the Discord status route now reports readiness rather than only the raw feature flag

## Files Changed

- `vtt_app/auth/routes.py`
- `vtt_app/templates/login.html`

## Proofs

Targeted verification completed in this Deploy pass:

1. Python syntax validation
   - `venv/bin/python -m py_compile vtt_app/auth/routes.py vtt_app/auth/discord_oauth.py`
2. Static Track B join-point validation in `login.html`
   - confirmed new bounded hooks exist:
     - `discordAuthSection`
     - `discordLoginBtn`
     - `discordError`
   - confirmed removed Track A coupling still stays absent:
     - `rememberMe`
3. Local app sanity run
   - app booted successfully on `http://127.0.0.1:5011`
   - `GET /api/auth/discord/status` returned `{"enabled":false}` in the default local state
   - `GET /login.html` returned `200`
4. Browser-level disabled-state sanity check
   - after page load and animation delay:
     - `#login-content.visible` became active
     - `discordAuthSection.hidden === true` in the default disabled state
     - `generalError` empty
     - `discordError` empty

## Acceptance Checklist

- [x] Track B reintroduced only a minimal Discord CTA surface in the login page
- [x] Track A layout closure was not intentionally reopened
- [x] Discord error presentation exists again for callback redirects
- [x] Discord readiness is gated by backend readiness, not only by front-end presence
- [x] Local sanity run completed for status endpoint and login page render

## Residual Risks And Next Step

- `high`: The real bot verification endpoint was not exercised in this Deploy pass.
- `high`: Positive and denied Discord callback paths are still not covered by dedicated session tests here.
- `medium`: `login.html` remains the shared join point between Track A and Track B.
- `medium`: No production rollout proof exists yet for the `discord_identity_links` schema path.
- `low`: The local sanity run emitted pre-existing SQLAlchemy relationship warnings unrelated to the Track B delta.

Next step:

- move to `MONITOR` for Track B to decide whether the bounded Deploy pass is internally sound and what remains open before any production-style enablement
