# roll drauf vtt - Milestone Plan (DAD-M)

Goal: stable community-ready VTT for ~200 users and ~40 active campaigns.

## Runtime Operating Method (dad-m-light)

For each milestone cycle we use the updated runtime flow:

1. Start from [`dadm-framework/runtime/AI_BIOS.md`](dadm-framework/runtime/AI_BIOS.md)
2. Load [`dadm-framework/runtime/file-registry.yaml`](dadm-framework/runtime/file-registry.yaml)
3. Use profile `standard` by default
4. Load phase route cards only (`discover`, `apply`, `deploy`, `monitor`)
5. Escalate to full governance/framework docs only if required

## Milestones

### M3: Auth and User Management
- Discover: users, roles, sessions, security constraints
- Apply: schema, API contracts, hardening plan
- Deploy: auth endpoints, UI, session model
- Monitor: functional/security verification

### M4: Campaign and Session Management
- Discover: campaign workflows, invites, joins, session state
- Apply: campaign/session API and data model
- Deploy: lobby and campaign dashboard
- Monitor: concurrency and limit testing

### M5: Map, Token, Session State Stabilization
- Discover: map/grid/light persistence needs
- Apply: map_state and token_state architecture
- Deploy: persisted multi-map campaign support
- Monitor: sync/load testing at target scale

### M6: Character Sheets and Combat
- Discover: D&D model scope, combat workflow
- Apply: modular sheet/combat engine design
- Deploy: character CRUD + automation
- Monitor: playable end-to-end dungeon run

### M7: Community and Moderation
- Discover: chat/voice/moderation workflows
- Apply: moderation and social feature design
- Deploy: community tools and reporting
- Monitor: QoS and resilience checks

### M8: Production Readiness
- Discover: data protection, backup, policy constraints
- Apply: CI/CD, deployment, observability architecture
- Deploy: production infra + SSL + monitoring
- Monitor: load, failover, and recovery validation

### M9: Session Runtime and Play Environment (Design Consolidation)
- Discover: decision log, domain boundaries, live flow and licensing constraints
- Apply: `/play` route architecture, session state machine, scene-stack and action-system contracts
- Deploy: minimal integrated play-shell prototype (behind feature flag if needed)
- Monitor: usability and scope adherence for vertical-slice target

### M10: Vertical Slice Implementation (Lobby -> Play -> End)
- Discover: implementation gaps by module and migration impacts
- Apply: implementation blueprint with strict MVP cutline
- Deploy: end-to-end playable slice (waiting room, start, live, pause, end, snapshot)
- Monitor: session reliability, rejoin behavior, DM/operator experience

### M11: Hardening, Performance, Monitoring
- Discover: warning debt, observability gaps, runtime bottlenecks
- Apply: hardening and telemetry uplift blueprint
- Deploy: runtime debt burn-down + metrics/logging enhancements + load/CI smoke upgrades
- Monitor: live-flow evidence with correlation and regression quality gates

### M12: Session UX and Operator Ergonomics
- Discover: DM/player workflow friction and cockpit pain points
- Apply: UX simplification and control-surface design
- Deploy: improved play controls, clearer state feedback, reduced operator clicks
- Monitor: usability checks and session completion quality

### M13: Realtime Resilience and Sync Robustness
- Discover: reconnect, ordering, conflict, and desync edge cases
- Apply: sync contract hardening strategy
- Deploy: deterministic reconnect/conflict handling and stronger socket safeguards
- Monitor: stress and chaos-style reliability checks

### M14: Scale Readiness and Release Gate
- Discover: release criteria, SLOs, and operational thresholds
- Apply: release-hardening checklist and go-live gates
- Deploy: final scale/ops improvements and release packaging
- Monitor: go/no-go evidence run with rollback readiness

### M15: MVP Launch Handover and Operating Playbook
- Discover: launch-day operator workflow gaps and handover risks
- Apply: finalize run commands, evidence flow, and ownership checkpoints
- Deploy: ship launch playbook artifacts and evidence automation wrapper
- Monitor: execute launch rehearsal and confirm repeatability

## Completion Targets

- 200 concurrent accounts
- 40 active campaigns
- recovery target under 5 minutes
- low-latency token events under 150 ms
- high backend test coverage on core modules
