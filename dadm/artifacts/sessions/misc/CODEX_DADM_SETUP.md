# Codex DAD-M Setup

Date: 2026-03-30

This repository now includes a minimal Codex-native DAD-M layer:

- `AGENTS.md`
- `.codex/config.toml`
- `.codex/agents/dadm-orchestrator.toml`
- `.codex/agents/reviewer.toml`
- `.codex/agents/docs-researcher.toml`
- `.agents/skills/dadm-discover/SKILL.md`
- `.agents/skills/dadm-apply/SKILL.md`
- `.agents/skills/dadm-deploy/SKILL.md`
- `.agents/skills/dadm-monitor/SKILL.md`
- `dadm-framework/runtime/bios.policy.md`
- `dadm-framework/runtime/bios.routing.yaml`
- `dadm-framework/runtime/bios.registry.json`

## Design Intent

The setup keeps method, delegation, and execution separate:

- `AGENTS.md` holds durable repo rules
- phase skills hold reusable DAD-M workflows
- custom agents are narrow helpers for orchestration, review, and docs verification
- BIOS control-plane artifacts hold prompt-to-phase-to-capability resolution

## BIOS Control Plane

The runtime BIOS extension does not duplicate the repo rules.

Instead it adds:

- `bios.policy.md`: what BIOS is allowed to do
- `bios.routing.yaml`: intent taxonomy, phase mapping, trigger semantics, and capability selection rules
- `bios.registry.json`: generated inventory of the repo's Codex-relevant capabilities with hashes and safety flags

Refresh the registry with:

```bash
python3 dadm-framework/runtime/build_bios_registry.py
```

## Current Defaults

Project-level Codex settings:

```toml
[agents]
max_threads = 4
max_depth = 1
```

This favors predictable, reviewable delegation over deep recursion.

## How To Invoke The Skills

Examples:

```text
$dadm-discover Research this repository and produce a Discover output for M01.
Scope: Discord login and bot-backed authorization.
Constraints: no code changes.
```

```text
$dadm-apply Turn the approved Discover findings into an implementation-ready design.
Do not implement yet.
```

```text
$dadm-deploy Implement the approved login flow changes and run targeted verification.
```

```text
$dadm-monitor Validate the branch, summarize regressions, and recommend the next bounded step.
```

## How To Invoke Subagents

Examples:

```text
Spawn dadm_orchestrator to scope this milestone and recommend the safest next phase.
```

```text
Have reviewer inspect this branch for correctness, security, regressions, and missing tests.
```

```text
Have docs_researcher verify the Codex or framework APIs this setup depends on.
```

```text
Spawn one agent per point:
1. reviewer for risk review
2. docs_researcher for official-source verification
Wait for all and return a consolidated recommendation.
```

## Notes

- Discovery and Apply are intentionally no-code phases.
- OpenAI or Codex behavior should be verified against official OpenAI docs before repo guidance is changed.
- If deeper automation is added later, keep `max_depth = 1` unless a very specific recursive workflow is proven necessary.
