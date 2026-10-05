# Roll20 GitHub → Roll-Drauf VTT translation research

**Datum:** 2026-08-31  
**Phase:** Discover  
**Status:** complete  
**Scope:** Public repositories under the [Roll20 GitHub organization](https://github.com/Roll20), with emphasis on character sheets, API scripts, Beacon SDK patterns, realtime/media examples, and safe translation into the local Roll-Drauf VTT.  
**Method:** Read-only inspection of public first-party repository pages, raw source files, repository metadata, and the local VTT. No application or deployment code was changed.

## Kurzfazit

The organization link is valuable, but it is not a leak of Roll20's core tabletop engine. The public organization listing contains 36 repositories, mostly community extensions, SDK examples, documentation, old infrastructure forks, and generic libraries. I found no public monolithic Roll20 application repository in that listing; that absence is an observation about the public surface, not proof about Roll20's private architecture.

The highest-value material for Roll-Drauf is:

1. **Character-sheet packaging:** a manifest, isolated sheet assets, translations, previews, and contribution checks.
2. **API-script packaging:** an explicit manifest for commands, versions, dependencies, conflicts, affected data, and user options.
3. **Beacon's relay contract:** separate handlers, actions, computed values, fallbacks, rolls, and a dispatch object.
4. **Capability boundaries:** privileged operations are exposed through a narrow host/worker contract rather than arbitrary browser code.
5. **Community release discipline:** JSON Schema validation, CI, human-readable help, changelogs, and stable update paths.

These are patterns to translate, not code to transplant. The local VTT already has compatible seams: an action catalog, server-owned token visibility, versioned session state, explicit Socket.IO events and resync, character JSON data, chat/roll surfaces, and editable page content.

## Public repository inventory

The organization page reports 36 public repositories. The repository metadata separates the useful product-facing repositories from historical or generic material:

| Repository | What it actually exposes | Relevance |
|---|---|---|
| [`roll20-character-sheets`](https://github.com/Roll20/roll20-character-sheets) | 800+ community sheets, mostly HTML/CSS plus metadata, translations, previews, and CI | **High** — content/module packaging and localization |
| [`roll20-api-scripts`](https://github.com/Roll20/roll20-api-scripts) | Community JavaScript scripts with `script.json`, schema validation, docs, and conventions | **High** — bounded action/module registry |
| [`roll20-beacon-sheets`](https://github.com/Roll20/roll20-beacon-sheets) | Quickstart and advanced Vue/TypeScript Beacon sheet examples | **High conceptually; license review required** |
| [`beacon-docs`](https://github.com/Roll20/beacon-docs) | Public documentation for `initRelay`, handlers, actions, computed values, dispatch, rolls, fallbacks, and Mod API integration | **High** — clean contract vocabulary |
| [`vtt-activity-example`](https://github.com/Roll20/vtt-activity-example) | Tiny Vue/Vite starter using Discord Activity iframe SDK and Firebase | **Low/conditional** — only relevant if we pursue an embedded Discord Activity |
| [`webrtc-server`](https://github.com/Roll20/webrtc-server) | An old WebRTC demo server README and example | **Low** — not a modern VTT architecture reference |
| [`simple-peer`](https://github.com/Roll20/simple-peer), [`peerjs-server`](https://github.com/Roll20/peerjs-server), [`mediasoup-sandbox`](https://github.com/Roll20/mediasoup-sandbox) | Forks, demos, or experiments around media/data channels | **Low/conditional** — investigate only for future voice/video |
| [`Canvas-Txt`](https://github.com/Roll20/Canvas-Txt), [`detect-gpu`](https://github.com/Roll20/detect-gpu) | Generic rendering/performance utilities, both forks | **Low** — isolated implementation references |
| Ruby/DataMapper, storage, routing, and UI repos | Historical infrastructure or vendored/generic dependencies | **Reference only** |

## Source-backed patterns worth translating

### 1. Treat character sheets as versioned modules, not template fragments

The legacy character-sheet repository requires a small package boundary: HTML, CSS, preview image, and `sheet.json` metadata. The README also documents repeating sections, roll buttons, roll templates, sheet workers, supported branches, weekly review cadence, translations, and MIT licensing for the sheet code. See the [character-sheet contribution guide](https://github.com/Roll20/roll20-character-sheets/blob/master/README.md).

**Translation candidate for Roll-Drauf:** define a sheet/module manifest around the existing `Character` model and `character_data` JSON. The manifest could describe:

- system identifier and display name;
- persisted fields and derived fields;
- available player/DM actions;
- chat/roll presentation hooks;
- supported locales and preview metadata;
- compatibility/migration version.

This is a candidate for the Apply phase, not a decision to add a plugin runtime. The immediate value is a stable boundary for a Roll-Drauf sheet without coupling every new rule-system field to `vtt/models/character.py`.

### 2. Make actions explicit and inspectable

The API-script repository requires `script.json` metadata for name, script entry point, current and previous versions, description, authors, user options, dependencies, modified data, and conflicts. It validates the manifest against [`script.json.schema`](https://github.com/Roll20/roll20-api-scripts/blob/master/script.json.schema). The repository also recommends namespaces, small footprints, explicit enable/disable behavior, readable help, and player-level controls; see the [API-script README](https://github.com/Roll20/roll20-api-scripts/blob/master/README.md). [`TokenMod`](https://github.com/Roll20/roll20-api-scripts/blob/master/TokenMod/script.json) is a concrete example of a configurable token action, while [`GroupInitiative`](https://github.com/Roll20/roll20-api-scripts/blob/master/GroupInitiative/script.json) shows a system-aware initiative action.

**Translation candidate for Roll-Drauf:** evolve the existing [`ACTION_CATALOG`](../vtt/play/actions.py#L8) into a contract that carries permission scope, input schema, target requirements, suggested roll, visibility, idempotency behavior, and audit label. Keep execution server-side. Do not expose arbitrary Python or JavaScript as a user-installed script.

### 3. Separate lifecycle events, actions, computed values, and dispatch

Beacon's public contract is unusually useful as vocabulary. [`initRelay`](https://github.com/Roll20/beacon-docs/blob/main/content/docs/components/InitRelay.md) groups handlers, actions, computed values, and legacy fallbacks. Handlers cover initial load, data changes, settings changes, translations, and drag/drop. Actions are callable operations. Computed values are derived properties that can be exposed to macros or token bars. [`dispatch`](https://github.com/Roll20/beacon-docs/blob/main/content/docs/components/dispatch.md) is the host-facing command surface for updates, rolls, chat, character queries, tokens, initiative, and macros.

**Translation candidate for Roll-Drauf:** preserve the same separation across the current Flask/Socket.IO boundary:

| Beacon idea | Existing Roll-Drauf evidence | Candidate translation |
|---|---|---|
| `onInit` / `onChange` | [`play-client.js`](../vtt/static/js/play-client.js#L6) bootstrap and [`play-socket.js`](../vtt/static/js/play-socket.js#L1) state events | Explicit bootstrap, delta, settings, and resync event names |
| Actions | [`vtt/play/actions.py`](../vtt/play/actions.py#L8) and `executeAction` client path | Server-validated action registry and operation envelopes |
| Computed values | [`Character.serialize`](../vtt/models/character.py#L115) and server state serializers | Named derived read surfaces; never trust client-computed secrets |
| Dispatch | [`PlayClient`](../vtt/static/js/play-client.js#L1) and Socket.IO event methods | One documented client command adapter over HTTP + Socket.IO |
| Roll + post | [`vtt/dice.py`](../vtt/dice.py#L1), chat events, external-roll bridge | Separate deterministic roll result from chat projection, with visibility metadata |
| Token/initiative operations | [`TokenState`](../vtt/models/token_state.py#L1), combat service, initiative model | Bulk/token-linked operations with permission and version checks |

The useful lesson is the boundary, not the Beacon API names. Roll-Drauf should remain Flask/vanilla-JS/Socket.IO unless a separate Apply decision shows that a frontend migration is justified.

### 4. Keep privileged capabilities behind a narrow boundary

Beacon's Mod API documentation says sheet actions and computed values can be exposed to scripts through a separate `worker.js`, which runs in cloud VMs without browser DOM globals. The documented restriction is deliberate: only relay/action/computed/handler code belongs in the worker; browser-only objects such as `window` and `document` must not be available there. See [Mod API Integration](https://github.com/Roll20/beacon-docs/blob/main/content/docs/components/modApi.md).

**Translation candidate for Roll-Drauf:** if we ever allow community actions or system modules, define a capability allowlist and execution boundary first. A module should receive a typed operation context and return a result; it should not receive database handles, Flask request objects, JWTs, or unrestricted server access. This aligns with the existing server-side visibility rule in [`vtt/play/service.py`](../vtt/play/service.py#L221), which correctly treats client filtering as presentation rather than authorization.

### 5. Use fallbacks for migration, not permanent ambiguity

Beacon documents fallback handlers for attributes, roll templates, and action names that are missing from a new sheet, especially during migration from an older sheet. See [fallbacks](https://github.com/Roll20/beacon-docs/blob/main/content/docs/components/fallbacks.md).

**Translation candidate for Roll-Drauf:** use an explicit compatibility layer when the current flexible `character_data` shape evolves. Migrations should map old field names and action identifiers to canonical names, emit audit information, and have a removal/version policy. Avoid scattering `old_name or new_name` checks across templates and routes.

### 6. Make roll results a structured product surface

Beacon's [roll contract](https://github.com/Roll20/beacon-docs/blob/main/content/docs/components/roll.md) returns named roll results, original expressions, dice details, totals, and a message identifier. It also separates rolling from posting to chat and supports roll buttons/actions.

**Translation candidate for Roll-Drauf:** the current [`roll_dice`](../vtt/dice.py#L5) result is intentionally small and useful for the MVP, but the next contract should distinguish formula, individual dice, modifier, total, actor, visibility, action id, and chat message id. This would give the Beyond20 bridge, native rolls, action buttons, and audit logs one common result shape.

### 7. Treat translations and content as data with validation

The legacy sheet repo contains translation catalogs and locale files, including German, and explicitly directs contributors to Crowdin for translation management. A representative [German catalog](https://github.com/Roll20/roll20-character-sheets/blob/master/13th%20Age%20Glorantha/translations/de.json) demonstrates key-based translation rather than duplicating sheet markup.

**Translation candidate for Roll-Drauf:** build on the existing [`PageContent`](../vtt/models/page_content.py#L1) model and [`PAGE_CONTENT_RETRANSLATIONS`](../vtt/content_defaults.py#L225) compatibility pass, but distinguish:

- stable message keys;
- locale-specific values;
- editor-owned overrides;
- required placeholders;
- rendered-language smoke checks.

This is especially relevant because the current product is German-first and the repository already records rendered language leaks as a known risk.

### 8. Copy the release discipline, not the product stack

Roll20's public repositories use different stacks because they solve different problems: legacy HTML/CSS sheets, community JavaScript scripts, Beacon Vue/TypeScript sheets, and an old WebRTC demo. The [quickstart Beacon sheet](https://github.com/Roll20/roll20-beacon-sheets/tree/main/sheets/quickstart-example-sheet) explicitly uses Vue, Vite, SCSS, a mock relay for offline development, and a sandbox mode. The [advanced example](https://github.com/Roll20/roll20-beacon-sheets/tree/main/sheets/advanced-example-sheet) adds TypeScript, multiple stores, roll templates, unit tests, Cypress tests, and a CI check.

**Translation candidate for Roll-Drauf:** retain the existing Python CI and browser smoke, then add contract validation for any future sheet/action manifest. A module should be testable offline with a fake host/dispatch, while integration tests exercise the real permission and persistence boundary.

## What not to copy

- **No core-engine assumptions:** public repositories do not reveal Roll20's campaign/session storage, authorization model, rendering engine, or production deployment topology.
- **No arbitrary script execution:** the community-script model is useful as a registry and documentation pattern, not as permission to run third-party code inside the Flask process.
- **No blind Beacon code copy:** `roll20-beacon-sheets` has no obvious license file or SPDX license in the [repository metadata](https://api.github.com/repos/Roll20/roll20-beacon-sheets) inspected on 2026-08-31. Treat its code and assets as reference-only until separately cleared.
- **No automatic game-content reuse:** the character-sheet repository is MIT for sheet code, but its README separately discusses publisher approval for officially supported game sheets. Rules text, logos, art, fonts, and publisher assets remain separate rights questions.
- **No WebRTC detour yet:** the public [`webrtc-server`](https://github.com/Roll20/webrtc-server) is an old demo, and the public [`vtt-activity-example`](https://github.com/Roll20/vtt-activity-example) is a three-commit Vue/Firebase/Discord starter, not evidence that Roll-Drauf needs either stack.

## Local gap and opportunity summary

| Area | Current state | Discovery finding |
|---|---|---|
| Campaign/session workflow | Already has Roll20-oriented lobby and launch parity work; see [`docs/roll20-soll-ist-vergleich.md`](roll20-soll-ist-vergleich.md) and the approved [copy-first program](../dadm/artifacts/programs/milestone_program_roll20_copy_v1.md) | Continue product-flow parity separately from extension architecture |
| Character data | Fixed fields plus flexible `character_data` JSON | Good seed for a manifest/compatibility boundary; not yet a formal sheet registry |
| Play actions | Small catalog with target requirement and suggested roll | Closest existing seam for explicit action metadata |
| Realtime | Socket events, event sequencing, duplicate/stale handling, and resync are present | Good host/dispatch substrate; document the event contract before adding modules |
| Security | Token and combat payload visibility are filtered on the server | Preserve this as the non-negotiable boundary for any future module/action system |
| Localization | Editable page content and targeted retranslation exist; no general locale catalog is evident | Roll20's key/locale pattern is a useful next discovery topic |
| Validation | Python tests, browser smoke, dependency audit, and GitHub Actions exist | Add schema/manifest checks only when a module boundary is approved |

## Risks and assumptions

- **High — security:** arbitrary community code would create a server-side execution and data-isolation problem. Any extension system needs a capability model before implementation.
- **High — IP/licensing:** MIT notices are repository-specific. Beacon sheets have no obvious license metadata, and game-specific content can carry separate rights.
- **Medium — architecture:** introducing a module/manifest layer can compete with the existing `Character`, `ACTION_CATALOG`, and page-content surfaces. The next phase must define ownership and migration boundaries first.
- **Medium — contract drift:** Beacon is a public SDK documentation/example surface, not a promise that its API or design is stable for third-party reimplementation.
- **Low — stack mismatch:** Vue/Pinia/Vite examples may be useful for a future isolated sheet editor, but they do not map directly onto the current Flask templates and vanilla JavaScript runtime.

## Next step into Apply

Choose one bounded design slice: **a non-executable Roll-Drauf character-sheet/action manifest contract**. Define its schema, ownership, localization fields, compatibility rules, permission vocabulary, and test boundary using the existing character/action/play seams. Do not add third-party execution, Beacon code, or a frontend rewrite as part of that slice.

## Artifact retention

Retain this document as a living research/reference artifact. It records public-source observations and candidate translations; it is not an implementation approval or a license grant.
