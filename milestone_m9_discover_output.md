# M9 Discover Output: Session Runtime and Play Environment

```
artifact: discover-output
milestone: M9
phase: DISCOVER
status: complete
date: 2026-03-26
```

---

## Input Summary

- Human-provided consolidated decision baseline:
  - `M9 Discover - konsolidierter Entscheidungsstand` (chat input)
- Existing project baseline:
  - M4-M8 artifacts (campaign/session/state/combat/community/ops)
  - current route/UI surface in `campaigns.html`, `lobby.html`, `campaigns/routes.py`, `socket_handlers.py`
- Focus:
  - transition from lobby into actual playable session environment
  - formal decision log, MVP split, and licensing first pass

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m9_discover_output.md` | Consolidated decision log + MVP boundary + licensing baseline | `immutable` after phase close | active draft in this turn |

---

## Current-State Summary

- Relevant: campaign/session lifecycle APIs exist (`create`, `start`, `end`) and are test-backed.
- Relevant: persisted session state, map activation, token state, combat state, and community chat/reporting exist.
- Relevant: realtime room model exists (`session:join`, `state:snapshot`, `token:*`, `map:activate`, `combat:*`).
- Relevant: UI is still campaign-centric; no dedicated `/play` experience bound to a selected session.
- Relevant: legacy map canvas UI (`index.html` + `src/main.js`) is not integrated with modern auth/session/campaign contracts.
- Core gap: the end-to-end "lobby -> waiting room -> live play -> end" flow is not yet a cohesive product path.

---

## A) Decision Log (Consolidated)

| ID | Decision | Architecture Consequence | Primary Risk |
|---|---|---|---|
| D1 | Dedicated `/play` route | clean split between management and live runtime | extra route/state integration |
| D2 | Session start rights = DM + Co-DM | session-level RBAC is mandatory | Discord-role vs app-role drift |
| D3 | Ready-check as soft checklist | warning-based preflight validation layer | critical warnings ignored |
| D4 | Pre-start waiting room (read-only) | explicit pre-live access mode and gating | permission edge cases |
| D5 | Scene Stack / Layer is first-class | shift from single-map to stack/layer model | render/sync complexity |
| D6 | Scene switching is first-class UX | player/DM scene sync controls required | desync and confusion |
| D7 | Combat on-demand | combat is optional sub-state of live session | low discoverability |
| D8 | Tokens are gameplay objects | token schema includes HP/stats/resources/action hooks | model complexity growth |
| D9 | One action system | unified action DSL and action bar | UX debt if schema is weak |
| D10 | Dice stay visible/manual | keep explicit roll loop with assistive UX | too little automation |
| D11 | Discord is identity bridge | OAuth + role mapping + session access bridge | external dependency risk |
| D12 | Session is first-class entity | dedicated lifecycle/state machine/storage | migration and invariants |
| D13 | Start snapshot semantics | deterministic baseline and recap/replay hooks | storage/version growth |
| D14 | Multi-scene preload support | asset lifecycle and preload strategy | memory/performance pressure |
| D15 | Safe reconnect/rejoin | authoritative resync protocol required | stale-client desync |
| D16 | Observer/Spectator role | additional permission tier | visibility leakage risks |
| D17 | Hybrid realtime/event model | sockets for live critical actions, event/log for rest | split-brain paths |
| D18 | Desktop-first + second-screen | prioritize dense desktop UX | reduced mobile quality |
| D19 | Persistent DM cockpit | fixed high-signal operator zones | cognitive overload |
| D20 | M10 scope = vertical slice | strict MVP boundary before platform expansion | vision pressure vs delivery |

---

## B) Product Scope Split

### MVP / Vertical Slice (M10 target)

- dedicated `/play` route with authenticated session entry
- session state machine:
  - `scheduled`, `ready`, `in_progress`, `paused`, `ended`
- waiting room:
  - pre-start read-only player access
- minimal scene stack:
  - one `SceneStack` with 2-3 switchable layers/floors
- live core:
  - token placement/movement and HP visibility
  - one unified action bar (basic actions only)
  - explicit dice roll UX
- DM/Co-DM controls:
  - start/pause/end session, switch scene layer
- end flow:
  - snapshot + recap artifact

### Phase 2

- deeper combat automation
- richer action/resource logic
- preload/streaming optimization
- observer enhancements and replay tools
- stronger Discord bot orchestration

### Long-Term Vision

- all-in-one VTT-RPG ecosystem (community + monetization + creator loops)
- configurable system/content packs on top of runtime engine
- advanced cross-session analytics and progression memory

---

## C) Domain Model v0 (Discover Draft)

- `User`
- `Membership`
- `Campaign`
- `Session`
- `SessionRole`
- `SessionSnapshot`
- `SceneStack`
- `SceneLayer`
- `Token`
- `CharacterSheet`
- `ActionDefinition`
- `ActionExecution`
- `ResourcePool`
- `Handout`
- `SessionEventLog`
- `DiscordIdentityLink`
- `AccessGrant`

---

## D) Live-Flow v0 (Discover Draft)

1. DM/Co-DM creates session (`scheduled`).
2. Ready-check runs (soft warnings, optional hard blockers).
3. Players enter waiting room (read-only pre-start).
4. DM/Co-DM starts session (`in_progress`) and baseline snapshot is created.
5. Players enter `/play`, join realtime room, receive authoritative snapshot.
6. Live loop runs (scene/layer switch, token interactions, actions, dice, combat on-demand).
7. Pause/resume as needed.
8. Session ends (`ended`) and final snapshot/recap is stored.
9. Safe reconnect path is available throughout live states.

---

## Licensing (Initial Risk Assessment, Not Legal Advice)

### Preliminary findings (official-source aligned)

- SRD 5.1 and SRD 5.2 are available under CC BY 4.0; official communication positions new SRD releases on Creative Commons.
- Wizards explicitly states SRD content can be used in VTT contexts.
- Wizards also states selected classes/species/monsters and names are excluded from SRD for IP reasons.
- CC BY 4.0 allows broad reuse but requires attribution and does not grant trademark rights.
- OGL 1.0a remains documented for SRD 5.1, but current direction favors CC for modern SRD use.

### Working interpretation for architecture

- safest starting path:
  - engine-first implementation with SRD-only content layer
  - strict content abstraction (no non-SRD hardcoding in runtime core)
- highest-risk zones:
  - copying non-SRD text/content from paid books
  - using protected names/identity content outside permitted scope
  - mixing branded lore with platform-native content without legal clearance

### Recommendation for M10

- proceed with SRD-compatible generic action/content model
- keep content packs separated from runtime engine
- get formal legal review before shipping non-SRD branded content or monetized packs

### Primary sources used

- D&D Beyond SRD hub:
  - https://www.dndbeyond.com/srd
- D&D Beyond OGL/CC announcement:
  - https://www.dndbeyond.com/posts/1439-ogl-1-0a-creative-commons
- SRD 5.1 OGL PDF:
  - https://media.dndbeyond.com/compendium-images/srd/5.1/SRD-OGL_V5.1.pdf
- Creative Commons BY 4.0 legal code:
  - https://creativecommons.org/licenses/by/4.0/legalcode

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Scene-stack design can over-expand M10 if not constrained to vertical slice. | `high` | yes |
| R2 | Session RBAC (DM/Co-DM/Observer) increases auth complexity across REST + Socket paths. | `high` | yes |
| R3 | `/play` introduction may duplicate legacy flow unless deprecation path is explicit. | `medium` | yes |
| R4 | Licensing misuse risk if non-SRD content is embedded too early. | `high` | yes |
| R5 | Existing technical-debt warnings may hide true regressions during rapid M10 changes. | `medium` | no |

Assumption A1: M10 prioritizes a playable vertical slice over full rules completeness.  
Assumption A2: Legal sign-off for non-SRD branded expansion is a gated track.

---

## Next Step

Proceed to **M10 Apply** with strict vertical-slice planning:

1. define `/play` architecture and session-entry contract,
2. formalize session state machine and waiting-room permissions,
3. define minimal `SceneStack/SceneLayer` runtime contract,
4. define action-bar v1 and token gameplay schema boundaries,
5. lock SRD-safe content boundary for first implementation.
