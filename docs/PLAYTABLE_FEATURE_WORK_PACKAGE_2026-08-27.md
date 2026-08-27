# Playtable feature work package

**Date:** 2026-08-27  
**Status:** research-first backlog; no production implementation approved  
**Scope:** Roll-Drauf VTT playtable inspired by the supplied VTT screenshots

## Working agreement

We will handle one feature slice at a time. Each slice has its own research note before implementation. A research note must distinguish facts, opinions, and proposed decisions.

Every feature research pass uses this structure:

1. **Current-state fit** — relevant routes, models, UI elements, realtime events, permissions, and constraints in Roll-Drauf.
2. **Web research** — first-party documentation, official APIs, standards, or source code for technical facts.
3. **Good examples** — concrete interfaces or workflows worth borrowing, with reasons.
4. **Bad examples** — failure modes, friction, clutter, accessibility problems, or unsafe defaults.
5. **Lessons learned** — rules that should survive into our design.
6. **Community favorites** — repeated community preferences and workflows, clearly labeled as opinion/anecdotal evidence rather than product requirements.
7. **Roll-Drauf boundary** — what belongs in this slice, what is explicitly deferred, and what data/API contract is needed.
8. **Acceptance criteria** — observable desktop, mobile, keyboard, permission, realtime, and error behavior.
9. **Apply handoff** — the design questions that need to be settled before code changes.

Primary sources establish behavior and technical constraints. Community sources may inform preference and discoverability, but they do not override security, accessibility, or our existing domain model.

## Parallel-work rules

The current repository has one `main` worktree and the playtable is still concentrated in a few large files. Parallel work is safe only when both agents use separate branches/worktrees or keep an explicit disjoint file ownership.

### Codex ownership

Codex owns the integration seam and final release path:

- `vtt/templates/play.html`
- `vtt/static/js/play-ui.js`
- `vtt/static/js/play-client.js`
- `vtt/static/js/play-socket.js`
- `vtt/play/routes.py` and `vtt/play/actions.py`
- shared playtable contract tests and deployment/production verification

Codex also resolves cross-feature state, permissions, event payloads, and merge order. Claude should not edit these files concurrently.

### Safe Claude work now

While Codex is researching or implementing one slice, Claude can work on separate files only:

| Work type | Safe assignment | Handoff rule |
|---|---|---|
| Feature research | One feature note per file, for example `PLAYTABLE_FEATURE_RESEARCH_02_APP_MENU_*.md` through `10_VISION_*.md` | No production edits; include primary sources and a clearly labeled community-opinion section. |
| Current-state inventory | Read-only map of routes, models, events, permissions, and existing IDs | Do not “fix” discovered gaps; report them in the note. |
| Contract tests | New feature-specific test files under `tests/`, using stable existing selectors/events | Do not modify shared fixtures or existing playtable tests without coordination. |
| Isolated backend module | Only after Apply approval: new model/service/schema files for loot or vision | Route registration, migrations, and central wiring wait for Codex. |
| Documentation/assets | New docs or catalog files with a unique path | Do not edit the shared broad research note or active implementation files. |

### Unsafe concurrent work

Do not have both agents edit `play.html`, `play-ui.js`, `play-client.js`, `play-socket.js`, `vtt/play/routes.py`, the same test file, deployment files, or the same research note. Do not let either agent deploy while the other has uncommitted changes. Use one final Codex-controlled commit and deploy after the slice is integrated and verified.

### Recommended operating mode

If Claude is using the same filesystem, give Claude only isolated research/test tasks and ask for no commit. If Claude needs to write code, use a separate worktree and branch, then merge one bounded change at a time. Every handoff must list changed files, tests run, unresolved risks, and whether the work is research, Apply design, or Deploy implementation.

## Iteration order

The order follows dependencies and user value rather than the screenshot order:

