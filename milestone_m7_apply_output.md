# M7 Apply Output: Community and Moderation Architecture Design

```
artifact: apply-output
milestone: M7
phase: APPLY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Discover baseline:
  - `milestone_m7_discover_output.md`
- Human approval:
  - `APPROVED: M7 Apply mit Empfehlungen`
- Constraints and method:
  - DAD-M runtime profile `standard`
  - Apply phase only: architecture, contracts, acceptance criteria (no implementation code)
  - Build on existing M6 auth/session/realtime baseline

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m7_apply_output.md` | M7 solution design baseline for Deploy | `immutable` after phase close | active draft in this turn |

---

## Recommended Decision Set (for M7 Deploy)

1. **Scope-first recommendation: text chat + report/moderation in M7, voice deferred to M7.1**  
   Voice remains planned via integration hooks/feature flag, but not required for M7 acceptance.

2. **Authority recommendation: hybrid moderation model (DM + Admin)**  
   Campaign DM/owner can moderate campaign/session activity; Admin handles escalations and override actions.

3. **Consistency recommendation: REST-authoritative writes, Socket.IO room fanout only**  
   Chat/report/moderation mutations go through REST; sockets broadcast resulting state changes to authorized rooms.

---

## Design Tradeoffs

| Topic | Option A | Option B | Selected | Reason |
|---|---|---|---|---|
| M7 scope | text+voice+moderation in one pass | text+moderation first, voice deferred | **B** | lower delivery risk, faster abuse-control coverage |
| Moderation authority | DM-only or Admin-only | hybrid DM+Admin | **B** | practical campaign autonomy plus escalation path |
| Write path | socket client writes | REST writes + socket broadcasts | **B** | one canonical auth/audit path, fewer race conditions |
| Message deletion | hard delete | soft-delete + audit action | **B** | preserves evidence for report resolution |
| Realtime distribution | global broadcasts | strict room-scoped events | **B** | closes cross-session leakage class |

---

## Solution Design

### 1) Architecture (target M7)

M7 introduces a dedicated community boundary:

- `community` blueprint:
  - chat read/write APIs
  - reporting endpoints
  - moderation action endpoints
- service layer:
  - `community/service.py` for validation, policy, idempotency, audit append, event fanout
  - `community/policy.py` for role/authority checks
- realtime:
  - reuse M5/M6 rooms for session-scoped fanout
  - add moderator room for report workflow visibility
- compatibility fix:
  - remove global social broadcasts (`dice_rolled`) and scope to campaign/session room

### 2) Data model design

#### A. `chat_messages` (new)

Purpose: persisted, auditable session chat timeline.

Fields:

- `id` (PK)
- `campaign_id` (FK -> campaigns.id, indexed)
- `game_session_id` (FK -> game_sessions.id, indexed)
- `author_user_id` (FK -> users.id, indexed)
- `content` (text, required)
- `content_type` (enum/string: `user`, `system`)
- `client_event_id` (string, nullable; idempotency token)
- `moderation_state` (enum/string: `visible`, `hidden_author`, `hidden_moderation`)
- `edited_at` (nullable datetime)
- `deleted_at` (nullable datetime)
- `deleted_by` (FK -> users.id, nullable)
- `created_at`, `updated_at`

Rules:

- unique idempotency guard on (`author_user_id`, `game_session_id`, `client_event_id`) when token present.
- soft-delete only in M7 (no physical delete).

#### B. `moderation_reports` (new)

Purpose: report intake and triage workflow.

Fields:

- `id` (PK)
- `campaign_id` (FK -> campaigns.id, indexed)
- `game_session_id` (FK -> game_sessions.id, nullable, indexed)
- `reporter_user_id` (FK -> users.id, indexed)
- `target_user_id` (FK -> users.id, nullable)
- `target_message_id` (FK -> chat_messages.id, nullable)
- `reason_code` (enum/string: `spam`, `abuse`, `harassment`, `other`)
- `description` (text, optional)
- `status` (enum/string: `open`, `in_review`, `resolved`, `rejected`)
- `priority` (enum/string: `low`, `medium`, `high`)
- `assigned_to_user_id` (FK -> users.id, nullable)
- `resolution_note` (text, nullable)
- `resolved_action_id` (FK -> moderation_actions.id, nullable)
- `created_at`, `updated_at`, `resolved_at`

#### C. `moderation_actions` (new)

Purpose: immutable action ledger + active sanction checks.

Fields:

