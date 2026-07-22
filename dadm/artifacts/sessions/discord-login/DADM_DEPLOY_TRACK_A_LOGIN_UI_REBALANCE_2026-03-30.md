# Deploy Output

```
artifact: deploy-output
milestone: TRACK-A-LOGIN-UI-REBALANCE-2026-03-30
phase: DEPLOY
status: complete
date: 2026-03-30
```

## Input Summary

This Deploy pass worked from:

- `docs/DADM_SESSION_CONTROL_2026-03-30_VTT.md`
- `docs/DADM_DISCOVER_VTT_SESSION_REENTRY_2026-03-30.md`
- `docs/DADM_APPLY_VTT_SESSION_BOUNDARY_2026-03-30.md`
- existing bounded Track A file set:
  - `vtt_app/templates/login.html`
  - `vtt_app/static/css/book-scene.css`
  - `vtt_app/static/css/components.css`
  - `vtt_app/static/css/theme.css`
  - `vtt_app/static/js/book-scene.js`
  - `vtt_app/static/js/auth.js`

## Implementation Summary

Track A was implemented as a bounded UI-only continuation.

The key Deploy action in this pass was to separate the approved login-layout rebalance from the gated Discord/auth contract work inside `login.html`.

Implemented outcome:

- the left/right book layout remains in place
- branding remains on the left sidecar panel
- the main login form remains on the right card
- the login page no longer carries Discord-button behavior or remember-me coupling in this Track A continuation
- MFA/password login flow remains intact in the template script

## Files Changed

- `vtt_app/templates/login.html`

## Proofs

Targeted verification run in this pass:

1. Confirmed that gated Discord/remember-me UI hooks were removed from `login.html`:
   - `discordLoginBtn`
   - `rememberMe`
   - `discord_error`
   - `book-login-divider`
   - `book-discord-btn`
2. Confirmed that login geometry selectors remain defined in `vtt_app/static/css/book-scene.css`, not in the template.
3. Confirmed that required login form and MFA hooks still exist in `login.html`:
   - `id="loginForm"`
   - `id="mfaGroup"`
   - `id="loginSubmitBtn"`
   - `BookScene.create()`
   - `BookScene.open()`

## Acceptance Checklist

- [x] Branding remains a left-side panel in the login book structure.
- [x] Form remains the right-side card in the login book structure.
- [x] Track A no longer silently bundles Discord-entry behavior from gated Track B.
- [x] Login page structure still contains the expected password/MFA submission hooks.
- [ ] Visual browser validation of the final layout on desktop and mobile

## Residual Risks And Next Step

- `medium`: The shared file `vtt_app/templates/login.html` is still a future join point with Track B, so later Discord work must respect the now-clean Track A boundary.
- `medium`: This pass did not include a browser-rendered visual proof, so the structural result is verified statically rather than visually.
- `low`: Existing uncommitted Track A CSS/JS changes remain part of the broader login rebalance state and should be reviewed together before session closeout.

Next step:

- Move to `MONITOR` for Track A if you want a bounded validation pass, or continue only if you explicitly want another Track A Deploy refinement.