| # | Feature slice | Research artifact | Current state | Dependency |
|---:|---|---|---|---|
| 1 | Scene/page directory and active-scene card | `docs/PLAYTABLE_FEATURE_RESEARCH_01_SCENES_*.md` | Existing layer stack, thumbnails, activation, reorder, add/copy | None |
| 2 | Application Escape/Menu surface | `docs/PLAYTABLE_FEATURE_RESEARCH_02_APP_MENU_*.md` | Existing campaign return and sidebar toggle | Session/navigation routes |
| 3 | Map tool rail and measurement | `docs/PLAYTABLE_FEATURE_RESEARCH_03_MAP_TOOLS_*.md` | Select, pan, token; measurement is not complete | Map interaction state |
| 4 | Selected-token HUD and character/creature focus | `docs/PLAYTABLE_FEATURE_RESEARCH_04_TOKEN_HUD_*.md` | Selected token widget and sheet drawer | Token selection |
| 5 | Conditions/status picker | `docs/PLAYTABLE_FEATURE_RESEARCH_05_STATUSES_*.md` | Conditions array and count badge | Token HUD + status schema |
| 6 | Combat strip and initiative | `docs/PLAYTABLE_FEATURE_RESEARCH_06_COMBAT_*.md` | Turn-order widget and combat events | Token HUD |
| 7 | Personal action hotbar | `docs/PLAYTABLE_FEATURE_RESEARCH_07_HOTBAR_*.md` | Generic action catalog and executor | Action definitions |
| 8 | Roll composer and chat dock | `docs/PLAYTABLE_FEATURE_RESEARCH_08_ROLL_CHAT_*.md` | Sidebar chat and basic dice input | Roll event/visibility contract |
| 9 | Loot transfer and inventory | `docs/PLAYTABLE_FEATURE_RESEARCH_09_LOOT_*.md` | Character inventory CRUD only | Multi-selection + container model |
| 10 | Lighting, vision, walls, and Fog of War | `docs/PLAYTABLE_FEATURE_RESEARCH_10_VISION_*.md` | Image/grid/token map; no vision engine | Scene geometry + permission model |
| 11 | Cross-cutting responsive/accessibility/realtime hardening | `docs/PLAYTABLE_FEATURE_RESEARCH_11_QUALITY_*.md` | Partial responsive and pointer support | Each implemented slice |

The existing broad note remains the visual and architectural overview: [`PLAYTABLE_UI_RESEARCH_2026-08-27.md`](PLAYTABLE_UI_RESEARCH_2026-08-27.md). The feature notes will be narrower and decision-ready.

The concrete Claude prompts are maintained in [`PLAYTABLE_CLAUDE_RESEARCH_PROMPTS_2026-08-27.md`](PLAYTABLE_CLAUDE_RESEARCH_PROMPTS_2026-08-27.md).

## Per-slice phase gate

```text
Research / Discover
  → review findings and unresolved risks
  → Apply: choose the smallest design and contracts
  → Deploy: implement only the approved slice
  → Monitor: run proofs and record follow-ups
  → next feature
```

No feature gets bundled into another slice merely because it appears in the same screenshot. Destructive or permission-sensitive operations—such as deleting a scene, resetting Fog of War, leaving a session, or transferring loot—must have an explicit confirmation and server-side authorization boundary.

## First slice

Start with **scene/page directory and active-scene context**. It already has a stable backend and UI seam, improves the table immediately, and gives later token/vision work a reliable scene context. Its research pass should answer:

- Which scene-directory behaviors are genuinely useful at the table versus administrative overhead?
- How should thumbnails, active state, search, actions, and scene notes behave on desktop and mobile?
- Which actions are DM-only, which are player-visible, and which need confirmation?
- Should active-scene context be a drawer, popover, or compact card?
- What do current VTT communities repeatedly praise or dislike about scene navigation?

The first research artifact is the next deliverable. Production code remains out of scope until its Apply handoff is accepted.

## Slice 01 (Scenes) — Apply decisions and Deploy status: DONE, 2026-08-27

Adrian explicitly overrode the Codex-file-ownership rule for this round ("code it directly in main, no worktree" — full override, coordinating live with whatever Codex is doing) rather than handing the Apply-approved slice to Codex. Implemented directly in `vtt/templates/play.html` / `vtt/static/js/play-ui.js`.