- `id` (PK)
- `campaign_id` (FK -> campaigns.id, indexed)
- `game_session_id` (FK -> game_sessions.id, nullable, indexed)
- `action_type` (enum/string: `warn`, `mute`, `delete_message`, `kick`, `ban`)
- `actor_user_id` (FK -> users.id, indexed)
- `subject_user_id` (FK -> users.id, nullable, indexed)
- `subject_message_id` (FK -> chat_messages.id, nullable)
- `source_report_id` (FK -> moderation_reports.id, nullable)
- `reason` (text, optional)
- `starts_at` (datetime)
- `ends_at` (datetime, nullable)
- `is_active` (bool, default true)
- `revoked_at` (datetime, nullable)
- `revoked_by_user_id` (FK -> users.id, nullable)
- `created_at`

Rules:

- actions are append-only; revocation creates explicit metadata, not row replacement.
- active mute/ban checks derived from `is_active` + time window.

### 3) API interface design (M7)

All endpoints require cookie auth and campaign membership validation.

#### Chat API

1. `GET /api/campaigns/<campaign_id>/sessions/<session_id>/chat/messages`
- query: `limit` (default 50, max 200), `before_id` optional
- returns ordered message page + cursor metadata

2. `POST /api/campaigns/<campaign_id>/sessions/<session_id>/chat/messages`
- body:
  - `content`
  - `client_event_id` optional
- blocked when active mute applies

3. `PATCH /api/campaigns/<campaign_id>/sessions/<session_id>/chat/messages/<message_id>`
- author edit window: 5 minutes
- DM/Admin may edit to redact with moderation note

4. `DELETE /api/campaigns/<campaign_id>/sessions/<session_id>/chat/messages/<message_id>`
- author self-delete window: 5 minutes
- DM/Admin can soft-delete anytime

#### Reporting API

5. `POST /api/campaigns/<campaign_id>/sessions/<session_id>/reports`
- body:
  - `target_user_id` optional
  - `target_message_id` optional
  - `reason_code`
  - `description` optional
- creates `open` report and notifies moderator room

6. `GET /api/campaigns/<campaign_id>/reports`
- DM/Admin only
- query: `status`, `priority`, `limit`, `cursor`

7. `POST /api/campaigns/<campaign_id>/reports/<report_id>/assign`
- DM/Admin only
- body: `{ assigned_to_user_id }`

8. `POST /api/campaigns/<campaign_id>/reports/<report_id>/resolve`
- DM/Admin only
- body:
  - `resolution`: `resolved` or `rejected`
  - `resolution_note`
  - `action_id` optional

#### Moderation Action API

9. `POST /api/campaigns/<campaign_id>/moderation/actions`
- DM/Admin only
- body:
  - `action_type`
  - `subject_user_id` or `subject_message_id`
  - `reason` optional
  - `duration_minutes` optional (for mute)
  - `source_report_id` optional
- policy:
  - DM can: `warn`, `mute`, `delete_message`, `kick`
  - Admin can: all DM actions + `ban`

10. `GET /api/campaigns/<campaign_id>/moderation/actions`
- DM/Admin only
- query: `active=true|false`, `subject_user_id` optional

11. `POST /api/campaigns/<campaign_id>/moderation/actions/<action_id>/revoke`
- DM/Admin only (Admin override allowed)

### 4) Realtime contract design (M7)

Room model:

- member room: `campaign:{campaign_id}:session:{session_id}`
- mod room: `campaign:{campaign_id}:mods`

Client writes remain REST-only. Server pushes updates:

- `chat:message_created` `{ message }`
- `chat:message_updated` `{ message }`
- `chat:message_deleted` `{ message_id, moderation_state, deleted_at }`
- `moderation:action_applied` `{ action, report_id? }`
- `moderation:action_revoked` `{ action_id, revoked_at }`
- `moderation:report_created` `{ report }` (mods only)
- `moderation:report_updated` `{ report }` (mods only)
- `community:error` `{ code, message }`

Hard requirement:

- all emits must be campaign/session scoped (no global broadcasts).

### 5) Authorization and policy matrix

| Capability | Player | DM/Owner | Admin |
|---|---|---|---|
| read session chat | yes | yes | yes |
| send chat message | yes (if not muted) | yes | yes |
| edit/delete own message (windowed) | yes | yes | yes |
| delete/redact any message | no | yes | yes |
| create report | yes | yes | yes |
| view report queue | no | yes | yes |
| assign/resolve report | no | yes | yes |
| warn/mute/kick campaign member | no | yes | yes |
| ban member | no | no | yes |
| revoke moderation action | no | yes (same campaign) | yes (override) |

### 6) Abuse controls and resilience

- Rate limits:
  - chat post: 20/min/user/session
  - report create: 5/hour/user/campaign
  - moderation actions: 30/hour/moderator/campaign
