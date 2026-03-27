# M7 Discover Output: Community and Moderation Workflows

```
artifact: discover-output
milestone: M7
phase: DISCOVER
status: complete
date: 2026-03-26
```

---

## Input Summary

- Prior milestone baseline:
  - `milestone_m6_deploy_output.md`
  - `milestone_m6_monitor_output.md`
- Runtime method:
  - `dadm-framework/runtime/AI_BIOS.md`
  - `dadm-framework/runtime/file-registry.yaml`
  - profile: `standard`
  - route card: `discover`
- M7 objective from plan:
  - Discover: chat/voice/moderation workflows
  - Apply: moderation and social feature design
  - Deploy: community tools and reporting

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m7_discover_output.md` | M7 current-state evidence and boundary definition | `immutable` after phase close | active draft in this turn |
| terminal evidence (commands, probes) | support evidence for discovery | `mutable` | not canonical |

---

## Current-State Summary

- Relevant: strong auth/session baseline exists (JWT cookie auth, CSRF, revocation-backed sessions with IP/user-agent metadata).
- Relevant: campaign membership and DM role checks exist and are used across REST/socket state mutations.
- Relevant: Socket.IO infrastructure is implemented with authenticated room joins (`campaign:{id}:session:{id}`) and membership enforcement.
- Relevant: there is no dedicated community/moderation backend surface (no moderation/community blueprints, endpoints, or models).
- Relevant: there is no persisted chat domain (no chat message, channel, report, mute/ban, or moderation action models).
- Relevant: there is no voice/signaling stack (no WebRTC signaling endpoints/events, no TURN/STUN integration).
- Relevant: no community/moderation UI exists (`game.html`, chat panels, moderation console are missing).
- Relevant: tests currently cover auth/campaign/map/token/combat flows, but no moderation/reporting/chat policy tests.
- Not relevant for M7 Discover boundary: deep combat-rule expansion and production-infra hardening (M6/M8 concerns).

---

## Inventory

| # | Name | Description | Location | Status |
|---|---|---|---|---|
| I1 | Auth and session revocation | JWT cookie auth + CSRF + persisted session metadata | `vtt_app/auth/routes.py`, `vtt_app/models/session.py` | present |
| I2 | Role model | `Player`, `DM`, `Admin` roles exist at data level | `vtt_app/models/role.py`, `vtt_app/models/user.py` | present |
| I3 | Campaign membership role boundary | campaign-level role and membership state (`invited/active/left/kicked`) | `vtt_app/models/campaign_member.py` | present |
| I4 | Room-scoped realtime transport | authenticated Socket.IO room join and state fanout | `vtt_app/socket_handlers.py` | present |
| I5 | HTTP rate limiting base | Flask-Limiter enabled (memory store) | `vtt_app/extensions.py`, `vtt_app/config.py` | present |
| I6 | Chat message persistence | per-session/campaign message storage model | `vtt_app/models/*` | missing |
| I7 | Chat REST/socket API | send/list/edit/delete message contracts | `vtt_app/*/routes.py`, `vtt_app/socket_handlers.py` | missing |
| I8 | Moderation domain model | reports, actions, mute/ban records, action history | `vtt_app/models/*` | missing |
| I9 | Moderation API surface | report submit/review/action endpoints | `vtt_app/*/routes.py` | missing |
| I10 | Voice signaling layer | session voice channel signaling/events | `vtt_app/*` | missing |
| I11 | Community/moderation UI | chat panel, report flow, moderation console | `vtt_app/templates/*` | missing |
| I12 | Moderation/community tests | automated policy and abuse-path validation | `tests/*` | missing |
| I13 | Legacy realtime module | old `api.py`/`sockets.py` implementation not wired into app factory | `vtt_app/api.py`, `vtt_app/sockets.py` | present (not integrated) |

---

## Dependencies

| # | Dependency | Version | Status |
|---|---|---|---|
| D1 | Flask | 2.3.3 | present |
| D2 | Flask-SocketIO | 5.3.6 | present |
| D3 | python-socketio | 5.8.0 | present |
| D4 | Flask-JWT-Extended | 4.5.2 | present |
| D5 | Flask-Limiter | 3.5.0 | present |
| D6 | Existing room/auth session model from M5/M6 | current codebase | present |
| D7 | WebRTC signaling/voice dependency stack | not configured | missing |
| D8 | Moderation policy/filtering service layer | not configured | missing |
| D9 | Migration tooling (Alembic/Flask-Migrate) | not configured | missing |

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | No chat/moderation persistence means no evidence trail for abuse handling or report resolution. | `high` | yes |
| R2 | No moderation action model/API means no enforceable mute/ban/report workflows. | `high` | yes |
| R3 | `Admin` role exists but has no operational enforcement pathways in current route/socket layer. | `high` | yes |
| R4 | `dice_rolled` socket event still uses global broadcast, risking cross-session leakage of social events. | `medium` | yes |
| R5 | Rate limiter uses `memory://` storage, weakening abuse resistance across restarts/multi-process deployments. | `medium` | yes |
| R6 | No voice signaling architecture exists; enabling voice ad-hoc would create high complexity/risk quickly. | `medium` | yes |
| R7 | Legacy unused realtime modules can cause contract confusion if accidentally reintroduced. | `low` | no |

Assumption A1: M7 should extend existing authenticated room architecture rather than introduce parallel communication stacks.

Assumption A2: M7 MVP can prioritize text chat + reporting/moderation workflow before full voice capability.

---

## Open Questions

| # | Question | Priority | Owner |
|---|---|---|---|
| Q1 | Is M7 scope text-chat-first, or must voice signaling ship in the same milestone? | blocking | human |
| Q2 | What is the moderation authority model: campaign DM-only, global admin-only, or hybrid? | blocking | human |
| Q3 | Which moderation actions are mandatory for M7 MVP (mute, kick, ban, timeout, message delete)? | blocking | human + backend |
| Q4 | What reporting workflow is required (in-app report, evidence snapshot, triage states, appeal)? | blocking | human |
| Q5 | What message retention policy is required per campaign/session (TTL, delete rights, audit constraints)? | important | human |
| Q6 | Is content filtering/profanity detection required now, and if yes rule-based or service-backed? | important | human |
| Q7 | Should social events (dice/chat/system notices) be fully room-scoped with immutable audit IDs in M7? | important | human + backend |

---

## Next Step

Proceed to **M7 Apply** to design:

1. chat + moderation domain model (messages, reports, actions, audit),
2. role/authority enforcement matrix (DM/Admin/member capabilities),
3. REST + Socket.IO community contracts with room isolation and abuse controls,
4. MVP scope split for text chat vs voice signaling,
5. test strategy for moderation policy and abuse-path validation.
