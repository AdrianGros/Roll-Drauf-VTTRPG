# VTT design implementation — slice 1

**Date:** 27 September 2026. **Status:** implemented and verified in the working tree; uncommitted. **Authorization:** the user's “go ahead and continue” after the design/backlog package. **Retention:** repository report plus task-workspace logs, screenshots and source manifest. **Scope:** [design v0.1](authoring-sandbox-design-v0.1.md) shared entry/theme/navigation, responsive layout and guarded navigation. G1's engine baseline is unchanged.

## Result

The current BookScene dashboard offers a contextual “Inhalte erstellen” entry when the server reports authoring available. The flag uses the configured authoring host and usable-account conditions, not a client role or Discord membership. Reading the dashboard does not create a workspace/draft. Existing session/preparation actions retain their priority. The authenticated home response is private/no-store, and direct authoring endpoints retain their existing current-authority checks.

The editor loads the existing fonts, theme, spellbook and book-navigation styles before its scoped feature styles. It uses paper/ink/rubrication tokens, a local item-authoring title and real overview/campaign/character links. No unrelated chapter is marked current. It uses ordinary link navigation into the existing VTT routes without introducing another navigation/animation engine. The three editor locales also localize navigation labels, page title and landmarks.

The page has a single question/preview column below 1200 CSS px and two tool columns above that boundary. Forms, errors, preview and history wrap within the page. A skip link reaches the main content; visible focus uses the shared rubrication token. Saved draft names and versions replace bare version-only identification for the current draft.

Navigation is held while an input is dirty or a command result remains uncertain. The user receives the existing Save/Discard or exact Retry explanation, without discarding input or issuing a replacement command. Normal navigation resumes after resolution. Browser unload protection remains, and no offline persistence or hard-tab-loss replay is promised.

## Changes

| File | Purpose |
| --- | --- |
| [Dashboard endpoint](../../vtt/endpoints/dashboard_home.py) | Add private `home_state.authoring_available` display metadata and no-store response headers. |
| [Transport helpers](../../vtt/creation_engine/transports/common.py) | Determine display availability from the installed host and current account state, excluding View As. No draft reads/provisioning. |
| [BookScene](../../vtt/static/js/book-scene.js) | Render one contextual link after the existing contents list. |
| [Editor template](../../vtt/templates/creation-engine.html) | Shared assets, navigation, local title, skip link and labelled landmarks. |
| [Editor styles](../../vtt/static/css/creation-engine.css) | Scoped shared-theme styles, form/readability states and 1200px layout boundary. |
| [Editor behavior](../../vtt/static/js/creation-engine.js) | Localized orientation, current draft name and dirty/pending navigation guard. |
| [Design integration tests](../../tests/creation_engine/test_ce_design.py) | Twelve cases covering the real home/auth endpoints, rendered dashboard/editor, availability, empty visits, retry/navigation and layout/contrast. |

The dashboard display metadata is not an engine wire command or receipt change. This slice changes no approved schema, domain storage, ruleset, runtime operation, default feature flag or dependency.

## Verification

Tests used a disposable PostgreSQL 16 `ce_test` database on localhost:55439 and installed Chromium. Dashboard/browser tests use the actual auth and home endpoints plus rendered page assets in the isolated application; existing application-level dashboard/book regressions run separately in the selected suite. No production database was used.

| Run/check | Result |
| --- | --- |
| Initial design checks | 11 passed, 7 warnings, 26.10s; exit 0. |
| Final selected regression after adding empty-workspace/contrast coverage and clarifying disabled commit styling | **111 passed**, 20 warnings, 56.91s; exit 0. Includes the final 12 design cases and existing authoring, sandbox browser, dashboard/book, icon and pure-boundary checks. |
| JavaScript syntax and whitespace | Passed for changed scripts and working-tree diff. |
| Active engine specification/core/registry hashes | All unchanged. |
| Full repository regression / human study | Not run for this slice. Historical WP8 results remain separately recorded. |

The selected regression command, with `CE_TEST_DATABASE_URL` and `CE_TEST_ARTIFACT_DIR` pointing to the disposable environment and retained evidence directory:

```text
venv/bin/python -m pytest tests/creation_engine/test_ce_design.py tests/creation_engine/test_ce_authoring_transports.py tests/creation_engine/test_ce_authoring.py tests/creation_engine/test_ce_boundaries.py tests/test_dashboard_social_hub_guild_navigation.py tests/test_core_book_runtime_routes.py tests/test_book_shell_ux_stabilization.py tests/test_book_scene_layout_contract.py tests/test_journey_nav_cta_cleanup.py tests/test_browser_icon_contract.py -q
node --check vtt/static/js/creation-engine.js
node --check vtt/static/js/book-scene.js
git diff --check
```

Measured layout cells were **320, 390, 1199, 1200, 1201 and 1280 CSS px wide at height 960**, each in de/en/fr with reduced motion: 18 cells, correct column boundary, no page horizontal overflow or horizontally clipped visible controls. Guided screenshots also cover 390×844; those are visual evidence, not physical phone testing. Desktop and phone-sized Guided/Structured screenshots were inspected.

Six sampled computed foreground/background text ratios ranged from **5.07:1 to 13.92:1**, covering help, navigation, submit, disabled commit, readiness and textarea. This is bounded contrast evidence, not a complete accessibility audit. Reduced-motion navigation links measured zero transition duration. Real browser zoom, transition-API absence, Firefox, WebKit, screen readers and physical devices remain unverified.

## Acceptance scope and remaining work

- [x] Server-controlled dashboard entry, unchanged primary actions, no draft creation on visit, flag-off removal and direct-access refusal checks.
- [x] Actual dashboard → editor → saved draft → dashboard browser path, including keyboard activation and protected dirty input.
- [x] Unknown-response navigation guard, exact retry and one resulting draft version change.
- [x] Shared material, localized orientation, six-width layout checks and sampled text contrast.
- [x] Existing authoring/sandbox workflows and relevant VTT regressions pass.
- [ ] Complete VD-C01–VD-C16 conformance: this is the first implementation slice, not blanket acceptance of the catalogue.
- [ ] Conflict reconciliation/focus/error-association coverage, distinct same-named-copy labels, in-page revocation races and remaining accessibility/browser matrix.
- [ ] Required human tasks and missing conditional-effect/choice authoring coverage in WP9.

The [backlog](test-backlog-2026-09-29.md) records the exact partial coverage. Human testing remains deferred until **Tuesday, 29 September 2026**, Europe/Berlin, with time and attendance unconfirmed in this workspace. The date does not waive the ≥8-person/four-task gate.

## Evidence, rollback and next step

The task workspace retains `vtt-design-slice1-2026-09-27/`: before snapshots, `design-initial.log/.exit`, `slice-regression.log/.exit`, `verified-source.json`, `layout-measurements.json`, `text-contrast.json`, screenshots and `verification.json`. Prior WP8 proof files were not overwritten. Relative links and the final source manifest were checked after documentation updates.

The task's `ce-design-slice1-postgres-20260927` container is stopped and removed after verification; preexisting test/production containers are preserved. All engine flags remain default-off. No commit, production migration, feature activation or deployment was performed.

A rollback restores this slice's UI/capability changes from its before snapshot; it does not delete or rewrite drafts, revisions, receipts or locks. Next: address the remaining draft-state/focus and copy-identification cases, then extend the technical matrix. Continue preparing WP9 evidence while the scheduled human session remains pending.
