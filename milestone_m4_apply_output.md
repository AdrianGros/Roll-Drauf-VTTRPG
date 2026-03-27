# M4 Apply Output: Campaign and Session Core Loop Delta Design

```
artifact: apply-output
milestone: M4
phase: APPLY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Closed Discover baseline:
  - `milestone_m4_discover_output.md`
- Human approval decisions for Apply scope:
  1. M4 delivers full 12-endpoint contract.
  2. Campaign/session realtime Socket.IO events deferred to M5.
  3. M4 must remove UI action placeholders for core flows.
- Constraints and method:
  - DAD-M runtime profile `standard`
  - Apply phase only: design, interfaces, acceptance criteria (no implementation code)

---

## Artifacts

| Artifact | Purpose | Retention class | State |
|---|---|---|---|
| `milestone_m4_apply_output.md` | M4 solution design baseline for Deploy | `immutable` after phase close | active draft in this turn |

---

## Solution Design

### 1. Architecture overview (delta from current state)

M4 Deploy will complete one coherent backend+frontend loop:

- Backend:
  - Expand `campaigns` blueprint to full 12-endpoint surface.
  - Keep cookie auth and role checks as enforcement source of truth.
  - Keep campaign/session state in DB (no in-memory campaign state).
- Frontend:
  - Wire campaigns and lobby pages to real API actions (remove alert placeholders for core actions).
  - Keep route model simple: list view + actionable campaign/session controls.
- Realtime:
  - No new campaign/session socket event contracts in M4.
  - M5 will introduce realtime campaign orchestration if still required.

Component responsibilities:

- `vtt_app/campaigns/routes.py`
  - Campaign CRUD + membership + session lifecycle APIs.
- `vtt_app/models/*`
  - Persistence and domain state.
- `vtt_app/templates/campaigns.html` and `vtt_app/templates/lobby.html`
  - User-facing campaign/session control flows.
- `vtt_app/static/js/auth.js`
  - Cookie-session auth helper only (already in place, reused).

### 2. Interface definitions (12-endpoint contract)

#### Campaign CRUD

1. `POST /api/campaigns`
- Auth: required
- Input: `{ name, description?, max_players? }`
- Output `201`: campaign object
- Rules: creator becomes owner and active DM member

2. `GET /api/campaigns/<campaign_id>`
- Auth: required
- Output `200`: campaign details + member/session summary
- Rules: requester must be active member

3. `GET /api/campaigns/mine`
- Auth: required
- Output `200`: `{ campaigns: [...] }`
- Rules: only campaigns where requester is active member

4. `PUT /api/campaigns/<campaign_id>`
- Auth: required
- Input: subset of `{ name, description, status, max_players }`
- Output `200`: updated campaign
- Rules: DM/owner only

5. `DELETE /api/campaigns/<campaign_id>`
- Auth: required
- Output `200`: success marker
- Rules: owner only; soft-delete (`deleted_at`) not hard delete

#### Membership

6. `POST /api/campaigns/<campaign_id>/invite`
- Auth: required
- Input: `{ player_username }`
- Output `201`: `{ invite_token, invited_user }`
- Rules: DM only; reject duplicate existing membership

7. `POST /api/campaigns/<campaign_id>/accept-invite`
- Auth: required
- Input: `{ token }`
- Output `200`: success marker
- Rules: token valid, requester invited

8. `GET /api/campaigns/<campaign_id>/members`
- Auth: required
- Output `200`: member list
- Rules: active campaign member only

#### Sessions

9. `POST /api/campaigns/<campaign_id>/sessions`
- Auth: required
- Input: `{ name, scheduled_at?, duration_minutes? }`
- Output `201`: session object
- Rules: DM only; validate schedule/duration

10. `POST /api/campaigns/<campaign_id>/sessions/<session_id>/start`
- Auth: required
- Output `200`: updated session object
- Rules: DM only; set status to `in_progress`, set `started_at`

11. `POST /api/campaigns/<campaign_id>/sessions/<session_id>/end`
- Auth: required
- Output `200`: updated session object
- Rules: DM only; set status to `completed`, set `ended_at`

12. `GET /api/campaigns/<campaign_id>/sessions`
- Auth: required
- Output `200`: session list for campaign
- Rules: active campaign member only

### 3. Data/state rules

Campaign membership state:

`invited -> active -> (left | kicked)`

Session state:

`scheduled -> in_progress -> completed`

Guard rules:

- A requester not in active membership receives `403`.
- Non-DM mutation attempts receive `403`.
- Missing entities return `404`.
- Invalid invite token returns `401` or `400` based on validation stage.
- Duplicate invite/membership attempts return `409`.

### 4. UI flow design (M4 scope)

#### Campaigns page

- “New Campaign” action calls `POST /api/campaigns`.
- “View” navigates to campaign-focused route (or detail section) backed by `GET /api/campaigns/<id>`.
- “Delete” performs soft-delete call to `DELETE /api/campaigns/<id>` for owners.

#### Lobby page

- “Create Campaign” action wired to same create flow.
- “Join via token” action wired to `POST /api/campaigns/<id>/accept-invite`.
- “Enter campaign” action navigates to campaign detail experience.

Non-core UI extras (advanced realtime indicators, live presence) are explicitly deferred.

### 5. Deploy sequencing plan

1. Backend endpoints completion
   - Fill missing campaign/member/session endpoints.
2. Backend validation and role guard hardening
   - Duplicate invite checks, campaign ownership checks, status transitions.
3. Frontend action wiring
   - Replace placeholder alerts in campaigns/lobby with API-backed behavior.
4. Test coverage expansion
   - Add tests for each newly added endpoint and key negative paths.
5. Monitor execution prep
   - Run full auth+campaign+character regression suite and capture output.

---

## Acceptance Criteria

AC-M4-01: All 12 campaign/session endpoints exist and return expected status codes for happy and key failure paths.  
AC-M4-02: Campaign owner/DM authorization is enforced server-side for all mutating campaign/session operations.  
AC-M4-03: Duplicate invite/membership attempts are handled deterministically (no unhandled DB integrity exception path).  
AC-M4-04: Campaign soft delete path is implemented and verified (`deleted_at` set, hidden from normal listings).  
AC-M4-05: Session lifecycle endpoints support `scheduled -> in_progress -> completed` with timestamps persisted.  
AC-M4-06: Campaigns and lobby pages no longer rely on placeholder `alert(...)` actions for core create/join/view/delete flows.  
AC-M4-07: Test suite includes coverage for newly added endpoints and passes in local `.venv`.  
AC-M4-08: No campaign/session realtime socket requirement remains open in M4 deliverables (explicitly deferred to M5).

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | UI and backend contract mismatch during wiring can cause partial non-functional actions. | `medium` | yes |
| R2 | Route expansion without shared validation helpers may introduce inconsistent error contracts. | `medium` | yes |
| R3 | Relationship overlap/legacy query warnings remain technical debt and may mask future ORM issues. | `low` | no |
| R4 | No migration framework means schema change rollback remains manual. | `low` | no |
| R5 | Realtime deferral to M5 may be perceived as feature gap if expectations are not communicated. | `low` | no |

Assumption A1: M4 acceptance is defined by functional API/UI core loop, not live presence/realtime campaign orchestration.

---

## Open TBDs

| # | TBD | Priority | Owner |
|---|---|---|---|
| T1 | Final campaign detail route UX (`/campaign/<id>` vs integrated campaigns view) | important | human + frontend |
| T2 | Exact error code split for invite token invalid vs expired (`400` vs `401`) | important | backend |
| T3 | Whether to add start/end session idempotency safeguards in M4 or defer to M5 hardening | nice-to-have | backend |

---

## Next Step

Start M4 Deploy by implementing the missing campaign/member/session endpoints first, then wire campaigns/lobby UI actions to those endpoints in one cohesive pass.

