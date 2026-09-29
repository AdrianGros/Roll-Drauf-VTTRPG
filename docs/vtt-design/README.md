# VTT design — authoring and sandbox

**28 September update:** the current test target is **Wednesday, 30 September 2026**, following the user’s latest instruction. The [race-to-sheet journey](../creation-engine/race-to-sheet-2026-09-28.md) adds D&D homebrew race authoring, character handoff and visible navigation. Earlier Tuesday plans and results below remain historical evidence.

**Status, 27 September 2026:** design v0.1 is in implementation following the user's instruction to continue. **Slices 1–3 are implemented and verified in the working tree**. Slice 1 covers the dashboard entry, shared editor theme/navigation and responsive/guarded navigation. Slice 2 adds draft-conflict recovery, deliberate focus/error handling and distinct sandbox-copy references. Slice 3 adds open-page access-loss handling, delayed-response protection, current sandbox projections and keyboard access recovery. The slice 3 selected regression passed **139 tests**, including 14 new access-state cases; work remains uncommitted. Human testing stays deferred until the scheduled **Tuesday, 29 September 2026** session (Europe/Berlin; time and attendance not supplied).

| Artifact | Purpose and authority |
| --- | --- |
| [Initial discovery](design-contract-discovery-2026-09-27.md) | Dated source inventory and gaps; preserved as discovery evidence. |
| [Design v0.1](authoring-sandbox-design-v0.1.md) | Proposed target for this bounded journey, source reconciliation, tradeoffs and implementation handoff. |
| [Design contracts v0.1](authoring-sandbox-contracts-v0.1.md) | Stable `VD-C01`–`VD-C16` observable requirements. Specified; not a claim of implementation or acceptance. |
| [Slice 1 implementation and evidence](deploy-slice1-2026-09-27.md) | Files changed, exact verified scope, screenshots/measurements, residual gaps and next step. |
| [Slice 2 implementation and evidence](deploy-slice2-2026-09-27.md) | Conflict recovery, focus/validation, copy identity and that slice's selected regression. |
| [Slice 3 implementation and evidence](deploy-slice3-2026-09-27.md) | Confirmed-denial cleanup, response ordering, access/capability rechecks, keyboard recovery and retained verification limits. |
| [Task-readiness implementation](deploy-task-readiness-2026-09-27.md) | Manual conditional/choice and standalone lore authoring, lifecycle verification, exact source evidence and residual limits. |
| [Task-readiness design](authoring-task-readiness-v0.1.md) | Explicit manual conditional/choice and standalone lore profiles, compatibility contracts and limits. |
| [Task cards and reset protocol](study-task-cards-2026-09-29.md) | Neutral proposed tasks, scope-review requirement and isolated setup/reset procedure. |
| [Tuesday run manifest](study-run-manifest-2026-09-29.json) | Candidate linkage and unfilled roster/time/build/acceptance fields; no human results. |
| [Test backlog and Tuesday protocol](test-backlog-2026-09-29.md) | Engineering preparation, deferred human scenarios, dependencies, ownership and evidence requirements. |
| [Result template](study-results-template.csv) | Empty observation register. No participant results have been recorded. |

**Task-readiness follow-up:** the editor now also supports manual conditional-effect cards, authored manual choices and standalone lore. Existing flame registry bytes and runtime locks are preserved. New tab-loss, equip/use, timeout and manual-completion checks have evidence; the [report](deploy-task-readiness-2026-09-27.md) distinguishes the combined run and focused keyboard follow-up from the unavailable WebKit check. Manual task fit still requires acceptance-owner review before T45 scoring.

The [engine authority](../creation-engine/README.md) remains v1.1.4 / core wire 1.1.3 / registry A1. G1 remains in Deploy. Its WP8 implementation is verified in the working tree; the scheduled WP8 product test contributes to WP9 evidence. Scheduling postpones the human evidence; it does not waive it or complete G1.

The design/backlog define the target; implementation reports identify completed slices and evidence. This is not a completed UI redesign or a new engine baseline. No calendar booking or participant confirmation is claimed. Human testing is deferred until 29 September; implementation, source review, automated checks, fixture preparation and documentation may proceed before then.

Use the contract catalogue for exact UI behavior and the backlog for execution status. Existing engine T-identifiers retain their original meaning; `VD-C`, `VD-T` and `VD-H` identifiers belong only to this design/test package. Future revisions must identify affected contracts and preserve dated evidence. Do not overwrite historical engine evidence or promote a screenshot/test name into proof of user acceptance.
