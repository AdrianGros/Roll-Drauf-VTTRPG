# Claude research prompts — Roll-Drauf playtable

These prompts are for Claude Code in **Research/Discover only**. Each run must write exactly one feature note and must not modify production code, tests, configuration, assets, or deployment files.

## Shared instructions

Use this shared preamble with every feature prompt:

```text
You are the research agent for the Roll-Drauf VTT playtable.

This is a Research/Discover pass only. Do not modify production code, tests,
configuration, assets, deployment files, or existing research notes. Write only
the one target Markdown file named in this prompt. Do not commit or deploy.

Read AGENTS.md, docs/PLAYTABLE_FEATURE_WORK_PACKAGE_2026-08-27.md,
docs/PLAYTABLE_UI_RESEARCH_2026-08-27.md, and the relevant current source files.

Research behavior and technical constraints from primary sources first:
official product documentation, official APIs/source code, W3C standards,
MDN, or other first-party sources. Add a separate section called
"Community favorites" using community discussions/recommendations only as
qualitative opinion. Label community claims as anecdotal and do not treat them
as requirements. Cite every factual or externally sourced claim with a direct
URL.

Write the note with these sections:
1. Status and input summary
2. Current Roll-Drauf state and relevant file inventory
3. Web research and source-backed findings
4. Good examples
5. Bad examples and failure modes
6. Lessons learned
7. Community favorites (opinion/anecdotal evidence)
8. Roll-Drauf fit and explicit non-goals
9. Proposed interface/data/permission contracts
10. Risks and assumptions with severity labels
11. Acceptance criteria for desktop, mobile, keyboard, permissions,
    realtime updates, errors, and destructive actions
12. Apply handoff: decisions still needed before implementation

Do not implement any recommendation. Finish with the target file path, changed
files, sources used, and a short summary.
```

## Feature prompts

### 01 — scenes and active-page context

Target: `docs/PLAYTABLE_FEATURE_RESEARCH_01_SCENES_2026-08-27.md`

```text
Use the shared instructions. Research the scene/page directory and active-page
context. Compare compact scene navigation, full searchable directories,
thumbnails, active state, folders, context actions, page notes, and desktop vs
mobile presentation. Use official Foundry Scenes documentation/API and W3C/MDN
semantics for disclosure, list/tree navigation, menus, focus, and lazy-loaded
previews. Include at least two good examples, two bad/failure examples, and
community preferences. Ground the recommendation in the existing layersWidget,
scene_stack endpoints, thumbnails, active_layer_id, and mobile table sheet.
Do not implement code.
```

### 02 — Escape/application menu

Target: `docs/PLAYTABLE_FEATURE_RESEARCH_02_APP_MENU_2026-08-27.md`

```text
Use the shared instructions. Research application-level Escape/Menu surfaces
for a VTT: return to campaign/session lobby, leave-session confirmation, help,
shortcuts, settings, user management, reload/recovery, and role-specific
commands. Distinguish application commands from the workspace sidebar and token
menus. Use first-party product docs and W3C menu-button/dialog/focus guidance.
Compare safe vs unsafe navigation defaults and collect community favorites.
Ground the recommendation in btnBack, btnSidebarToggle, the current session
routes, and read-only/role state. Do not implement code.
```

### 03 — map tools and measurement

Target: `docs/PLAYTABLE_FEATURE_RESEARCH_03_MAP_TOOLS_2026-08-27.md`

```text
Use the shared instructions. Research a VTT map-tool rail: select, pan,
measure distance, ruler waypoints, cancel/remove waypoint, token placement,
targeting, drawings/templates, notes, and tooltips. Focus on mouse, touch, pen,
keyboard, pointer capture, snapping, cancellation, and keeping the map readable.
Use official VTT controls documentation plus W3C/MDN Pointer Events and
touch-action guidance. Include good and bad examples, community favorites, and
the exact gap between the current select/pan/token implementation and a safe
measurement tool. Do not implement code.
```

### 04 — selected-token HUD and creature focus

Target: `docs/PLAYTABLE_FEATURE_RESEARCH_04_TOKEN_HUD_2026-08-27.md`

```text
Use the shared instructions. Research the selected-token HUD and full
player-character/monster focus sheet. Cover portrait, name/type, HP, movement,
defense, vision, stats, proficiencies, immunities, resistances, languages,
features, actions, legendary actions, legendary resistance, limited-use values,
character sheet entry, and token context actions. Compare anchored HUDs,
drawers, dialogs, and hover/right-click behavior. Use official Foundry Token HUD
and Token documentation plus accessibility guidance. Ground the result in
selectedTokenId, tokenWidget, character_id, sheetDrawer, and the current token
fields. Do not implement code.
```

### 05 — conditions and status picker

Target: `docs/PLAYTABLE_FEATURE_RESEARCH_05_STATUSES_2026-08-27.md`