- Input controls:
  - chat length 1..1000 chars
  - strict JSON schema validation for action/report payloads
  - store plain text and render escaped in frontend
- Idempotency:
  - support `client_event_id` for safe retries on unstable connections
- Audit:
  - all moderation actions and report transitions persisted
  - deleted messages remain as soft-deleted evidence rows

### 7) Voice strategy (deferred by recommendation)

M7 Deploy includes voice readiness hooks only:

- config flag: `VOICE_ENABLED` (default false)
- reserved room naming convention aligned with session rooms
- optional stub endpoint:
  - `GET /api/campaigns/<campaign_id>/sessions/<session_id>/voice/config`
  - returns disabled state unless feature flag is enabled

Full signaling/TURN rollout moves to M7.1 or M8 prep track.

### 8) Test strategy (M7 Deploy target)

New suites:

- `tests/test_chat_api.py`
  - pagination, post/edit/delete, mute enforcement, idempotent retries
- `tests/test_reports_api.py`
  - report creation, queue access control, resolve flow
- `tests/test_moderation_actions.py`
  - policy matrix (player denied, DM allowed subset, admin ban override)
- `tests/test_community_realtime.py`
  - room-scoped fanout for chat/mod events, no cross-session leakage

Regression suites to keep green:

- `tests/test_auth.py`
- `tests/test_campaigns.py`
- `tests/test_characters.py`
- `tests/test_combat_api.py`
- `tests/test_tokens_realtime.py`

---

## Acceptance Criteria (for M7 Deploy)

AC-M7-01: Session chat messages persist and can be paged by authenticated campaign members.  
AC-M7-02: Muted users receive `403` on chat post attempts while mute is active.  
AC-M7-03: Users can submit reports with message/user targets and triage metadata is persisted.  
AC-M7-04: DM/Admin can view and manage campaign report queue; players cannot.  
AC-M7-05: Moderation actions are persisted with actor/subject/timestamp/audit linkage.  
AC-M7-06: DM can apply warn/mute/kick/delete_message, but cannot apply `ban`.  
AC-M7-07: Admin can apply and revoke `ban` actions with campaign override capability.  
AC-M7-08: Chat/moderation realtime events are emitted only to authorized campaign/session rooms.  
AC-M7-09: Global broadcast leakage class is removed from social events (`dice_rolled` and community events).  
AC-M7-10: M7 suites and prior core regression suites pass in local `.venv`.

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Deferring full voice can be perceived as incomplete social feature coverage. | `medium` | accepted for M7 |
| R2 | Moderation policy disputes (DM vs Admin precedence) can create operational ambiguity if not documented in UI/help text. | `medium` | yes |
| R3 | `memory://` rate-limit backend remains weak for multi-process abuse resistance until later infra milestone. | `medium` | accepted for M7 |
| R4 | Without migration tooling, adding moderation tables increases schema rollout friction. | `low` | no |
| R5 | Existing legacy modules (`api.py`, `sockets.py`) can reintroduce old event patterns if not kept clearly deprecated. | `low` | no |

Assumption A1: M7 acceptance prioritizes moderation-grade chat safety over synchronous voice release.  
Assumption A2: Campaign-level moderation is the canonical scope; global trust/safety tooling remains a later expansion.

---

## Planned Deploy Artifacts

- `vtt_app/models/chat_message.py` (new)
- `vtt_app/models/moderation_report.py` (new)
- `vtt_app/models/moderation_action.py` (new)
- `vtt_app/models/__init__.py` (update imports)
- `vtt_app/community/__init__.py` (new)
- `vtt_app/community/routes.py` (new)
- `vtt_app/community/service.py` (new)
- `vtt_app/community/policy.py` (new)
- `vtt_app/__init__.py` (register community blueprint)
- `vtt_app/socket_handlers.py` (room-scoped community emits + remove global social broadcast)
- `vtt_app/templates/campaigns.html` (session chat panel + moderation controls)
- `vtt_app/static/js/auth.js` (optional helper extensions if needed)
- `vtt_app/static/js/community.js` (new; chat/report/moderation client layer)
- `tests/test_chat_api.py` (new)
- `tests/test_reports_api.py` (new)
- `tests/test_moderation_actions.py` (new)
- `tests/test_community_realtime.py` (new)
- `milestone_m7_deploy_output.md` (new)

---

## Next Step

Start **M7 Deploy** and implement the approved design in one pass:

1. add community/moderation persistence models and policy layer,
2. implement chat/report/moderation REST contracts,
3. add room-scoped realtime fanout and remove global social broadcasts,
4. integrate minimal campaign UI chat/mod controls,
5. execute M7 + regression suites and record deploy proof.
