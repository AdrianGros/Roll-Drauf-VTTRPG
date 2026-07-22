# DAD-M Orchestrator Protocol: Book UI 20-Milestone Block

Date: 2026-04-01
Status: active
Scope: orchestration rules for the spellbook UI milestone block

## Approval Override

On 2026-04-01 the project owner granted a package-wide approval override for the Book UI block:

- scope: `M01` through `M20`
- framework role: admin-level execution for this package
- human approval: not required between milestones for this package
- explicit approval statement: `M1-M20 Approved for CODEX autonomy`
- explicit approval text confirmed: `M1-M20 Approved for CODEX autonomy`

This override does not remove the orchestrator's responsibility to:

- keep milestone scope small
- review delegated output
- record risks
- enforce the one-live-check-per-milestone limit
- reject progression when artifacts and implementation diverge

## Purpose

Provide one operating protocol for running the Book UI milestone program in small, auditable slices.

## Active Approval Override

For the Book UI package `M01-M20`, a one-time framework-level approval override is active.

Effective consequence:

- no additional human approval gate is required between milestones
- the orchestrator may approve progression directly
- all other scope, verification, artifact, and live-check limits still apply

## Operating Loop Per Milestone

1. Write milestone-specific `discover`
2. Write milestone-specific `soll`
3. Write milestone-specific `research`
4. Delegate implementation work to a sub-agent where useful
5. Review returned changes locally
6. Run local verification
7. Perform at most one live verification check if needed
8. Write `apply`, `deploy`, and `monitor`
9. Approve or reject progression

## Delegation Rule

The orchestrator may delegate:

- code exploration
- bounded implementation
- verification support

The orchestrator must still:

- define scope
- review output
- decide approval
- record residual risks

## Approval Ledger Format

For each milestone, record:

- `milestone`
- `status`
- `scope_kept: yes/no`
- `live_check_used: yes/no`
- `artifacts_complete: yes/no`
- `risks_open`
- `approval`

## Hard Boundaries

- no multi-milestone deploy bundling
- no more than one live check per milestone
- no hidden scope expansion
- no approval if documentation and implementation disagree

## Initial Approval Ledger

| Milestone | Status | Scope Kept | Live Check Used | Artifacts Complete | Risks Open | Approval |
|---|---|---|---|---|---|---|
| M01 | approved | yes | no | yes | none beyond documented scope | approved |
| M02 | approved | yes | no | yes | none beyond later implementation work | approved |
| M03 | approved | yes | no | yes | minor source-render limitation documented | approved |
| M04 | approved | yes | no | yes | template-level nav duplication remains out of scope | approved |
| M05 | approved | yes | no | yes | none beyond later entry-flow design work | approved |
| M06 | approved | yes | no | yes | open product choices intentionally deferred to M07/M08 | approved |
| M07 | approved | yes | no | yes | signup auto-login decision remains deferred by design | approved |
| M08 | approved | yes | no | yes | login handoff messaging remains deferred to later auth work | approved |
| M09 | approved | yes | no | yes | none beyond shared spread polish | approved |
| M10 | approved | yes | no | yes | none beyond later implementation work | approved |
| M11 | approved | yes | no | yes | no additional source risk beyond documented interpretation | approved |
| M12 | approved | yes | no | yes | generic legacy class overlap remains a watchpoint | approved |
| M13 | approved | yes | no | yes | none beyond focus-shell implementation | approved |
| M14 | approved | yes | no | yes | none beyond later implementation work | approved |
| M15 | approved | yes | no | yes | no additional source risk beyond documented interpretation | approved |
| M16 | approved | yes | no | yes | mobile density remains a normal watchpoint | approved |
| M17 | approved | yes | no | yes | none beyond workspace-shell implementation | approved |
| M18 | approved | yes | no | yes | none beyond later implementation work | approved |
| M19 | approved | yes | no | yes | performance assumptions remain bounded to shell pilot scope | approved |
| M20 | approved | yes | no | yes | narrow-height behavior remains a normal watchpoint | approved |
