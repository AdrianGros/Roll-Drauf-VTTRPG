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

## Slice 08 (Roll/Chat) — Apply decisions and Deploy status: DONE, 2026-08-27

Current-state check directly refuted the research doc's own claim: it said "no chat message schema at all (no author, timestamp, type, or visibility metadata)". The real `ChatMessage` model already had author, timestamp, a `content_type` enum, moderation state, and dedup via `client_event_id` — a fully mature schema. Chat history was already capped at 30 messages server-side too, well inside the doc's own "don't render 1000+ messages" risk threshold, so no pagination/load-more work was needed. The one genuinely missing piece, and the actual headline feature of this slice, was **visibility** — every roll was unconditionally broadcast to the entire session room with no scoping at all.

Apply decisions: one table with existing `content_type` (not a new roll table) plus a new `visibility` column (public/gm_only/blind/self, default public) — migration `migrations/migration_m69_chat_message_visibility.sql`, same manual-apply caveat as m68 (`AUTO_CREATE_SCHEMA` never adds columns to existing tables); ADV/DIS as a dedicated `mode` field, never folded into the dice-formula grammar; ADV/DIS only applies to a genuine single-die roll — a multi-die formula ("advantage on 3d6") has no well-defined meaning and silently falls back to normal rather than erroring; roll broadcast stays socket-based (this app has no polling anywhere); die presets use the doc's own proposed starting set; a fully separate modifier-stepper synced with the formula text was scoped out as a nice-to-have polish item, not a functional gap (the digest itself left this decision unresolved); roll expansion uses native `<details>/<summary>` (explicitly allowed by the acceptance criteria as an alternative to hand-rolled aria-expanded/aria-controls) instead of custom JS toggle state.

