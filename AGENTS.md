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

## VTT Live Delivery Rule (owner decision, 2026-11-01)

- The existing production VTT is the user acceptance environment. Do not make
  a separate development or staging environment a prerequisite for delivery.
  Focused automated checks still run before release; they do not replace live acceptance.
- An authorized functional change is not complete until it is committed,
  deployed to `https://vtt.roll-drauf.de`, and reachable through the established
  VTT UI by its intended user role. Carry implementation through deployment
  and live verification in the same work cycle; do not leave an undisclosed
  local-only feature or require the owner to know an undocumented URL.
- For every functional slice, record the user journey/navigation entry,
  intended roles, acceptance criteria, source commit, deployed image identity,
  targeted checks, live verification and rollback reference. Report missing
  evidence or a delivery blocker explicitly; never label an undeployed or
  inaccessible change as done. Push the commit when repository access permits;
  identify a failed push separately from deployment status.
- Determine the actual running source/image and Compose configuration before
  deployment. Reconcile the slice with the latest explicit product decisions.
  Intentional replacements are allowed and expected: superseded code is not
  unfinished work to resurrect, and difference from production alone is not a
  regression. Protect behavior that remains required, including newer work
  present in another branch or the live image.
- Never bundle unrelated dirty work or superseded implementations into a
  release. Keep a recoverable prior image; handle schema/data changes within
  their explicit scope. If checks fail or required access is missing, leave
  the slice visibly incomplete with the exact next step.
- Discover/Apply reports, repository rules and other documentation-only work
  retain their phase boundaries and do not require an application deployment.
  An audit request does not itself authorize unrelated feature implementation.
- This rule supersedes older runbooks that require staging or treat local
  completion as delivery.

## Done When

A task is done only when:

- the current phase output is complete
- the requested repo changes are applied
- verification status is explicit
- remaining risks or follow-ups are clearly named
