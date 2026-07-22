# Codex + DAD-M Repo Rules

This repository uses DAD-M as the primary working method for complex work.

## Start Here

When work is larger than a trivial one-file edit, load the smallest useful DAD-M runtime context first:

1. `dadm/framework/runtime/AI_BIOS.md`
2. `dadm/framework/runtime/file-registry.yaml`
3. Default profile: `standard`
4. Load the route card for the active phase: `discover`, `apply`, `deploy`, or `monitor`

Prefer runtime cards over loading the entire framework tree.

## Phase Boundaries

### Discover

Purpose:
- gather facts
- inventory files, dependencies, constraints, and risks
- define a safe boundary for the next phase

Do:
- inspect code, docs, configs, tests, and live constraints
- capture evidence and severity-labeled risks
- end with a clear next step into Apply

Do not:
- choose architecture
- implement code
- hide design decisions inside a research summary

Minimum output:
- input summary
- current-state summary
- relevant inventory
- dependencies
- risks and assumptions
- open questions
- next step

### Apply

Purpose:
- design the solution inside the discovered boundary

Do:
- define target state, interfaces, contracts, rollout notes, and acceptance criteria
- make design decisions explicit
- keep the design tied to the discovered facts

Do not:
- implement code
- expand scope silently
- bypass unresolved medium-or-higher risks

Minimum output:
- design summary
- solution boundary
- interfaces or data contracts
- acceptance criteria
- risks or tradeoffs
- explicit deploy handoff

### Deploy

Purpose:
- implement an approved design and verify it

Do:
- make the smallest defensible change
- preserve unrelated user changes
- run targeted verification and record what was or was not run

Do not:
- introduce new architecture decisions
- mix in unrelated cleanups
- claim verification that did not happen

Minimum output:
- implementation summary
- files changed
- verification run
- proofs or evidence
- acceptance checklist

### Monitor

Purpose:
- validate outcomes, regressions, residual risk, and follow-up work

Do:
- check whether acceptance criteria were actually met
- capture regressions, incidents, or leftover risks
- propose the next bounded action

Do not:
- add silent feature work
- use Monitor to slip in undocumented fixes

Minimum output:
- observed results
- validation evidence
- residual risks
- recommended next action

## Planning First

For ambiguous, high-risk, or multi-step tasks:

- plan before editing
- keep phase boundaries explicit
- prefer a Discover or Apply pass before Deploy

If the user asks for research, discovery, planning, audit, inventory, or architecture direction, stay out of implementation unless the user explicitly redirects the phase.

## Repo-Native Codex Setup

This repo keeps Codex behavior in three layers:

- `AGENTS.md` for durable repo rules
- `dadm/skills/` for reusable DAD-M phase workflows
- `dadm/agents/` for narrow custom subagents

Prefer the repo skills when the task clearly maps to a phase:

- `$dadm-discover`
- `$dadm-apply`
- `$dadm-deploy`
- `$dadm-monitor`

## Subagent Policy

Subagents are for bounded parallel work, not default feature coding.

Use them when:
- exploration can be split cleanly across independent areas
- review needs a separate risk-focused pass
- documentation or framework verification should be isolated from implementation noise

Keep delegation controlled:
- default to one level only
- do not recursively fan out work without a strong reason
- ask for explicit subagent spawning when you want parallelization

Custom agents in this repo:
- `dadm_orchestrator`: planning, scoping, delegation, synthesis
- `reviewer`: read-only risk review
- `docs_researcher`: read-only documentation verification, especially for OpenAI/Codex behavior

## Verification Rules

- Run the smallest relevant verification for the change
- If verification cannot run, say why and record the gap
- For OpenAI or Codex product behavior, verify against official OpenAI docs before changing repo guidance

## Working Constraints

- Keep edits phase-appropriate
- Keep artifacts reviewable
- Preserve unrelated work already in the tree
- Use file references and concrete evidence when summarizing findings

## Done When

A task is done only when:

- the current phase output is complete
- the requested repo changes are applied
- verification status is explicit
- remaining risks or follow-ups are clearly named
