# M13 Apply Output: Realtime Resilience and Sync Robustness

```
artifact: apply-output
milestone: M13
phase: APPLY
status: complete
date: 2026-03-27
```

---

## Input Summary

- Discover baseline:
  - `milestone_m13_discover_output.md`
- Human approval:
  - `APPROVED: M13 Apply`
- Scope:
  - reconnect safety
  - optimistic concurrency hardening
  - out-of-order/stale event resilience
  - resilience telemetry and targeted tests

---

## Chosen Architecture Decisions

1. **Strict socket concurrency for mutable token events**
   - `token:update` and `token:delete` require `base_version` (no optional fallback).
   - Conflict remains explicit via `state:conflict`.

2. **Client mutation idempotency contract**
   - Add required `client_event_id` for socket mutation writes.
   - Server dedupes repeated mutation intents (short retention window).

3. **Unified realtime event envelope**
   - Add `event_seq` (monotonic per session room) to state-changing emits:
     - `token:created`
     - `token:updated`
     - `token:deleted`
     - `map:activated`
     - `session:state_changed`
     - `scene:layer_activated`
     - `action:executed`
   - Include `session_id`, `campaign_id`, `server_time` consistently.

4. **Client-side stale/drop handling**
   - Track latest `event_seq` per session.
   - Ignore stale events (`<= last_seq`).
   - Request resync when gap detected.

5. **Room safety policy**
   - On `session:join`, leave previous play-session rooms for same socket before joining target room.
   - Preserve mod room behavior separately.

6. **Recovery path**
   - Keep authoritative snapshot as recovery source.
   - On gap/conflict/reconnect uncertainty, trigger `state:request`.

---

## Work Tracks (M13 Deploy Plan)

### Track A: Protocol + server contract

- `vtt_app/socket_handlers.py`
  - enforce required `base_version` + `client_event_id` on token mutate events.
  - implement in-memory dedupe registry per `(session_id, client_event_id, user_id)`.
  - add `event_seq` allocation and event envelope utility.
  - apply single-active-session-room join policy.

### Track B: Client resilience logic

- `vtt_app/static/js/play-socket.js`
  - track `lastEventSeq`.
  - gate handlers against stale sequence.
  - detect sequence gaps and emit `state:request`.
  - include `client_event_id` + `base_version` support hooks for mutation-capable calls.

### Track C: Telemetry

- metrics store + `/metrics` export:
  - `socket_conflicts_total`
  - `socket_resync_requests_total`
  - `socket_reconnect_recoveries_total`
  - optional `socket_stale_events_dropped_total`

### Track D: Tests

- add/extend tests for:
  - required `base_version` in socket token mutation.
  - duplicate `client_event_id` dedupe behavior.
  - stale/out-of-order event drop behavior (client-level where feasible).
  - room switch on repeated `session:join`.
  - reconnect + recovery path assertions.

---

## Rollout Order

1. Server contract changes (`socket_handlers`) + metrics wiring.
2. Client `play-socket` sequence/recovery logic.
3. Test additions and updates.
4. Regression run.
5. M13 deploy artifact and closure recommendation.

---

## Acceptance Criteria for M13 Deploy

- AC-M13-01: socket token mutate calls reject missing `base_version`.
- AC-M13-02: duplicate `client_event_id` mutations are idempotent.
- AC-M13-03: emitted realtime mutations include monotonic `event_seq`.
- AC-M13-04: client ignores stale events and resyncs on sequence gaps.
- AC-M13-05: repeated `session:join` cannot leave socket in multiple play-session rooms.
- AC-M13-06: resilience counters are exported in `/metrics`.
- AC-M13-07: targeted resilience test suite + full regression pass.

---

## Risks and Mitigations

| # | Risk | Mitigation |
|---|---|---|
| R1 | Contract change can break older clients | keep errors explicit; update play client in same deploy |
| R2 | In-memory dedupe cache can reset on restart | scope as short-window safety, not persistence guarantee |
| R3 | Sequence logic bugs can cause false resync storms | gap detection thresholds + targeted tests |

---

## Next Step

Proceed to **M13 Deploy** implementing Tracks A-D in one controlled rollout.
