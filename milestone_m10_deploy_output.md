# M10 Deploy Output: Vertical Slice Live Runtime (`/play`)

```
artifact: deploy-output
milestone: M10
phase: DEPLOY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Design baseline:
  - `milestone_m10_apply_output.md`
- Human approval:
  - `APPROVED: M10 Deploy.`
- Deploy scope:
  - implement session runtime vertical slice from lobby to play
  - keep compatibility with existing campaign/session/token stack
  - deliver M10-specific test suites + preserve regression green state

---

## Implementation Summary

Implemented M10 end-to-end with a dedicated `/play` runtime flow:

- Backend runtime module:
  - added `vtt_app/play` blueprint and registered it under `/api/play`
  - implemented runtime bootstrap, ready-check, lifecycle transitions, scene stack init/layer activation, and action execution endpoints
- New runtime domain models:
  - `SceneStack`, `SceneLayer`, `SessionSnapshot`
  - wired model exports for app-wide metadata creation
- Lifecycle + RBAC:
  - state-machine transitions for `scheduled`, `ready`, `in_progress`, `paused`, `ended`
  - operator permissions for both `DM` and `CO_DM`
  - waiting-room and observer read-only behavior
- Reconnect/play-mode signaling:
  - socket `session:join` now emits `play:mode` alongside authoritative snapshot
  - compatibility status normalization (`completed -> ended`, `cancelled -> paused`)
- Frontend runtime surface:
  - new `play.html` shell and JS runtime modules:
    - bootstrap loading
    - socket room join/rejoin handling
    - ready-check and lifecycle controls
    - scene layer activation
    - action bar v1 execution
    - explicit dice rolling UI
- Campaign handoff:
  - session cards in `campaigns.html` now include direct `Play` entry (`/play?campaign_id=&session_id=`)
  - `CO_DM` included in management/moderation UI checks

---

## Files Changed

- `vtt_app/__init__.py`
- `vtt_app/campaigns/routes.py`
- `vtt_app/socket_handlers.py`
- `vtt_app/play/service.py`
- `vtt_app/templates/campaigns.html`
- `vtt_app/templates/play.html` (new)
- `vtt_app/static/js/play-client.js` (new)
- `vtt_app/static/js/play-socket.js` (new)
- `vtt_app/static/js/play-ui.js` (new)
- `tests/play_shared.py` (new)
- `tests/test_play_bootstrap_api.py` (new)
- `tests/test_session_state_machine.py` (new)
- `tests/test_ready_check.py` (new)
- `tests/test_scene_stack_api.py` (new)
- `tests/test_play_permissions.py` (new)
- `tests/test_play_rejoin_socket.py` (new)
- `tests/test_action_bar_v1.py` (new)
- `milestone_m10_deploy_output.md` (new)

---

## Proofs

Executed command:

`.\.venv\Scripts\python -m pytest tests/test_play_bootstrap_api.py tests/test_session_state_machine.py tests/test_ready_check.py tests/test_scene_stack_api.py tests/test_play_permissions.py tests/test_play_rejoin_socket.py tests/test_action_bar_v1.py -q`

Result:

- `19 passed`

Executed command:

`.\.venv\Scripts\python -m pytest tests/test_auth.py tests/test_campaigns.py tests/test_maps.py tests/test_session_state.py tests/test_tokens_realtime.py tests/test_combat_api.py tests/test_chat_api.py tests/test_play_bootstrap_api.py tests/test_session_state_machine.py tests/test_ready_check.py tests/test_scene_stack_api.py tests/test_play_permissions.py tests/test_play_rejoin_socket.py tests/test_action_bar_v1.py -q`

Result:

- `74 passed`

Executed command:

`.\.venv\Scripts\python -m pytest -q`

Result:

- `110 passed`

---

## Acceptance Checklist

- [x] AC-M10-01: `/play` route exists and loads authenticated session runtime by `campaign_id` + `session_id`.
- [x] AC-M10-02: Bootstrap endpoint returns role, mode, scene/layer metadata, and authoritative state payload.
- [x] AC-M10-03: Session lifecycle supports `scheduled`, `ready`, `in_progress`, `paused`, `ended` with enforced valid transitions.
- [x] AC-M10-04: DM and CO_DM can transition session state; players/observers cannot.
- [x] AC-M10-05: Waiting-room mode is read-only for players before `in_progress`.
- [x] AC-M10-06: Scene stack/layer model supports switchable multi-layer session stacks.
- [x] AC-M10-07: Layer activation updates active play map and broadcasts synced state.
- [x] AC-M10-08: Action bar v1 supports server-validated action execution on owned tokens.
- [x] AC-M10-09: Dice interaction remains explicit and visible in the play surface.
- [x] AC-M10-10: Rejoin returns authoritative snapshot and current play mode.
- [x] AC-M10-11: Start/end transition snapshots are persisted (`SessionSnapshot`).
- [x] AC-M10-12: M10 suites + full regression pass locally in `.venv`.

---

## Risks and Follow-up

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Test/plugin warning: `PytestAssertRewriteWarning` for `tests.play_shared` import order. | low | no |
| R2 | Existing repository-wide deprecation warnings (`datetime.utcnow`, `Query.get`) remain noisy. | medium | no |
| R3 | Play UI is functional vertical slice; deeper UX polish and DM cockpit ergonomics remain phase-2 work. | medium | no |

---

## Next Step

Proceed to **M10 Monitor**:

1. validate real browser flow (campaign lobby -> `/play` -> ready -> live -> pause -> end),
2. capture runtime evidence (screens + socket event timeline),
3. monitor early session usage and convert warning hotspots into M11 hardening tasks.