```text
Use the shared instructions. Research status/condition systems in VTTs: icon
catalogs, labels, active states, values/durations, grouping/search, clear-one,
clear-all, token overlays, player visibility, and synchronization. Use official
VTT documentation/APIs and W3C checkbox/toggle/disclosure guidance. Separate
system mechanics from visual conventions and capture community favorites and
complaints about dense status grids. Ground the recommendation in
metadata_json.conditions and the current count badge. Do not implement code.
```

### 06 — combat tracker and initiative strip

Target: `docs/PLAYTABLE_FEATURE_RESEARCH_06_COMBAT_2026-08-27.md`

```text
Use the shared instructions. Research combat/initiative UI: current turn,
rounds, party portraits, next actors, initiative editing, adding/removing
combatants, turn transitions, player vs DM controls, and mobile behavior. Use
official VTT documentation/API references and accessibility guidance for live
regions and focus. Compare compact strips, trackers, and overlays; include bad
examples and community favorites. Ground the recommendation in turnOrderWidget,
combat state, initiative events, and token initiative fields. Do not implement
code.
```

### 07 — personal action hotbar

Target: `docs/PLAYTABLE_FEATURE_RESEARCH_07_HOTBAR_2026-08-27.md`

```text
Use the shared instructions. Research personal VTT hotbars: numbered slots,
keyboard shortcuts, multiple pages, drag/drop, macros vs system actions,
token-specific bars, use counts/cooldowns, empty slots, ownership, and mobile
presentation. Use official Foundry Macro/Hotbar documentation and other
first-party VTT documentation where available. Include good/bad examples,
community favorites, and the smallest useful first slice for an action_catalog
with server-backed executeAction. Do not implement code.
```

### 08 — roll composer and chat dock

Target: `docs/PLAYTABLE_FEATURE_RESEARCH_08_ROLL_CHAT_2026-08-27.md`

```text
Use the shared instructions. Research compact chat/dice composers: message
input, die presets, formula input, modifiers, normal/advantage/disadvantage,
public/private GM/blind/self visibility, roll result expansion, chat history,
whispers, keyboard behavior, and mobile input. Use official VTT chat/dice docs,
W3C input/focus guidance, and MDN where relevant. Explicitly separate roll
mathematics from visibility policy. Ground the recommendation in chatInput,
btnSendChat, diceInput, btnRoll, socket roll events, and current chat history.
Do not implement code.
```

### 09 — loot transfer and inventory

Target: `docs/PLAYTABLE_FEATURE_RESEARCH_09_LOOT_2026-08-27.md`

```text
Use the shared instructions. Research safe VTT loot transfer: source tokens,
multi-selection, containers, recipient characters, party stash, item stacks,
quantity review, permission checks, ownership, atomic transactions, idempotency,
conflicts, audit/chat events, and undo/recovery. Use authoritative transaction,
inventory, and security sources where applicable; use VTT documentation and
community discussions for workflow preferences. Clearly distinguish facts from
game-design recommendations. Ground the gap analysis in InventoryItem,
character-owned inventory CRUD, TokenState.character_id, and the current single
token action executor. Do not implement code.
```

### 10 — lighting, vision, walls, and Fog of War

Target: `docs/PLAYTABLE_FEATURE_RESEARCH_10_VISION_2026-08-27.md`

```text
Use the shared instructions. Research VTT lighting and vision: walls, light and
darkness sources, token sight, line of sight, explored vs currently visible
areas, per-user/shared Fog of War, reset semantics, permissions, scene changes,
performance, and mobile behavior. Use official Foundry Lighting, Walls, Fog,
and Scene documentation/API plus browser rendering guidance. Include good and
bad examples, community favorites, and a staged minimum viable subsystem.
Ground the gap analysis in the current image/grid/token DOM map and the lack of
a vision backend. Treat Fog of War reset as a destructive scene-wide command.
Do not implement code.
```

### 11 — responsive/accessibility/realtime quality

Target: `docs/PLAYTABLE_FEATURE_RESEARCH_11_QUALITY_2026-08-27.md`

```text
Use the shared instructions. Research cross-cutting VTT quality: desktop/mobile
responsive surfaces, pointer and keyboard input, focus restoration, menus,
dialogs, live updates, optimistic state, conflicts, reduced motion, tooltips,
large token counts, map dragging performance, and offline/reconnect behavior.
Use W3C APG, WCAG-related primary guidance, MDN Pointer Events/touch-action/
requestAnimationFrame/ResizeObserver, and official browser performance docs.
Include good and bad examples, community favorites, measurable acceptance
criteria, and a test matrix for the other feature slices. Do not implement code.
```

## Handoff format Claude must return

```text
Completed: <target file>
Changed files: <exact list>
Production code changed: no
Tests run: <or none, with reason>
Sources: <primary sources and community sources>
Risks: <severity-labelled unresolved items>
Apply handoff: <the next design decision>
```
