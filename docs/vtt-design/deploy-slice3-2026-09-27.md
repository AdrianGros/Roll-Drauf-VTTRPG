# VTT design implementation — slice 3

**Date:** 27 September 2026. **Authorization:** the user's “Continue” after slice 2's permission-revocation/accessibility handoff. **Scope:** VD-C11, related VD-C12/C13/C15 behaviors, and VD-T12/T13. **Phase:** G1 Deploy; implementation in the working tree, uncommitted. The engine remains on specification 1.1.4 / wire 1.1.3 / registry A1.

## Result

The open editor now treats a confirmed 401/403/unavailable response or changed workspace identity as access loss. One handler removes protected draft, history, preset, conflict, receipt, revision and sandbox content from the DOM and releases the corresponding client state. It disables mutations, focuses an unavailable message and offers sign-in and an explicit read-only access recheck. Unknown/inaccessible responses use the same public wording. An outstanding request may already have committed; the message directs the author to inspect saved state before repeating it. Recovery loads fresh authorized state and never replays an old command.

Every request records the current client access generation. Access loss invalidates that generation and aborts outstanding requests; late responses are rejected even when transport cancellation cannot prevent their eventual resolution. Sandbox and catalog reads also carry sequence numbers, so an older projection cannot replace a newer authorized one. Closing or changing the selected sandbox clears its previous detail projection rather than retaining hidden rows or input.

The page checks the existing workspace, optional native catalog and selected sandbox endpoints on window focus/visible-tab return and every **15 seconds while visible**. Probe requests have a **10-second timeout per request**, and only one probe runs at a time. Checks update runtime availability, revision choices, instance/target selectors and decisions; still-authorized selections are preserved. Unchanged background projections do not rebuild controls. If a focused decision disappears, focus returns to the sandbox status. A restored browser-cache page requires fresh access verification.

A failed connection check is distinct from a denial: editing pauses, but dirty input and the exact pending command remain available in the open tab. Successful read-only verification resumes the relevant field or Retry action. Local discard remains available when no command outcome is unknown. The sign-in link follows the same unsaved/pending navigation guard as other in-app links.

This uses existing server authorization and projected reads. It adds no server endpoint, policy rule, schema, migration, dependency, token refresh or engine operation. Rechecks use existing GET semantics, including the server’s existing private-workspace provisioning behavior; they send no authoring/runtime command. It does not promise instantaneous push revocation: reaction depends on a completed request, periodic check or lifecycle signal, and hidden/offline tabs have browser scheduling/network limits. A connection failure alone does not prove that permission was revoked.

## Files and verification

- [Editor JavaScript](../../vtt/static/js/creation-engine.js): access-loss cleanup, request generation/sequence checks, read-only revalidation, projection cleanup and focus.
- [Editor template](../../vtt/templates/creation-engine.html): localized unavailable/paused-access recovery surface and guarded sign-in link.
- [Access-state browser tests](../../tests/creation_engine/test_ce_access_states.py): real authenticated endpoints, database-backed account/policy changes, delayed responses and keyboard recovery.
- Design/engine indexes, technical backlog and G1 program evidence are updated without rewriting earlier reports or the active contracts.

The first access run passed **12 tests, 7 warnings in 50.71s, exit 0**. A wider development run recorded **29 passes / 2 failures**: the tests attempted pointer activation of an intentionally `aria-disabled` navigation link and started another probe before the current one had finished. The tests were corrected to exercise keyboard guarding and wait for probe completion. The next development run had **31 passes / 1 failure**: its new deselection test changed the select programmatically without first moving keyboard focus there. It now uses the native Home key on the focused select. These are test-harness corrections; development logs remain separate from fixed-source acceptance. The final fixed-source selected regression passed **139 tests, 126 warnings in 236.94s, exit 0**, including all **14 new access-state cases**. The warnings concern existing ORM relationships/table cycles and UTC deprecations. This is selected regression coverage, not a full repository run.

Checks use the disposable `ce-design-slice3-postgres-20260927` PostgreSQL 16 container on localhost:55440 and headless Chromium **151.0.7922.34** / Playwright **1.62.0**, Python **3.14.7**. No live account, production database or human participant is used. The delayed-response fixtures hold responses after native fetch resolves, proving that cancellation alone is not the only protection.

Final selected regression command, with `CE_TEST_DATABASE_URL` and `CE_TEST_ARTIFACT_DIR` pointing to the isolated database and retained slice directory:

```text
venv/bin/python -m pytest tests/creation_engine/test_ce_access_states.py tests/creation_engine/test_ce_editor_states.py tests/creation_engine/test_ce_design.py tests/creation_engine/test_ce_authoring_transports.py tests/creation_engine/test_ce_authoring.py tests/creation_engine/test_ce_native.py tests/creation_engine/test_ce_public.py tests/creation_engine/test_ce_transports.py tests/test_browser_icon_contract.py -q
node --check vtt/static/js/creation-engine.js
git diff --check
venv/bin/python docs/creation-engine/v1.2/verify_reconciliation.py
```

Acceptance evidence covers confirmed suspension/sign-out/authoring-flag/View As denial in de/en/fr; periodic detection; fresh recovery after identity change; delayed preset/save responses; independent object/decision revocation; capability/catalog changes; deselected-scope cleanup; network-pause retention and identical-command retry. Screenshots cover unavailable states at 390×844; English and French captures were inspected. The existing layout checks also reran at 18 width/locale cells (six widths × de/en/fr, height 960, reduced motion), with no horizontal overflow/clipped controls, and six text contrast samples remained 5.07:1–13.92:1. JavaScript syntax, whitespace, documentation links and source/authority/reconciliation checks pass. These are bounded technical assertions, not a complete accessibility or browser matrix.

## Limits, evidence and next step

- [x] Confirmed denial removes the tested protected surfaces and disables mutations.
- [x] Old responses cannot restore a prior access generation or supersede a newer sandbox projection.
- [x] Rechecking access is read-only; transient failure retains input and the original pending envelope.
- [x] The tested recovery/removal paths have intentional keyboard focus and preserve navigation guards.
- [ ] Complete browser-cache restoration/tab-loss lifecycle tests, uninterrupted keyboard traversal and assistive-technology announcement checks.
- [ ] Actual browser zoom, Firefox/WebKit, physical devices and the remaining suspended/timeout/receipt-state UI matrix.
- [ ] Tuesday's human observations and unresolved T45 task-capability coverage.

Before snapshots, the implementation boundary, development/final logs and exit codes, source hashes, screenshots and the verification manifest are retained in task-workspace `vtt-design-slice3-2026-09-27/`. Rollback restores this slice's two UI files from their before snapshots and removes its new test/report as appropriate; persisted drafts, receipts, revisions and execution locks are unaffected. Earlier uncommitted WP5–WP8 and design-slice work is preserved. The task database container is stopped and removed after verification; preexisting containers are preserved.

Human testing stays deferred until **Tuesday, 29 September 2026**, Europe/Berlin; time/attendance and the ≥8-user/four-task gate remain open. Next: complete the remaining technical browser/accessibility and failure-state evidence before interpreting the scheduled session as WP9 acceptance. Changes remain uncommitted; production flags stay default-off and no deployment, migration or activation occurred.
