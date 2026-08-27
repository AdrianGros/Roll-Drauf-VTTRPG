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