**Visibility enforcement** (the research doc's own CRITICAL risk) reuses the exact role-scoped-room infrastructure the earlier F4/S05 secret-filtering work already established (`dm_room`/`players_room`/`user_room`/`sibling_envelope` from `vtt/utils/realtime.py`, the same pattern `_emit_token_event` already used for tokens) — no new broadcast architecture needed, just a new `_emit_scoped_roll` helper mirroring it. Blind/Self are DM-only server-side; a non-DM request is silently downgraded to public rather than erroring the roll. Players receive a genuinely anonymized placeholder for blind/self rolls (`player`/`dice`/`result` all null, only `hidden: true`) — never the real data with a client-side "don't show this" flag, which the research doc explicitly warned would let a modified client cheat. Server-side pytest coverage (not just JS contract-test string matching, given the security stakes) hits the real socket handler end to end across DM and player sockets.

Verification found a real test-script bug in the new robot flow (not a product bug): `#chatLog` lives in a different sidebar tab (`#panel-chat`) than the dice composer (`#panel-tools`) — Playwright correctly reported it as genuinely hidden (`display:none` from the inactive tab), not a false positive; the flow just needed to switch tabs before asserting on chat content.

Scenario-first: 6 new server-side pytest tests (`TestRollVisibility` — non-DM blind downgrade, DM blind roll reaching the DM in full and players only as a placeholder, GM-only reaching no player event at all, a public-roll regression check, and two ADV/DIS tests including "20 rolls, the kept one is never lower than the discarded one" run 20 times to catch a coin-flip discard-selection bug), 1 new contract test, new real-browser robot flow (`roll_composer`) covering die presets, a real advantage roll with an expandable breakdown, DM-enabled Blind/Self options, and the Shift+Enter-vs-Enter split — 0 findings across all 12 registered flows. Full suite: 515 passed, 0 failed.

Next: slice 09 (Loot transfer and inventory).

## Slice 09 (Loot) — Apply decisions and Deploy status: DONE, 2026-08-27

Built concurrently by both sides of the working agreement rather than the "Claude does all of it" override used for S01–S08: Claude drafted the data model (`vtt/models/token_loot.py`, `vtt/models/loot_transfer.py`, `TokenState.is_loot_source`, `Character.is_party_stash`, migration `migrations/migration_m70_loot_transfer.sql`) while Codex built the integration seam live in the same working tree (`vtt/play/routes.py`: `POST loot/transfer`, `GET loot/<token_id>`, `POST loot/<token_id>/items`; the `is_loot_source` DM-only socket-patch carve-out in `vtt/socket_handlers.py`; the `getTokenLoot`/`addTokenLootItem`/`transferLoot` wrapper in `play-client.js`; the loot popover markup in `play.html`). No file was edited by both sides — routes/sockets/client-JS/templates stayed exclusively Codex's, models/migration stayed exclusively Claude's, avoiding the clobbering risk flagged earlier for shared files.

Apply decisions actually landed in Codex's implementation (superseding some open questions from the research doc's §12): single-source-token transfers only, not true multi-source atomicity (research doc's own scope note: "looting two corpses is two clicks, not a functional gap"); idempotency via a unique `idempotency_key` on `loot_transfers`, a retried request returns the cached row instead of re-executing; every quantity decrement is one conditional `UPDATE ... WHERE quantity >= :qty` checked by rowcount rather than an explicit row lock, portable between SQLite (dev) and Postgres (prod); stacking onto an existing same-named `InventoryItem` rather than creating a duplicate; a loot-source token is inherently table-wide/shared — any active session member may loot from it, not just the token's owner or the DM; recipient must be the requester's own character, a party-stash character, or the requester must be an operator; cursed items transfer freely, no blocking/approval logic this slice; only the DM can flag a token `is_loot_source` (added as a carve-out in the existing DM-only socket-patch allowlist, not a general player-writable field); a DM "stock this token" endpoint was added even though no research-doc AC named it explicitly — without it there is no way to ever populate a corpse/chest, so the whole feature would be unreachable end to end.

Claude added server-side pytest coverage against Codex's real endpoints (not just the model layer) given the same idempotency/security stakes as S08's roll visibility: `tests/test_playtable_loot_transfer.py`, 11 tests — happy-path transfer + stacking, depleting a source item deletes its row, DM-to-party-stash transfer, idempotent retry does not double-transfer, over-quantity request is rejected with zero partial mutation, cross-player recipient forbidden, non-loot-source token rejected, transfer blocked outside a live session, DM-only stocking (player attempt forbidden), and recipient-list scoping (a player only sees their own characters + party stash, never other players' characters). All 11 passed against Codex's code on the first run; full suite re-verified at 526 passed, 0 failed (up from 515 at S08, consistent with +11 new tests and no regressions).

Codex paused before wiring `play-ui.js` (the popover markup existed in `play.html` but nothing called it — the feature wasn't clickable end to end). Adrian confirmed Codex had stopped for this round and asked Claude to finish, commit, and deploy the slice, extending the same override used for S01–S08 to the remainder of S09. Claude then wired the client: `_bindLootPopover`/`_renderLootPopover`/`_loadLootPopoverData` (fetch-on-open, not carried in `state_payload` since `TokenLoot` rows aren't part of `TokenState.serialize()`), the DM-only source toggle, the DM-only stock-item row, item selection + transfer submission with a per-submission idempotency key, and `loot:updated`/`loot:transferred` socket registration in `play-socket.js`.

Two real bugs caught by building the `loot_transfer` robot flow (added to the permanent fleet, now 13 flows) — not found by inspection, found by driving the actual UI:

1. **Escape stopped closing the popover after a completed transfer.** `_transferSelectedLoot` disables the (focused) transfer button while the request is in flight; Chromium blurs a disabled element, so focus silently moves to `document.body` and the popover's own `keydown` listener — scoped to the popover element, matching the S05 conditions-popover pattern — never sees the event again. Same class of focus-loss bug S05 already had to account for (there: a list rebuild stealing focus; here: disabling the focused control). Fixed by moving the Escape handler to a document-level listener added/removed alongside the existing outside-click listener, so it works regardless of where focus ends up while the popover is open.
2. **The audit chat line never reached connected clients live.** `play_transfer_loot` persisted the `ChatMessage` row correctly but only ever emitted `loot:transferred` — never `chat:message_sent`, the event `_handleChatBroadcast` actually listens for. The message only would have appeared after a reload/re-bootstrap, silently, with no live confirmation the transfer happened. Fixed by adding a second `chat:message_sent` emit alongside `loot:transferred`, same envelope/room, payload shape matching the existing `chat:message_sent` socket handler exactly (`message_id`/`message`/`sender_id`/`sender_name`/`timestamp`).

Verification: `loot_transfer` robot flow 0 findings after both fixes (toggles the loot-source flag through the real button and confirms it survives a reload, stocks an item through the DM-only add row, transfers it into a real character through the popover, confirms the source item fully depletes, confirms the audit line lands live in `#chatLog`, confirms `inventory_count` on the recipient via a real REST re-fetch). Full pytest suite re-verified at 526 passed, 0 failed (unchanged from the mid-slice check — this fix touched broadcast/UI wiring, not anything server-tested). Full 13-flow robot fleet (all registered flows, not just this slice's new one) re-run end to end: 13 flows, 0 findings — no regression from the play-ui.js/play-socket.js/routes.py changes anywhere else in the table. Nothing else from the original research doc's "not done yet" list changed: still single-source-token only, still no encumbrance enforcement, still no undo.

Next: slice 10 (Vision/FoW).

## Slice 10 (Vision/Fog of War) — Apply decisions and Deploy status: DONE, 2026-08-28

Different in kind from every prior slice: not UI wiring over existing backend, but a genuinely new subsystem (wall geometry, light sources, a server-side raycasting engine, per-user persistent Fog of War) that the research doc itself flagged as needing 10 real architecture/game-design decisions before implementation, not just an Apply-phase scope trim. Given Codex had stopped for the round, Adrian explicitly chose "build the full thing as researched" over a data-model-only cut, so all 10 were decided directly rather than deferred:

1. **Wall representation**: line segments (x0,y0,x1,y1) with `sight`/`light` enum flags — matches what a raycasting intersection test needs directly, no polygon-boundary conversion step.
2. **Fog storage**: JSON arrays of `[col, row]` grid cells (not a bitmap) — no image/canvas dependency exists server-side in this stack, and no client renders a fog mask yet (explicitly deferred), so a human-debuggable cell list beat a binary blob for a brand-new subsystem's first pass.
3. **Light sight model**: Foundry's bright/dim radius split, as the research doc's own default contract already proposed.
4. **DM sight override + no soft-mode**: the DM/operator always sees everything (matches the `is_operator_role` exemption already used everywhere else in this app); a player-side "soft fog" toggle was scoped out — no acceptance criterion required it and there's no fog-mask renderer yet to toggle.
5. **Wall/light creation workflow**: explicitly NOT a freehand draw tool (research doc's own non-goal) — a DM places with one or two map clicks and sensible defaults, then refines via a click-to-edit popover. "Place first, refine after," the same split S01–S09 already use for token creation.
6. **Scene-transition persistence**: Fog of War is keyed to `(user, CampaignMap)`, not to a session — switching maps and back preserves what a player explored, matching Foundry's own per-user/per-scene persistence.
7. **Vision algorithm**: single-pass-per-token radial raycasting (`vtt/play/vision.py`) — one raycast from the token out to an effective range, sampled points classified afterward by distance against the token's own `sight_range` and any vision-providing light's radius, rather than the full Foundry model's separate light-to-cell raycast per light. Documented in the module's own docstring as a deliberate simplification: walls still fully gate what's perceivable at all, only "how far do I see" is simplified. Darkness sources are a flat circular exclusion, not priority-blended.
8. **Performance baseline**: a hard `MAX_EFFECTIVE_RANGE` cap (4000 world units) and a documented ray-count constant (180) rather than a profiled number — unmeasured at production scale, same "measure after deployment" posture prior slices already took for open perf questions.
9. **Permission boundary**: DM bypasses Fog of War entirely (same source as decision 4).
10. **Darkness behavior**: a `light_type="darkness"` source excludes any cell within its radius from visibility outright, regardless of what other lights would otherwise illuminate it — a flat exclusion zone, not Foundry's priority-based blending; emission angle is not modeled (explicit non-goal).

Data model: `SceneWall`/`SceneLight` keyed to `CampaignMap` (not `SceneLayer`) — walls/lights are geometry belonging to the map asset itself, the same anchor `TokenState.map_id` already uses, not to a session's particular arrangement of layers around that map. `FogOfWarState` keyed to `(user_id, campaign_map_id)`. `TokenState.sight_range` added (NULL = unlimited natural sight, still wall-blocked). Migration `migrations/migration_m71_vision_fog_of_war.sql`. `CampaignMap.fog_enabled` — a column that already existed, unused, since before this slice — is the real on/off switch: recalculation is a no-op on any map where it's false, so walls/lights can be placed and previewed either way but Fog of War itself only persists once a DM turns it on.

Backend: `vtt/play/vision.py` (pure geometry, no Flask/DB dependency, so it's independently unit-tested — 11 tests in `tests/test_vision_engine.py`); `recalculate_fog_for_owner`/`recalculate_fog_for_all_owners` in `vtt/play/service.py`, unioning vision across every token a player owns on a map (not just whichever one moved, so a two-token owner's fog doesn't flicker down to one token's view every time only the other moves); 11 new REST endpoints under `/vision/` in `vtt/play/routes.py` (walls/lights CRUD, fog GET, destructive fog/reset, and a DM-only `tokens/<id>/visible` debug endpoint matching the AC's "read-only verification tool" ask); recalculation wired into both the `token:update` socket handler and its REST fallback (`campaigns/routes.py::update_token`) whenever `x`/`y`/`sight_range` changes. Drive-by fix while touching the REST token-patch allowlist: it had silently drifted out of sync with the socket handler's own allowlist since S09 (`is_loot_source` was DM-writable over the socket but rejected over REST) — folded back in sync. 12 integration tests in `tests/test_playtable_vision_fog.py` cover DM-only permission boundaries, per-user fog isolation (a player can never read another user's fog row, confirmed a `fog:updated` broadcast never reaches the DM room or another player), the destructive reset's confirm-required + audit-chat-message contract, and that a real token move over the socket actually persists fog end to end (not just that the underlying math is correct).

Client: wall/light markers render as plain SVG lines/circles on a new `#visionLayer` (explicitly NOT the fog-of-war shadow/mask overlay, which stays deferred per the research doc's own non-goal) — a materially smaller, distinct thing satisfying the AC's "DM places a light and sees its position" without building a canvas vision-rendering pipeline this slice. Two new DM-only tool-rail buttons (wall/light placement) plus an all-roles "Sicht" toggle for the marker layer (mobile-safe, client-only, mutates nothing — same read-only-friendly posture as the S03 measure tool). Token panel gained an owner-or-DM-editable `sight_range` field and a DM-only "Sichtbare Tokens" verification popover. DM-only session-wide Fog of War toggle + destructive reset (two-step native-confirm, matching the S05 clear-all-conditions convention) live in the Turn Order widget alongside the other DM session controls.

Two real bugs the `vision_fog` robot flow caught (added to the fleet, now 14 flows), neither found by inspection:

1. **A light's glow radius blocked every click underneath it.** `.vision-light-marker` had `pointer-events: fill` on the whole group, so the large semi-transparent bright/dim rings (which can span a big fraction of a map) intercepted clicks meant for wall placement, token selection, or panning anywhere within their radius — not just clicks on the light itself. Fixed by moving `pointer-events: fill` down to only the small 5px center dot; the rings are purely decorative now.
2. **The destructive fog-reset button lived inside a widget that resets to collapsed on reload**, discovered only because the robot flow's own reload-to-verify-persistence step (mirroring the same pattern S09 already established for `is_loot_source`) then couldn't reach the button — not a product bug, but confirmed the Turn Order widget's default-collapsed behavior is real and any flow (robot or human) reaching DM session controls needs to expand it first.

A third finding was a pure robot-flow authoring mistake worth recording since it'll recur: an SVG `<line>` between two points sharing a coordinate (e.g., both at the same y) has a zero-height geometric bounding box and fails Playwright's default "visible" wait even though the stroke renders correctly on screen — wall-placement test coordinates must be genuinely diagonal, not just "two different points."

Verification: full pytest suite re-verified at 549 passed, 0 failed (23 new tests over S09's 526: 11 in test_vision_engine.py, 12 in test_playtable_vision_fog.py); full robot fleet re-run end to end after both fixes: 14 flows, 0 findings. Explicitly NOT built this slice, matching the research doc's own non-goals: fog-of-war mask/shadow rendering, a freehand wall-draw tool, multilevel/height-based vision, dynamic light-color blending, darkness emission angles, and cross-scene vision persistence beyond the per-(user, map) fog row.

Next: slice 11 (Quality, cross-cutting, last).

## Slice 11 (Quality) — Apply decisions and Deploy status: DONE, 2026-08-28

Cross-cutting by nature (the research doc frames it as ~40 acceptance-criteria cells applying to all 10 prior slices at once), so scoping it the way S01–S09 scoped their own Apply decisions -- narrow to what a current-state check actually confirmed as a real, concrete gap, not the full test matrix. A quick audit against the doc's own §2 claims found several were already substantially addressed by earlier slices' incidental work (`prefers-reduced-motion` already existed for the entry/exit curtains and tool buttons; `touch-action: none` already existed on token markers; the S04 reconnect banner already covers the doc's "graceful reconnection" ask) -- fixed only what was genuinely still missing:

1. **The app-wide error/success toast could be structurally invisible.** `#msg` -- the element every `_showMessage()` call targets, from every slice's error paths -- lived inside `#panel-session`, one sidebar tab among several (`.tab-panel { display: none }` unless active). An error fired while any other tab was open, or the sidebar closed on mobile, landed inside a `display:none` ancestor and was never seen — a real, previously-undetected bug (not just an AC gap), most likely unnoticed because prior slices' robot flows check `session.findings` for server/console errors, not toast visibility, and error paths get proportionally less UI-click coverage than golden paths. Fixed by moving `#msg` to a body-level fixed-position toast (same `id`, so `_showMessage()` needed no JS change beyond the aria-live wiring below) — `#readOnlyNotice`/`#firstStepsNotice` keep the shared `.message` class and stay inline, only `#msg` got the ID-specific fixed-position override.
2. **No live region on that toast at all.** Added `role="status"` + `aria-live`, toggled between `polite` (success) and `assertive` (error) per the research doc's own recommendation #4 (assertive interrupts screen-reader reading, warranted for failures, not routine confirmations).
3. **No focus trap in any popover.** Added one shared `_bindFocusTrap(container)` in `play-ui.js` (research doc's own recommendation #1: hand-coded, not a library dependency in a vanilla-JS stack) and wired it into every `role="dialog"` popover this app has: conditions, loot, wall-edit, light-edit, visible-tokens. Deliberately NOT wired into the app menu (`role="menu"`) — it already implements its own correct arrow-key roving-focus navigation per the W3C APG Menu Button Pattern (one of the research doc's own cited sources); a generic Tab-trap there would be a regression against that pattern, not a fix, since a menu's Tab behavior is supposed to differ from a dialog's.
4. **`prefers-reduced-motion` coverage was curated, not exhaustive.** The existing rule enumerated specific selectors from when it was written, predating several later slices' own transitions (popovers, the sidebar dodge rule, widget dragging). Added a global `*, *::before, *::after { transition-duration: 0.001ms !important; animation-duration: 0.001ms !important; ... }` fallback alongside the existing curated list (kept, not replaced, so the original's intent-documentation isn't lost) — near-zero duration rather than `transition: none` so any future `transitionend`-driven code (none exists today) keeps firing.
5. **Widget drag handles had no `touch-action`.** `.floating h3.widget-drag-handle` (the draggable header `_bindWidgetDragging` already uses) had nothing preventing a touch-drag from fighting the browser's default pan/scroll on the same surface — same class of fix `#mapViewport`'s tokens already had via their own `touch-action: none`.

Explicitly descoped (Apply decision, same posture prior slices used for open-ended items): a full pending-action queue with reconnect-replay and duplicate detection — the doc's own §8 already calls this a "future slice," and building it now would be a real architecture commitment (which actions are safely replayable, what "duplicate" means per action type) rather than implementation detail; formal performance profiling/optimization — no production telemetry exists yet to profile against, same "measure after deployment" posture used for S10's unmeasured raycasting performance; custom gesture recognition and aria-label i18n — both explicit non-goals in the doc's own §8.

Verification: a new `quality` robot flow (added to the fleet, now 15) drives all three fixed behaviors through the real browser rather than just asserting CSS exists — creates a browser context with `reduced_motion="reduce"` and confirms `.tool-btn`'s computed `transition-duration` actually collapsed (not just that the media query matches), switches to the Tools tab (deliberately not Session, where `#msg` used to live) and confirms a real client-side validation error's toast is visible there with `aria-live="assertive"`, and opens the conditions popover, moves focus to its last focusable element, presses Tab once more, and confirms focus wrapped back to the first element instead of escaping into the page. 0 findings on first run and on a stability re-run. Caught one own mistake along the way: a doc comment inside play.html literally contained the text `<body>` while explaining the #msg relocation, which a pre-existing formal-cleanliness contract test (`test_play_template_remains_formally_clean_after_boundary_chain_changes`, a naive `.count("<body")` on the raw template) correctly flagged as a second body tag — reworded the comment, not a real structural issue. Full pytest suite re-verified at 549 passed, 0 failed (unchanged from S10 — this slice added a robot flow, not pytest tests); full 15-flow robot fleet (incl. the new `quality` flow) re-run end to end: 15 flows, 0 findings.

This closes the Foundry-parity playtable work package: all 11 slices (Scenes, App Menu, Map Tools, Token HUD, Statuses, Combat, Hotbar, Roll/Chat, Loot, Vision/Fog of War, Quality) are DONE and deployed to vtt.roll-drauf.de.
