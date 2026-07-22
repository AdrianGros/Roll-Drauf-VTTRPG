# Deploy Output

```
artifact: deploy-output
milestone: TRACK-A-LOGIN-UI-REBALANCE-PROOF-PASS-2026-03-30
phase: DEPLOY
status: complete
date: 2026-03-30
```

## Input Summary

This Deploy proof pass worked from:

- `docs/DADM_MONITOR_TRACK_A_LOGIN_UI_REBALANCE_2026-03-30.md`
- `docs/DADM_DEPLOY_TRACK_A_LOGIN_UI_REBALANCE_2026-03-30.md`
- the current Track A login UI files

## Implementation Summary

No additional Track A UI implementation changes were applied in this proof pass.

This pass completed the missing proof capability and used it to capture browser-rendered evidence for the already deployed Track A layout.

## Files Changed

- `docs/DADM_HUMAN_DECISION_TRACK_A_PROOF_CAPABILITY_2026-03-30.md`
- `docs/proofs/track-a-login-desktop.png`
- `docs/proofs/track-a-login-mobile.png`
- `docs/proofs/track-a-login-proof.json`

## Proofs

What was attempted:

1. Browser-proof path discovery
   - checked for local browser binaries on the machine
   - checked for Playwright, Selenium, Node, and npm availability
2. Local render sanity path
   - attempted to boot the app in the repo `venv` with Flask `testing` config and request `/login.html`
3. CSS-level static proof extension
   - confirmed positioning tokens remain in `vtt_app/static/css/book-scene.css`

Observed results:

- the missing Python dependencies required for proof were installed in the active `venv`:
  - `requests`
  - `playwright`
- Playwright Chromium was installed successfully
- the app was started locally on `http://127.0.0.1:5010`
- browser-rendered evidence was captured successfully:
  - `docs/proofs/track-a-login-desktop.png`
  - `docs/proofs/track-a-login-mobile.png`
  - `docs/proofs/track-a-login-proof.json`
- proof JSON confirms:
  - desktop sidecar present
  - desktop form card present
  - desktop signup link below the form card
  - mobile sidecar hidden
  - mobile form card present
  - mobile signup link below the form card
  - login content visible in both viewport classes
- CSS static checks also confirmed:
  - wrapper positioning token present
  - sidecar positioning token present
  - mobile sidecar hide rule present

## Acceptance Checklist

- [x] Browser-rendered proof captured for desktop layout
- [x] Browser-rendered proof captured for mobile layout
- [x] Local render sanity check completed successfully through a live app run on port `5010`
- [x] Static CSS proof extended beyond the previous Monitor pass

## Residual Risks And Next Step

- `low`: The proof pass used a locally provisioned browser capability rather than a pre-existing system browser.
- `low`: Later Track B work must still respect the cleaned Track A boundary in `login.html`.

Next step:

- move to `MONITOR` for Track A closure with the new browser-rendered evidence
