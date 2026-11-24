# DAD-M Discover — FV18 interaction timing (2026-11-24)

Phase: Discover. Task: FV18 interaction timing. Profile: standard.
Author: Claude (independent handoff `docs/CLAUDE_HANDOFF_FV18_TIMING_2026-11-24.md`).
Worktree `/home/admin/projects/roll-drauf-vtt-fv15-quota-20261124`, source `96f2f510a`.

Read-only source inspection only. No commands, tests, browsers, git, network, live,
catalog or credential access were used. No nested agents. Nothing below is reproduced;
every timing statement is either a direct source fact (with file:line) or explicitly
labelled hypothesis. This file is the only write.

## 1. Input summary

Codex supplied three observations (O1–O3, quoted in the handoff, not re-verified here):

- **O1** Live Firefox Player creator (EN site / DE rules): after rapid species/native-select
  actions, a "species text" button click returned but no modal opened and the old (closed)
  class dialog title remained. Another attempt: Dragonborn card focused while Goliath stayed
  selected and its ancestry control was absent. A journey waiting for `!dirty && !saving`
  before every species action and asserting `aria-pressed` passed.
- **O2** Quota browser "initial 500 panel failure" case never reached its mocked route: the
  dashboard profile button detached during nav composition; an 8 s click deadline expired.
  Unchanged isolated retry passed (56.94 s). Not a quota-panel behaviour failure.
- **O3** Creator DE-site / EN-rules home entry exceeded an existing 5 s assertion once; passed
  unchanged on retry.

## 2. Current-state summary

Two independent DOM-replacement mechanisms exist in source that can replace the node a
user or test is about to act on, without any change of user intent:

1. **Creator:** every state mutation re-renders the step body synchronously, and the save
   response triggers a *second, asynchronous* full rebuild of the same body ~400 ms + RTT later.
2. **Dashboard/nav:** the book scene replaces its entire surface (topbar, ribbon, crest) at
   least twice during load; the shared nav then rebuilds the ribbon and a *new* profile
   button for each replaced topbar.

Neither path exposes a "render settled" signal; tests that pass reliably poll internal
`SrdCreator.app` flags.

## 3. Direct source facts

### 3.1 Creator autosave / render loop (`vtt/static/js/srd-creator.js`)