Apply decisions taken (smallest-footprint default from each research question, per this doc's own working-agreement principle):
- Flat list only, no folders this slice.
- No thumbnail cache-busting mechanism yet (URLs assumed stable per CampaignMap).
- Client-side name/map-name filter only, no server-side search.
- Scene notes UI deferred.
- Reorder stays buttons-only (Up/Down); no drag-and-drop this slice.
- Socket events: **kept the existing `scene:layer_activated` / `scene:layers_updated` convention** — the research doc treated this as an open, non-reversible question, but the backend CRUD (activate/create/reorder/update/delete) turned out to already be fully built and already using exactly this convention, so there was nothing left to decide.
- Reconciliation: the existing full-`loadBootstrap()`-refetch-on-mutation pattern was kept (already matches "reconcile from server snapshot" in spirit); no new optimistic-update layer was added.

Real gap found during Apply review: the research doc's "duplicate/visibility toggle" asks collided with a **previously and deliberately removed** visibility-toggle control (commit `8e856de`, removed for reusing the same eye glyph as the activate button — genuinely confusing). Reintroduced it with a lock/unlock icon instead of an eye, so it can't recreate that exact ambiguity; a robot-flow assertion (`scene_directory` in `tools/robots/flows.py`) now checks the two icons never match, so this can't silently regress a second time.

Delivered: thumbnail rows (already existed), a duplicate action (reuses the existing add-layer `allow_copy` endpoint, no new backend route), a lock/unlock player-visibility toggle, a client-side search/filter input, roving-tabindex keyboard navigation (arrows/Home/End/Enter/Space, W3C APG listbox pattern), scroll-active-layer-into-view on reopen, a named+irreversibility-worded delete confirmation, and 44px mobile touch targets for the row buttons. Not delivered (explicitly deferred per the Apply decisions above): folders, scene notes UI, drag-and-drop reorder, server-side search.

Verification: contract tests in `tests/test_public_surface_and_playtable_contract.py` (extended + one pre-existing test sharpened rather than deleted, see its docstring), a new real-browser robot flow `scene_directory` in `tools/robots/flows.py` (0 findings against a disposable stack, alongside all 4 pre-existing flows also still green), full `pytest` suite 495 passed / 0 failed.

Next: slice 02 (Application Escape/Menu surface) per the iteration order below, same per-slice Apply-then-Deploy gate.

## Slice 02 (App Menu) — Apply decisions and Deploy status: DONE, 2026-08-27

Current-state check (per the Slice 01 lesson: always verify before trusting the research doc's gap list) found far more already built than the doc assumed:
- Pause/Resume/End already have working dedicated UI (`#btnPause`/`#btnEnd`/etc. calling the existing `POST .../transition` endpoint) — NOT duplicated into the new menu, since that would be a second, redundant control surface for the same action.
- `session:state_changed` + `play:mode` already exist and are already wired client-side — this **is** the "does a status-changed event already exist" open question, just under a different name than the doc guessed (`session:status_changed`). Reused as-is, no new event.
- `presence:update` (roster chip "Am Tisch: …") already broadcasts to everyone when a connection drops, including on the existing `session:leave` socket event that `play-socket.js`'s `disconnect()` already emits on any navigation-away. So "notify other players when someone leaves" was **already fully solved** — no `session:player_left` event was needed either.
- Net effect: Leave Session needed **zero new backend surface**. It's `returnToBook()` (the same navigation `btnBack` already did) behind a confirmation dialog; the disconnect this triggers already tears down presence and updates everyone's roster for free.

Apply decisions: menu button reuses the existing `btnBack` (bottom action-dock, not the research doc's suggested top-right — this app's own established chrome convention beat a generic recommendation); flat menu with a divider, no submenu; status line inside the menu; Escape is dismiss-only and scoped with `stopPropagation()` so it can never leak to token-deselect; Leave copy is a plain German sentence, no "don't ask again" checkbox; **read-only disables Leave with a tooltip** (resolving the research doc's own internal contradiction — Apply-handoff text said "enable it," Acceptance Criteria said "disable it" — in favor of the stricter, already-established "read-only means no mutations" rule used everywhere else in this app); mobile menu becomes a full-width bottom sheet; native `<dialog>` for both Leave-confirmation and Help (first use of `<dialog>` in this codebase — sidesteps hand-rolled focus-trap/z-index risk entirely). Settings and Manage Players were **not** added — no such pages exist yet, and a menu item that links nowhere is a dead button, the exact anti-pattern this codebase already has a house rule against (§2, cited in existing code comments).

Real near-miss caught during Apply review: `#btnSidebarToggle` (Journal/Chat/Tools/Session workspace drawer) already uses the label "Menü" with a ☰ icon. The new app-menu trigger deliberately does NOT reuse that label/icon — doing so would recreate the exact same-label/same-icon ambiguity as the S01 eye-icon near-miss, just for text instead of a glyph. A contract test pins this (`back_button_markup` must not contain "Menü").

Verification: extended `tests/test_public_surface_and_playtable_contract.py`; new real-browser robot flow `app_menu` in `tools/robots/flows.py` (open/close, keyboard nav focus assertions, sidebar-closes-on-open, native-`<dialog>` checks for Help, Leave-cancelled-stays-in-session, Return-navigates) — 0 findings across all 6 registered flows. Full suite: 496 passed, 0 failed.

Next: slice 03 (Map tool rail and measurement).

## Slice 03 (Map Tools) — Apply decisions and Deploy status: DONE, 2026-08-27

A 4th tool button (`data-tool="measure"`) joins select/pan/token, reusing the same world-coordinate math token placement already uses. Fully client-local per the doc's own permission contract (section 9): no persistence, no broadcast, single active measurement, cleared silently on tool switch.

Apply decisions on the open questions: grid-snap defaults ON (matches the primary D&D-grid use case), diagonal distance uses the simplified same-cost-as-orthogonal rule when snapped (5e's own default) and true Euclidean when freehand; **unit-per-square is a hardcoded client constant (5 ft/square)** — `CampaignMap.grid_size` turned out to only track *pixels* per square, not a real-world unit, and no such field exists anywhere in the schema yet, so a real configurable unit is deferred rather than adding new backend schema just for this one label (flagged as a known placeholder, not silently assumed permanent); nested Escape (nothing more to add — nothing else scoped for this slice); silent discard on tool-switch (the doc's own Acceptance Criteria section, not its conflicting risk-mitigation toast+undo proposal); single-active-measurement only; AoE templates and walls/LOS explicitly out of scope, as the doc itself scoped them.

Verification found two bugs in the verification code itself, not the feature — worth noting since they'll recur: Playwright's `wait_for_selector` defaults to waiting for "visible", so asserting an element *becomes* `[hidden]` needs `state="attached"` explicitly (bit S02's app-menu flow too); and SVG `<text>` isn't an `HTMLElement`, so `.inner_text()` throws on it — `.text_content()` works on any node type. Both are now the pattern to reuse for any future SVG-overlay or hide/show flow work.

Scenario-first: extended `tests/test_public_surface_and_playtable_contract.py` (including a check that the read-only flag is never referenced anywhere in the measurement interaction code, since — unlike the token tool right next to it — this one must stay usable in read-only mode); new real-browser robot flow `measure_tool` covering waypoint placement, the game-unit distance label, right-click undo, nested-Escape-to-empty, and clears-on-tool-switch — 0 findings across all 7 registered flows. Full suite: 497 passed, 0 failed.

Next: slice 04 (Selected-token HUD and character/creature focus).

## Definition of done for this work package

- Every feature has a separate cited research note before implementation.
- Each note contains good examples, bad examples, lessons learned, and community favorites.
- Facts from first-party sources are separated from community opinion and our design inference.
- Each Apply handoff defines data contracts, permission boundaries, responsive behavior, and acceptance criteria.
- Each Deploy slice has targeted tests/proofs and leaves unrelated work untouched.
- Each Monitor pass records residual risk before the next feature begins.

## Slice 04 (Token HUD) — Apply decisions and Deploy status: DONE, 2026-08-27

The research doc's fuller ambition (dynamically anchoring a floating HUD to the token marker's exact on-map position, re-anchoring on every scroll/zoom/resize without flicker) was **deliberately not built**. This app already has an established, working convention for `#tokenWidget` as a user-positioned, draggable floating panel (F5/S01, earlier the same day); continuously re-anchoring a panel to a moving world-space point is a materially larger and jankier undertaking (Risk R1, flagged MEDIUM in the doc itself) than reusing that existing pattern. Documented as an explicit Apply-phase deviation from the literal acceptance criteria wording, not a silent cut — `#tokenWidget` already auto-opens on selection (earlier F4 work, same session) and is already draggable.

Current-state check found most of the "editable" HUD already built (from earlier same-session F4 work, before this slice-by-slice pass even started): name/HP/image/delete controls, owner-or-DM permission gating, and a delete confirmation that already names the token. The real, concrete gap was narrower: an unowned/observed token showed nothing at all beyond a one-line "Ausgewählt: NAME" summary — no HP, no indication it wasn't the viewer's. Fixed with a read-only counterpart view. Also added: a reconnecting indicator (this app had zero connect/disconnect handling anywhere before this), and an enhanced delete-confirmation message stating the blast radius.

Status-icon rendering (depends on S05's schema, not yet built), combat/initiative display (depends on S06, not yet built), and multi-select (depends on S09, not yet built) are explicitly deferred. Real bug caught mid-implementation: a naive truthiness check would have silently rendered "HP unbekannt" for a token at exactly 0 HP (0 is falsy) — fixed to an explicit != null check.

Verification found a real API-routing gotcha, not a feature bug: play_bp is mounted at /api/play, not /api. Also: token x/y default to grid-cell coordinates, not pixels — needs metadata_json.position_mode = "pixel" for pixel placement.

Deliberately incomplete robot coverage, stated rather than silent: the cross-user read-only view is NOT covered by the new token_hud robot flow (would need a second browser context plus a full invite/join dance) — covered instead by a direct contract-test assertion.

Scenario-first: extended tests/test_public_surface_and_playtable_contract.py; new real-browser robot flow (token_hud) — 0 findings across all 8 registered flows. Full suite: 498 passed, 0 failed.

Next: slice 05 (Conditions/status picker).

## Slice 05 (Statuses) — Apply decisions and Deploy status: DONE, 2026-08-27

Apply decisions: hardcoded 16-entry D&D-5e-ish condition catalog (the research doc's own list is labeled "~15" but literally enumerates 16 including "concentrating" — a documentation nit in the upstream research, not something to silently correct one way or the other); conditions stay in `metadata_json.conditions` (no migration) but each entry is now validated against the canonical id list server-side, where previously any free-form string was accepted; duration/value/source fields deliberately not added to the schema yet (S06 hasn't defined tick semantics); clear-all always confirms, naming the token and count; text-only labels, no icons yet; separate desktop-grid vs mobile-list popover layouts; conditions toggle through the existing token PATCH/socket-update path rather than new dedicated endpoints.

New isolated module `vtt/play/conditions.py` (the slice's whole "claude_safe_subscope") holds the catalog + a `validate_condition_ids` helper, unit-tested directly in `tests/test_conditions_catalog.py`.

**A real regression was caught and fixed mid-slice, in a *pre-existing, previously-passing* flow, not new code**: `beyond20-bridge.js` was synthesizing an "Erschöpfung N" (exhaustion level) string and mixing it into the same conditions array the new server-side validator now guards — since that string is never a canonical condition id, the *entire* conditions patch was being silently rejected, breaking the existing Beyond20 exhaustion sync end-to-end. Root cause: exhaustion is a 0–6 *level*, not a togglable condition, and never should have been smuggled into a string array as free text. Fixed properly rather than papered over: exhaustion now travels as its own `metadata_json.exhaustion_level` field through the whole pipeline (bridge → `updateCharacterConditions` handler → both display spots), folded back into the combined display text only at render time. The Beyond20 sync path also now filters incoming condition names against the catalog and silently drops unrecognized ones instead of hard-rejecting the whole update — correct for an external, semi-trusted integration (D&D Beyond's vocabulary isn't ours to control), unlike our own picker UI which only ever sends canonical ids by construction and can stay strict.

One more real bug caught by the new `conditions_picker` robot flow itself (not by hand-inspection): `_renderConditionsPopover()` rebuilds the entire checkbox list on every realtime state render, including immediately after the user's *own* toggle — which silently destroyed keyboard focus every time, breaking Escape-to-close and arrow navigation the moment anyone actually used them. Fixed by remembering which condition id had focus and restoring it to the corresponding new checkbox after rebuild.

A pre-existing test's literal-English assertion ("Poisoned, Prone, Erschöpfung 1") was updated to the new German-labeled display ("Vergiftet, Liegend, Erschöpfung 1") — a deliberate, documented consequence of canonicalizing condition display consistently across the app (matching the picker's own German UI) rather than leaking raw English strings through from the external sync, not a silently-tolerated regression.

Scenario-first: 7 new unit tests on the isolated catalog module, 1 new contract test, and a new real-browser robot flow (`conditions_picker`) covering the full catalog rendering, badge count, the image_url-survives-a-toggle check (the exact bug a naive whole-metadata_json-overwrite would cause), Escape-restores-focus, and the clear-all confirmation — 0 findings across all 9 registered flows (including the previously-broken `beyond20_bridge`, now fixed). Full suite: 506 passed, 0 failed.

Next: slice 06 (Combat strip and initiative).

## Slice 06 (Combat) — Apply decisions and Deploy status: DONE, 2026-08-27

Current-state check found the combat backend already largely built — the research doc's proposed "seven new DM-only endpoints" (start/end/advance-turn) were already live and working (`combatStart`/`combatAdvanceTurn`/`combatEnd`), including version-conflict retry-on-fetch-fresh-state logic and server-side hidden-participant filtering for the active-encounter render path. The gap was narrower and more surgical: no "Zug m von n" position in the summary, no live-region announcement (the doc's own HIGH-severity risk), no click-to-select sync between turn-order rows and map tokens (rows had zero interaction), no pending-disable on the DM buttons during a request, and undersized mobile touch targets.

Apply decisions: brief live-region text (name + round, not full HP/conditions); flat list, no party/enemy grouping this slice; vertical mobile list, not a carousel; Space-to-advance-turn needed no code at all — it's already native `<button>` focus behavior, matching the "focus-aware, not global" recommended default for free; bidirectional token<->turn-order selection sync built both directions. **Deliberately not built**: a dedicated initiative-edit-with-confirmation-and-audit-log UI — no such editing surface exists today (initiative is set via bulk auto-roll only), and inventing one wasn't clearly in scope versus the slice's actual acceptance criteria; flagged rather than silently developed.

Real bug caught by the new robot flow, not by inspection: `_renderState()` doesn't itself call `_renderTurnOrder()`, so selecting a token via any OTHER path (map click, HUD) never updated the turn-order widget's selection highlight — the "bidirectional" sync would have only worked one direction. Fixed by calling `_renderTurnOrder()` explicitly from `_selectToken()`.

Test-authoring note for next time: `combatStart(..., "auto")` re-rolls initiative server-side regardless of what value a token was created with — a robot flow asserting seat order by name/position will be flaky by construction; correlate by `data-token-id` instead (now added to both turn-order rows and reused from the existing token markers).

Scenario-first: 1 new contract test, new real-browser robot flow (`combat_turn_order`) covering the turn-position summary, the live-region announcement changing across a turn advance, and the full bidirectional selection sync in both directions — 0 findings across all 10 registered flows. Full suite: 507 passed, 0 failed.

Next: slice 07 (Personal action hotbar).

## Slice 07 (Hotbar) — Apply decisions and Deploy status: DONE, 2026-08-27

Genuinely new UI this time — no hotbar existed at all, though the backend seam (`vtt/play/actions.py`'s `ACTION_CATALOG`/`execute_action`, `POST actions/execute`) was already fully built with real permission checks (operator-or-owner, read-only-mode 403) and already broadcasts `action:executed` over the socket. Discovered along the way: a full-featured "Aktionsleiste" panel already exists in the sidebar Tools tab (actor + explicit target + action selects, a fire button) — kept untouched rather than replaced, since it supports an explicit target picker the new quick-fire hotbar deliberately doesn't (Apply decision matching the research doc's own scope). Both surfaces now coexist for different moments.

Apply decisions: kept the existing 3-action catalog, no expansion; **renders exactly `catalog.length` slots (3), not a fixed 10 padded with empty placeholders** — with only 3 real actions, 7 grey placeholder slots would be pure clutter for zero functional value, a deliberate deviation from the AC's literal "10 slots" wording (which was clearly written assuming a fuller catalog); no cooldown/use-count schema or tracking; no drag/drop; no paging; no token-specific action variants; fuller accessible-name pattern ("Slot N: Aktion (Taste N)"); auto-populate all catalog actions, no user selection step. Positioned as a new `position: fixed` bottom-center bar rather than a grid child of `.tabletop-shell` — `.left-toolbar` right below it uses explicit CSS-grid row/column placement in that shell's layout, and touching that grid to insert a new item correctly would have meant understanding and risking the whole shell's grid-template; fixed positioning sidesteps that. Exact pixel offset is a reasonable stacked-above-the-toolbar estimate, not visually verified — flagged as a legitimate follow-up rather than claimed as pixel-perfect.

Also upgraded `_handleAction`'s existing message handler: it was already receiving the `action:executed` broadcast but showing a raw, developer-facing toast ("Aktions-Event: attack_basic") with no actor/target names. Now resolves the action code through the same catalog the hotbar renders from and posts a readable line to chat + activity log ("Held setzt Dash ein.").

Verification found a real robot-flow setup gap, not a feature bug: `play_execute_action` 409s unless the session has actually transitioned to `"in_progress"` — earlier flows in this batch never needed this (they don't call the actions/execute endpoint), so the two-hop `scheduled -> ready -> in_progress` transition call was missing entirely from the new flow. Worth remembering for any future flow that fires an action.

Scenario-first: 1 new contract test, new real-browser robot flow (`action_hotbar`) covering the exact slot count, disabled-with-no-selection, click-to-fire, numeric-key-to-fire, and — the research doc's own HIGH-severity risk — that shortcuts do NOT fire while focus is in `#chatInput` — 0 findings across all 11 registered flows. Full suite: 508 passed, 0 failed.

Next: slice 08 (Roll composer and chat dock).
