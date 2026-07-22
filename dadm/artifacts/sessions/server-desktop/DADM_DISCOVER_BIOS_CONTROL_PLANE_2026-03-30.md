# Discover Output

```
artifact: discover-output
milestone: BIOS-CONTROL-PLANE
phase: DISCOVER
status: complete
date: 2026-03-30
```

## Input Summary

This Discover pass worked from:

- `dadm-framework/runtime/AI_BIOS.md`
- `dadm-framework/runtime/file-registry.yaml`
- `dadm-framework/runtime/cards/discover-card.md`
- `dadm-framework/framework/templates/discover-output.md`
- repo-local Codex surfaces:
  - `AGENTS.md`
  - `.codex/config.toml`
  - `.codex/agents/*.toml`
  - `.agents/skills/*/SKILL.md`
- the current design goal: make BIOS the control plane that maps prompt intent to DAD-M phase and then to repo capabilities, without duplicating the operative instructions already stored in AGENTS, skills, config, or agents

## Current-State Summary

- Relevant: the repo now has a root `AGENTS.md` with DAD-M phase boundaries and Codex usage rules.
- Relevant: the repo now has project Codex config in `.codex/config.toml` with bounded delegation defaults.
- Relevant: the repo now has three custom agents in `.codex/agents/`:
  - `dadm_orchestrator`
  - `reviewer`
  - `docs_researcher`
- Relevant: the repo now has four DAD-M phase skills in `.agents/skills/`:
  - `dadm-discover`
  - `dadm-apply`
  - `dadm-deploy`
  - `dadm-monitor`
- Relevant: the current runtime BIOS is intentionally small and phase-oriented, but it does not yet define a formal capability-resolution layer.
- Relevant: the current file registry describes route cards and profiles, but it does not yet classify repo-local capabilities or routing metadata.
- Relevant: current Codex behavior is split across multiple surfaces with different trigger modes:
  - `AGENTS.md` loads automatically
  - skills can route implicitly through metadata or explicitly by name
  - subagents are best treated as explicit delegation only
  - MCP is capability-specific and external
- Relevant: without a separate routing model, the repo has the operative pieces but not the explicit translation layer from prompt -> phase -> capability.
- Not relevant for this milestone: application business logic, game routes, and frontend layout changes.
- Unclear: whether future BIOS routing should remain purely declarative or later gain script-backed scoring or heuristic ranking.

## Inventory

| # | Name | Description | Location | Status |
|---|---|---|---|---|
| I1 | Runtime BIOS | Minimal DAD-M runtime entrypoint | `dadm-framework/runtime/AI_BIOS.md` | present |
| I2 | Runtime registry | Runtime profiles, routes, and document classes | `dadm-framework/runtime/file-registry.yaml` | present |
| I3 | Repo policy | Durable Codex and DAD-M repo rules | `AGENTS.md` | present |
| I4 | Project Codex config | Bounded subagent settings | `.codex/config.toml` | present |
| I5 | Custom agents | Narrow orchestration, review, and docs roles | `.codex/agents/*.toml` | present |
| I6 | DAD-M skills | Phase-oriented reusable workflows | `.agents/skills/*/SKILL.md` | present |
| I7 | Capability registry | Structured inventory with hashes and flags | `dadm-framework/runtime/bios.registry.json` | missing before this milestone |
| I8 | Routing model | Prompt-intent to phase/capability mapping | `dadm-framework/runtime/bios.routing.yaml` | missing before this milestone |
| I9 | BIOS policy | Human-readable control-plane rules | `dadm-framework/runtime/bios.policy.md` | missing before this milestone |

## Dependencies

| # | Dependency | Version | Status |
|---|---|---|---|
| D1 | Codex repo rules surface (`AGENTS.md`) | repo-local | present |
| D2 | Codex project config (`.codex/config.toml`) | repo-local | present |
| D3 | Custom agent definitions (`.codex/agents/*.toml`) | repo-local | present |
| D4 | Repo skill metadata (`.agents/skills/*/SKILL.md`) | repo-local | present |
| D5 | Python stdlib for registry generation (`tomllib`, `json`, `hashlib`) | Python 3.11+ compatible | present |
| D6 | Official OpenAI docs for Codex behavior | external | present |

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | If BIOS duplicates AGENTS, skills, or agent instructions, the repo will drift into two competing truths. | `high` | yes |
| R2 | Skill routing is partly metadata-driven and partly prompt-driven, so the mapping layer can only be heuristic, not absolute. | `medium` | no |
| R3 | Subagent use is only predictable when treated as explicit delegation, not implied magic. | `medium` | no |
| R4 | A stale capability registry will cause wrong routing unless hashes or refresh triggers are tracked. | `medium` | yes |
| R5 | Overly deep delegation would conflict with DAD-M’s requirement for reviewable phase transitions. | `low` | no |

## Open Questions

| # | Question | Priority | Owner |
|---|---|---|---|
| Q1 | Should BIOS routing remain fully declarative in YAML/JSON, or later add a scoring layer for ambiguous prompts? | important | framework owner |
| Q2 | Should registry refresh happen only on explicit command, or automatically at task start when hashes changed? | important | framework owner |
| Q3 | Should repo-local skills be phase-only, or should cross-phase helper skills like `dadm-kodex-handoff` also be first-class in the routing model? | important | framework owner |
| Q4 | Should MCP capabilities be listed statically in the BIOS registry or only referenced through agent/config metadata? | nice-to-have | framework owner |

## Next Step

Apply should define the exact schema contract for BIOS routing and registry refresh, including which fields are mandatory for every capability and when a task must be re-routed back to an earlier DAD-M phase.