| # | Fact | Ref |
|---|---|---|
| C1 | `SC.mutate` applies `fn(state)`, sets `dirty=true`, calls `scheduleSave()` (400 ms default) and then **synchronously** `renderAll()` unless `render:'none'`. | 223-229 |
| C2 | `scheduleSave` clears and re-arms one timer; rapid mutations debounce to one save 400 ms after the last one. | 232-235 |
| C3 | `runSave`: if already saving, re-arms at 300 ms; sets `saving=true, dirty=false`, PUTs `{version, state, step}`. | 237-244 |
| C4 | On 2xx response: `applyView` updates **only** `version`, `name`, `evaluation`, `blockers` — the local `draft.state` is kept (canonical draft state is client-held; server returns version). | 216-221, 247 |
| C5 | After a successful save, if `!dirty && !typing && !finalizing && status==='draft'` → **full `renderAll()`**; otherwise `renderChrome()`. `typing` is true only for focused `TEXTAREA` or `INPUT[type=text|search|number]` — **not** for `SELECT`, `BUTTON`, checkbox or radio. | 249-251 |
| C6 | If a mutation arrived during the PUT, `dirty` is true again → only chrome is rendered and a follow-up save is scheduled at 100 ms. | 248, 251, 268 |
| C7 | `goStep` sets `dirty=true`, `scheduleSave(800)`, then `renderAll()` → entering a step also produces a deferred save-response rebuild ~800 ms + RTT later. | 608-616 |
| C8 | `renderAll` = `captureBuilderView` → `renderBody` (`body.textContent=''` then rebuild every section from step renderers) → `renderChrome(false)` → `restoreBuilderView`. All controls in `#scStepBody` are new nodes after each call. | 468-481, 583-603 |
| C9 | Focus restore re-finds the active control by `id`, else by `controlKey` (section + group label + tag + type + label/text). For a card button the key includes its full text content. | 492-507, 555-566 |
| C10 | `openDraft` renders, then `loadExtras().then(() => renderChrome())` — a further async chrome rebuild (steps nav, summary, findings; not the step body). | 668-669 |
| C11 | `vtt:displaychange` → `loadLocale()` and `refreshLocaleView()` → `renderAll(true)` (locale-preserving rebuild), and again after the overlay resolves. | 856-875 |
| C12 | `SC.openEntry` sets `#scDialogTitle.textContent` to the fallback title **synchronously, before any `await`**, then calls `showModal()`. | 165-175 |
| C13 | Pending-input protection exists: inputs with `onchange` track pending edits in a `WeakSet` and re-dispatch `change` on blur while connected; locale-only rebuilds carry pending values across. Non-locale `renderAll` does not carry pending values across (it relies on C5's `typing` guard). | 23-46, 586-602 |

### 3.2 Species step (`vtt/static/js/srd-creator-steps.js`)

| # | Fact | Ref |
|---|---|---|
| S1 | Species cards are `<button class="sc-card" aria-pressed=…>`; onclick → `SC.mutate(...)` setting `state.species={id, choices:{}}` when id differs → full rebuild per click (C1). | 36-39, 315-317 |
| S2 | The species detail block, including the "Spezies-Text lesen" button (`SC.detailButton` → `SC.openEntry`) and species choice selects (e.g. draconic ancestry), exists only for the currently selected species. | 318-323, 210 |
| S3 | Species choice selects call `SC.mutate` on `change` → full rebuild (C1) and later save-response rebuild (C5, since a focused `SELECT` is not "typing"). | 233-260, 29-35 |
| S4 | `SC.onSaved` only toggles the finalize button's `disabled`. | 919-922 |

### 3.3 Dashboard / nav composition

| # | Fact | Ref |
|---|---|---|
| N1 | `dashboard.html` boots via `BookScene.bootstrapProtectedRoute({routeKey:'dashboard', snapshotLoader: loadDashboardSnapshot})`. | `vtt/templates/dashboard.html:61-76` |
| N2 | `bootstrapProtectedRoute` → `create()` → `showLoadingShell` (writes `sceneSurface.innerHTML` with `buildPageShell(...loading:true)`) → awaits `requireAuth` + `loadPageContent` → awaits snapshot → `bootstrapRoute` → `showSceneInstant` → `renderSceneRoute` (writes `sceneSurface.innerHTML` again). | `vtt/static/js/book-scene.js:2642-2695, 2621-2634, 2575-2611, 2470-2505` |
| N3 | `create()`'s setup ends with `ensureDashboardScene()` → `renderSceneRoute('dashboard')` (another full surface write) — whether this runs on the dashboard path depends on `create()`'s bind-once guard (not fully traced). | `book-scene.js:250, 390-392` |
| N4 | `buildPageShell` always contains `.book-dashboard-topbar` > `.book-dashboard-ribbon` + `.book-dashboard-crest`, including in the loading shell. | `book-scene.js:994-1013` |
| N5 | `vtt-main-nav.js` observes the whole document (`MutationObserver` childList+subtree) and on a microtask runs `scan()`: any `.book-dashboard-ribbon` without `data-vtt-main-nav="true"` gets `buildRibbon` + `buildAccount`. | `vtt/static/js/vtt-main-nav.js:324-351` |
| N6 | `buildAccount` replaces the crest with a memo containing a new `button.vtt-account-profile` (click → `openOwnProfile`), then awaits the cached `/api/dashboard/navigation` memo. | `vtt-main-nav.js:276-322` |
| N7 | Therefore, per source, the profile button created on the loading shell is discarded when the final route render rewrites `sceneSurface`, and a new one is built on the next microtask. Further `renderSceneRoute`/`transitionToRoute`/`innerHTML` writes (e.g. `book-scene.js:1614, 1633, 1666, 2792`) repeat this. | N2-N6 |
| N8 | `openOwnProfile` → `mountQuota` is only reached after the click handler runs and `/api/review-web/profile` resolves. | `vtt-main-nav.js:229-274` |

### 3.4 Creator home entry

| # | Fact | Ref |
|---|---|---|
| H1 | `init` performs strictly sequential awaits before `#scNewGuided` exists: `requireAuth`, `/meta`, `/creator-data?displaySchema=1`, `/species-catalog`, `/origin-catalog`, `SC.loadLocale()`, then `showHome()` → `/drafts`. | `srd-creator.js:803-844, 732-771` |
| H2 | With rules locale `en`, `loadLocale` adds one more serial request `/creator-display?locale=en&v=<hash>`; with `de` it returns immediately. | `vtt/static/js/srd-creator-locale.js:61-86` |

### 3.5 Existing tests / observability

| # | Fact | Ref |
|---|---|---|
| T1 | Quota browser tests set `page.set_default_timeout(8000)`; `_open_profile` does `goto('/dashboard')` then immediately `.vtt-account-profile.first.click()`. | `tests/test_campaign_quota_browser.py:64, 76-79` |
| T2 | Same pattern in review UI tests. | `tests/test_review_ui_browser.py:46, 73` |
| T3 | Creator locale test asserts `#scNewGuided` text with `expect(...)` and no explicit timeout (Playwright `expect` default is 5 s and is not changed by `set_default_timeout`) — matches the "existing 5 s assertion" in O3 for the `('de','en','en')` parameter. | `tests/test_creator_rules_locale_browser.py:9-19` |
| T4 | Several creator tests already settle on `!SrdCreator.app.dirty && !SrdCreator.app.saving` via `wait_for_function`. | `test_creator_content_browser.py:49,74,125`; `test_creator_equipment_browser.py:27`; `test_creator_rules_locale_browser.py:55,114` |
| T5 | No public render-generation counter, settle event, or `data-*` busy/saved state exists for the creator (contrast: mapmaker exposes `#saveStatus[data-state]`, `tests/test_fv06_brush_controls_browser.py:38`). Dashboard exposes `sceneRenderVersion` only as an internal property. | source search |

## 4. Provided observations vs. source (consistency, not proof)

- **O1a (no modal, old title):** By C12, any invocation of `openEntry` overwrites the title
  synchronously. An unchanged old class title therefore indicates `openEntry` was most likely
  **not invoked** by that click (alternative: an exception before line 171, none visible in
  source). This is consistent with, but does not prove, the click being delivered to a node
  that was replaced or to no handler.
- **O1b (Dragonborn focused, Goliath selected, ancestry absent):** Consistent with a
  Dragonborn card receiving focus (pointer-down) without its click handler mutating state,
  followed by a rebuild whose focus restore (C9) re-focused the new Dragonborn card. The
  ancestry select is only rendered for Dragonborn (S2), so its absence follows from the
  state still being Goliath.
- **O1c (settle-per-action journey passes):** Consistent with C5: once `!dirty && !saving`,
  the deferred save-response rebuild has already happened.
- **O2:** Consistent with N7 (profile button replaced during load). Source does not explain
  why the 8 s deadline was exhausted rather than Playwright re-resolving `.first` to the new
  button; unknown.
- **O3:** Consistent with H1/H2 (6–7 serial requests before the home button, one extra for EN
  rules). No timing data exists to attribute the overrun.

## 5. Unproven hypotheses (require instrumented evidence)

- **H-A (creator):** A pointer action whose `mousedown`→`mouseup`→`click` straddles the
  deferred save-response `renderAll` (C5) or a sync `renderAll` from a preceding select
  `change` (S3) loses the `click` (target detached / different node under pointer), so no
  `mutate`/`openEntry` runs. Window per action ≈ save delay (400/800 ms) + PUT RTT.
- **H-B (creator, select):** A native `<select>` change committed during a rebuild window
  may mutate state for a node that is then replaced; ordering with a following card click is
  untested.
- **H-C (dashboard):** Playwright actionability resolved the loading-shell profile button,
  the final render detached it, and repeated retries kept racing further surface rewrites or
  slow bootstrap until 8 s elapsed.
- **H-D (home entry):** Serial bootstrap latency under parallel test load, plus the EN
  overlay request, occasionally exceeds 5 s.

None of H-A…H-D has been reproduced or measured. Autosave full-render timing remains a
hypothesis exactly as the handoff states.

## 6. Risks and assumptions

| Risk | Severity | Note |
|---|---|---|
| R1 Real users on slow links lose card/detail clicks in the creator during the deferred rebuild window (if H-A holds). | **Medium** (UX/data intent; no data corruption seen — state stays canonical per C4, conflict handling unchanged) | Player-facing; affects every mutate-driven step, not only species. |
| R2 Browser tests flaky on post-load node replacement (creator and dashboard). | Medium (delivery/CI reliability) | Masks real regressions; retries hide signal. |
| R3 A later fix suppresses or delays rebuilds and drops pending input, focus, or the server version update. | Medium | Must preserve C4, C6, C13, conflict path 253-256/292-308. |
| R4 A later fix touches shared nav/book-scene and alters Player/DM composition or auth bootstrap. | Medium | `vtt-main-nav.js` and `book-scene.js` serve Player and DM pages; role separation rules in AGENTS.md apply. |
| R5 "Fix" by generic timeout increases. | Low/Medium | Explicitly out of bounds; hides cause. |
| No security/privacy finding. No critical finding. No mandatory human decision trigger fired. | — | — |

Assumptions: O1–O3 are accurate as reported; Firefox and Chromium click-retargeting
behaviour on detached targets was not checked against documentation in this pass.

## 7. Open questions / missing evidence

1. Per-action timeline (instrumented) of `mutate`, `runSave` start/end, `renderAll` calls,
   and pointer/click events for the O1 journey — does a rebuild land between pointerdown and
   click?
2. Does the click in O1a reach any handler? (Event listener log on `#scStepBody`.)
3. Dashboard: count of `sceneSurface` writes and `vtt-account-profile` creations per load,
   and whether N3's `ensureDashboardScene()` runs on `/dashboard` (bind-once guard at
   `book-scene.js:250+`, not fully traced).
