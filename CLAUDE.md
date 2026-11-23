# VTT Claude Code entry

Read `AGENTS.md` before work; it remains the durable repository rule source.
Use the smallest DAD-M runtime profile and the route card for the assigned phase.

Active handoff (2026-11-23):
- `docs/plans/VTT_NEXT_FULL_VERSION_2026-11-23.md` and its JSON register are the
  active next-version scope: the owner assigned all retained outstanding work
  to FV01–FV18. Every packet still needs its bounded Apply before implementation;
  the existing S2–S11 designs remain proposals where not yet accepted.
- `docs/DADM_MONITOR_FULL_VERSION_LAYERS_2026-11-23.md`: FV04 is live on
  `207c8e9fc`; FV05/FV06 have partial deliveries. Preserve this source/image.
  FV01 has a reviewed Apply and spell-candidate inventory, without locale implementation.
- `docs/CLAUDE_HANDOFF_MAPMAKER_27_2026-11-23.md`
- `docs/DADM_DISCOVER_EDITOR_CREATOR_FEEDBACK_2026-11-23.md`
- `docs/DADM_APPLY_FEEDBACK_HARNESS_2026-11-23.md`
- `docs/DADM_APPLY_CLAUDE_MAPMAKER_2026-11-23.md` (S1 accepted; later slices remain proposals)

Earlier execution-program references (historical task IDs, not new assignments):
- `docs/DADM_DISCOVER_VTT_REVIEWS_2026-11-11.md`
- `docs/plans/VTT_REVIEW_CLAUDE_EXECUTION_2026-11-11.md`
- `docs/plans/VTT_REVIEW_CLAUDE_EXECUTION_2026-11-11.json`

A phase name and one task ID must be explicit before working. Planning tasks do
not authorize application edits. Implementation requires the task's completed
Apply contract, exact integration base and file ownership from the coordinator.

Implementation runs use the existing Claude subscription; no automatic switch to
API billing, extra usage or a different provider. Report quota/access failures.
Agents do not spawn agents. Work only in the assigned worktree. Do not reset,
stash, overwrite other workers, restore superseded G1 code, or access production.
Codex owns test execution, commit integration, pushes, production deployment and
live evidence. Read-only reviewers receive a diff and do not edit files.
