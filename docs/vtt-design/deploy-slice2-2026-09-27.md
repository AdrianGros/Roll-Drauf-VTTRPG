# VTT design implementation — slice 2

**Date:** 27 September 2026. **Authorization:** the user's “Ok go” following slice 1's proposed conflict/focus/copy-identity work. **Phase:** bounded G1 Deploy under [design v0.1](authoring-sandbox-design-v0.1.md). Working-tree implementation; uncommitted. Engine authority remains specification 1.1.4, wire 1.1.3 and registry A1.

## Result and implementation boundary

A rejected draft-version save now opens an explicit recovery panel. It preserves the local control values, including JSON formatting, and blocks ordinary edits/navigation until resolution. Loading the current draft is read-only. The author compares retained input with the saved version, then explicitly restores a compatible answer into an editable form and saves again. That save receives a new key and the reviewed version; another concurrent change returns to recovery. Guided recovery opens Structured view so an already-answered question remains reachable; Advanced recovery retains JSON view.

An unavailable, unready or differently versioned question cannot receive the retained answer automatically. The input remains available to inspect/copy. Preset/revision/revert conflicts require reviewing the current draft and choosing the action again. Discarding before refresh first loads the current draft; a failed refresh retains the recovery state. Draft/history reads complete before replacing the editor's draft. The existing uncertain-response path still retains and retries the identical command. The page explicitly states that unsaved input lasts only in the open tab.

Focus is applied after controls are enabled. Saves reach the next applicable question or completion heading; modes/locales retain focus; preset previews focus their Apply button. Invalid native input, malformed JSON and server-rejected typed answers retain input and expose an associated field error. Discard returns focus to the relevant field. A sandbox hit focuses its available decision, and completed sandbox actions reach the sandbox status.

Item, holder and target selectors use the same copy reference as the resource list. It derives from the authorized immutable instance ID, precedes the name so a narrow selector exposes the distinction, and remains independent of resource values. References normally show the last 12 ID characters; colliding abbreviations expand to the full IDs. That exceptional expansion can change the displayed reference length when another colliding copy appears. Command values remain the complete IDs; no instance order, local counter, inferred holder or new revision lock is introduced.

Implementation changes are limited to [editor JavaScript](../../vtt/static/js/creation-engine.js), [template](../../vtt/templates/creation-engine.html), [scoped styles](../../vtt/static/css/creation-engine.css) and [browser cases](../../tests/creation_engine/test_ce_editor_states.py). Small helpers separate focus, field errors and conflict recovery from transport commands. No server model, wire command, schema, migration, policy or engine behavior changed.

## Verification

The dedicated browser run passed **11 cases, 7 warnings in 55.57s, exit 0**. The final selected regression passed **96 tests, 24 warnings in 168.58s, exit 0**, including the final wording adjustment and all 11 new browser cases. The warnings concern existing ORM relationships/table cycles, UTC deprecations and Eventlet. This is not a full repository run. Tests use a disposable PostgreSQL 16 container, real authenticated Flask/engine endpoints and headless Chromium 151.0.7922.34 through Playwright 1.62.0; Python 3.14.7. They are automated engineering evidence, not participant testing.

Final regression command, with `CE_TEST_DATABASE_URL` pointing to the isolated database on localhost:55440 and `CE_TEST_ARTIFACT_DIR` pointing to the slice's retained evidence directory:

```text
venv/bin/python -m pytest tests/creation_engine/test_ce_editor_states.py tests/creation_engine/test_ce_design.py tests/creation_engine/test_ce_authoring_transports.py tests/creation_engine/test_ce_authoring.py tests/creation_engine/test_ce_native.py tests/test_dashboard_social_hub_guild_navigation.py tests/test_core_book_runtime_routes.py tests/test_book_shell_ux_stabilization.py tests/test_book_scene_layout_contract.py tests/test_journey_nav_cta_cleanup.py tests/test_browser_icon_contract.py -q
node --check vtt/static/js/creation-engine.js
git diff --check
venv/bin/python docs/creation-engine/v1.2/verify_reconciliation.py
```

The new scenarios cover:

- Real competing tabs in de/en/fr: exact retained input, safe text rendering, read-only refresh and explicit new-key save against the reviewed version.
- Failed conflict refresh, a second intervening save, Guided-to-Structured recovery and a damage question hidden by a changed behavior.
- Conflicting preset discard both before and after refresh, without applying the rejected preset.
- Native/JSON/server validation, error associations, discard, mode/locale/preset/next-question/completion focus, and a Tab/Shift+Tab/Enter/arrow-key entry-to-save sequence.
- Two identically named copies with independent charges, stable labels through refresh/reload, retained selection, and recovery of the chosen copy.
- Same-named imported actors, keyboard flame-decision decline and return of focus without spending charges or drawing damage.

Development logs are preserved: the initial run had 5 passes/3 failures from early keyboard activation and an incorrect completion assumption; the next had 7 passes/2 failures from the test's Structured-view order assumption and a label-format edit made while a browser reload test was running. These were development runs, not fixed-build acceptance. The final regression uses recorded source hashes checked again after completion. Historical WP8 and slice 1 results remain unchanged.

## Acceptance and remaining work

- [x] Conflict recovery retains input, requires explicit reconciliation and never automatically reapplies a rejected command.
- [x] The tested edit/validation/view/preset/completion/decision paths have intentional focus and associated errors.
- [x] Same-named sandbox copies are distinguishable and the tested selected copy alone spends/replenishes its resources.
- [ ] Full VD-C01–VD-C16 acceptance, in-page revocation/delayed-response races, hard-tab-loss behavior and the remaining browser/accessibility matrix.
- [ ] An uninterrupted keyboard traversal of every control/state, actual browser zoom, Firefox/WebKit, screen-reader and physical-device evidence.
- [ ] Tuesday's human results and unresolved T45 conditional-effect/choice authoring coverage.

The [backlog](test-backlog-2026-09-29.md) tracks partial evidence without closing broader contracts. Human testing remains deferred until **Tuesday, 29 September 2026**, Europe/Berlin. Time and attendance remain unconfirmed here; the ≥8-user/four-task acceptance requirement is unchanged.

## Evidence and rollback

Task-workspace directory `vtt-design-slice2-2026-09-27/` retains before snapshots, development/final logs with exit codes, source hashes, environment details, screenshots, layout/contrast measurements and the verification manifest. Conflict screenshots cover de/en/fr at 390×844; copy evidence also uses 390×844. The rerun layout test covers 18 cells (six widths × de/en/fr, height 960 with reduced motion), with no horizontal overflow or clipped controls. Six sampled text contrast ratios remain 5.07:1–13.92:1. Conflict and same-named-copy phone screenshots were inspected. This does not establish physical-device or browser-zoom acceptance. JavaScript syntax, whitespace, local documentation links, unchanged source hashes and the authority/reconciliation verifier pass.

Rollback restores only this slice's three UI files from its before snapshots and removes its new test/report as appropriate. It does not change drafts, revisions, receipts or locks. Existing uncommitted WP5–WP8 and slice 1 work is preserved. The task container `ce-design-slice2-postgres-20260927` was stopped and removed after verification; preexisting containers were preserved. No commit, production deployment, migration or feature activation is part of this slice; flags remain default-off.

Next bounded work is the open-page authorization/revocation behavior and remaining technical accessibility/browser coverage, followed by the scheduled WP9 observations. G1 remains open.