4. Why Playwright did not succeed on the replacement profile button within 8 s (trace file
   from the failed O2 run, if retained).
5. Wall-clock breakdown of the creator init request chain for `('de','en')` (H1/H2).
6. Does Firefox vs. Chromium differ for O1 (live was Firefox; repo browser tests launch
   Chromium, `test_campaign_quota_browser.py:61`)?

## 8. Smallest factual boundary for Apply

In scope for a later Apply (design only; no choice made here):

- Creator: `srd-creator.js` save→render handoff (lines 223-269, 583-616) and possibly an
  observable settle/generation signal; species step only as the reference journey
  (`srd-creator-steps.js:310-323`).
- Dashboard/nav: the load-time composition sequence `book-scene.js:2621-2695, 2470-2505`
  and `vtt-main-nav.js:276-351`, limited to profile-entry stability and an observable
  "composed" signal.
- Tests: the affected helpers (`test_campaign_quota_browser.py:76-79`,
  `test_review_ui_browser.py:46,73`, creator species journeys) — settling on a defined
  signal rather than raw timeouts.

Must be preserved by any Apply:

- Canonical client draft state, server `version` handshake and 409 conflict flow
  (`srd-creator.js:216-221, 253-256, 279-308`); pending-input and typing guards (C5, C13);
  finalize waits (775-789).
- Player/DM separation: nav/book-scene changes must not mount DM controls on Player
  surfaces or alter server-side context authorization.
- FV15 quota panel behaviour and Codex's in-flight FV15 files (not touched here).

Out of scope: generic timeout increases, architecture choice, locale/overlay redesign,
unrelated book-scene routes.

## 9. Next step

Apply (FV18): first decide the evidence step — an instrumented read-only trace (render
counter + event log) for O1/O2 run by Codex, who owns test execution — then design within
§8 with acceptance criteria that (a) a card/detail click after a mutation is never lost
under a simulated slow PUT, (b) the profile entry is clickable exactly once composition is
signalled, (c) C4/C6/C13 and the conflict path behave unchanged.
