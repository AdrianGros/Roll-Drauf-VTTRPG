# M13 Discover Output: Realtime Resilience and Sync Robustness

```
artifact: discover-output
milestone: M13
phase: DISCOVER
status: complete
date: 2026-03-27
```

---

## Input Summary

- Baseline:
  - `milestone_m12_monitor_output.md`
  - current runtime in `vtt_app/socket_handlers.py`, `vtt_app/play/*`
- Human approval context:
  - `Approved: M11 - M14`
- Discover focus:
  - reconnect behavior
  - event ordering/conflict handling
  - desync prevention and recovery contracts

---

## Evidence Snapshot

- Socket event surface in runtime:
  - `14` handlers in `vtt_app/socket_handlers.py` (`connect`, `disconnect`, `session:join`, `session:leave`, `mod:*`, `state:*`, `map:activate`, `token:*`, `roll_dice`).
- Rejoin test depth:
  - only `2` dedicated tests in `tests/test_play_rejoin_socket.py`.
- Conflict test coverage:
  - only `1` socket conflict assertion (`tests/test_tokens_realtime.py`: `state:conflict` on wrong `base_version`).
- `base_version` in socket token mutation is optional (not enforced) in:
  - `token:update`
  - `token:delete`

---

## Key Discover Findings

### F1 - Socket token mutations allow blind last-write-wins updates

`token:update` and `token:delete` only validate optimistic concurrency if `base_version` is provided.
If omitted, update/delete succeeds and increments version.

Impact:

- high race-risk under concurrent operators
- silent overwrites possible without conflict signal

### F2 - No idempotency key on socket mutations

Socket `token:create/update/delete` payloads have no `client_event_id` or dedupe key.

Impact:

- retransmit/retry can duplicate writes or replay mutations
- reconnect edge-cases can apply the same user intent twice

### F3 - No room-level event sequence contract for client ordering

Events include state/token versions in many payloads, but there is no monotonic per-room event sequence.
Frontend socket runtime applies inbound events directly and does not drop stale/out-of-order events.

Impact:

- clients cannot deterministically reject stale events
- transient network reordering can produce UI drift until manual refresh

### F4 - Session join does not enforce single active play-room per socket

`session:join` adds room membership, but does not automatically leave previous session rooms for the same socket.

Impact:

- stale subscriptions possible if join is called multiple times without explicit leave
- cross-session event noise risk on long-lived clients

### F5 - Reconnect contract is present but shallowly validated

On `session:join`, server returns:

- `session:joined`
- authoritative `state:snapshot`
- `play:mode`

This is good baseline, but missing coverage for:

- disconnect/reconnect during in-flight mutations
- replayed/stale event handling
- session switch on same socket

### F6 - Resilience telemetry is still coarse for sync incidents

Socket metrics track event counts by name, but no dedicated counters for:

- conflicts emitted
- resync requests
- stale event drops
- reconnect recoveries vs failures

Impact:

- desync incidents are hard to quantify and trend

---

## Consolidated Decision Log (M13)

| ID | Decision | Consequence | Risk if Deferred |
|---|---|---|---|
| D1 | Require `base_version` for socket `token:update` and `token:delete` | deterministic optimistic concurrency in realtime path | hidden last-write-wins clobbering |
| D2 | Add `client_event_id` idempotency for socket mutations | retry-safe realtime writes | duplicate replay on network retries |
| D3 | Introduce per-session monotonic `event_seq` on emitted realtime events | client can reject stale/out-of-order events | unresolved ordering drift |
| D4 | Enforce single active play session room per socket on `session:join` (or explicit policy) | prevents stale room subscriptions | mixed-room event leakage risk |
| D5 | Add explicit resync contract (`state:request` with `since_seq` / full snapshot fallback) | robust reconnect recovery | manual refresh dependency |
| D6 | Expand telemetry with conflict/resync/recovery counters | measurable reliability posture | no evidence-driven tuning |
| D7 | Expand test matrix for reconnect+ordering chaos paths | regression guardrails for resilience work | fragile behavior under scale |

---

## M13 Apply Scope Proposal

### Track A: Protocol hardening

- require `base_version` in socket mutation writes
- add `client_event_id` for idempotent handling
- define event envelope with `event_seq`, `server_time`, `session_id`

### Track B: Room/session safety

- single-active-session-room policy per socket
- safe room switch behavior in `session:join`
- explicit leave cleanup consistency checks

### Track C: Client reconciliation

- ignore stale events by sequence/version
- trigger resync on detected gaps/conflicts
- preserve authoritative snapshot as recovery source

### Track D: Verification and observability

- tests for:
  - reconnect during mutation
  - duplicate event replay
  - out-of-order delivery handling
  - session room switch isolation
- metrics:
  - `socket_conflicts_total`
  - `socket_resync_requests_total`
  - `socket_reconnect_recoveries_total`
  - optional `socket_stale_events_dropped_total`

---

## Acceptance Targets for M13 Deploy (Draft)

- AC-M13-01: socket mutation writes enforce optimistic concurrency contract.
- AC-M13-02: duplicate client mutation events are idempotently handled.
- AC-M13-03: realtime events carry sequence metadata and clients handle stale ordering safely.
- AC-M13-04: reconnect path restores authoritative state without manual reload.
- AC-M13-05: session room switching cannot leak events from prior sessions.
- AC-M13-06: resilience metrics and targeted tests are present and green.

---

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Protocol change across socket payloads requires synchronized backend/frontend rollout. | high | yes |
| R2 | Idempotency persistence design (in-memory vs DB) impacts correctness/perf tradeoff. | medium | yes |
| R3 | Event-sequencing retrofit may touch many emit points and test fixtures. | medium | yes |

Assumption A1: M13 is resilience-first and should avoid broad gameplay feature expansion.  
Assumption A2: Existing `/api/play` and token/combat data models remain valid foundations.

---

## Next Step

Proceed to **M13 Apply**:

1. freeze event envelope and concurrency contract,
2. implement minimal server+client changes for deterministic recovery,
3. land resilience tests and telemetry before deploy closeout.
