# Creation Engine — active contract and project status

**Advanced studio, 29 September:** the user authorized a power-user interface on
the class/race/spell backend before expanding Guided. The
[studio implementation record](advanced-studio-2026-09-29.md) covers complete
document editing, atomic saves, revision/history controls and the private test
bench at `/api/ce/authoring/advanced`. Production activation and human acceptance
remain separate from automated implementation evidence.

**Backend expansion, 29 September:** the user requires classes, races and spells
before inviting homebrew testers and has authorized backend-first implementation.
The [implementation boundary](homebrew-backend-2026-09-29.md) and
[private backend API](homebrew-backend-api.md) cover typed class/race/spell
authoring, character composition and executable spell outcomes in isolated
persisted test scopes. Existing manual race and G1 native contracts remain pinned.
The new backend needs M80; its Advanced browser integration is described above.
Human acceptance and production activation are not established by automated
item/race or backend evidence.

**Current work, 28 September:** the implemented end-to-end journey is:
D&D 5e homebrew race with features/traits → existing/imported character or a new
character sheet, with visible Creation Engine navigation throughout the VTT.
The test target is now **Wednesday, 30 September 2026** (Europe/Berlin), superseding
Tuesday's schedule below. See the [bounded scope and verification record](race-to-sheet-2026-09-28.md).
The real desktop/mobile browser journeys pass. This extends sheet authoring and
integration; it does not claim full D&D runtime
automation, change the frozen engine protocol, or close WP9. Live flags remain off
until a tested release is activated. The dated entries below are historical.

**Release instruction, 28 September:** the user requested committing and deploying the current engine work. The [release boundary](deployment-2026-09-28.md) preserves the active contract and current disabled live flags; deployment does not close WP9 or activate campaign cutover. Dated implementation entries below retain their original evidence.


**Current phase: G1 Deploy, authorized 24 September 2026. G0 passed.** Start here before reading or rewriting any specification. A larger document version does not supersede an approved implementation contract.

| Authority | Active artifact |
| --- | --- |
| Approved specification | [v1.1.4](v1.1.4/creation-engine-v1.1.4.md), including approved E1–E4 |
| Core wire protocol | [1.1.3 schema](v1.1.3/creation-engine-v1.1.3-contracts.schema.json), three commands |
| Approved command registry | [A1](addenda/creation-engine-v1.1-registry-addendum-a1.md) and [schema](addenda/creation-engine-v1.1-registry-a1.schema.json), 24 additional commands |
| Decisions and authorization | [Approval record](../../dadm/artifacts/approvals/approval_creation_engine_g1_2026-09-24.md); its final G0/Deploy rows establish current authorization |
| Implementation sequence and evidence | [G1 program](../../dadm/artifacts/programs/milestone_program_creation_engine_g1.md), especially §16 |
| Reconciled reading edition and research proposals | [v1.2](v1.2/creation-engine-v1.2.md) · [PDF](v1.2/creation-engine-v1.2.pdf) |
| Why the documents diverged and how they were repaired | [Reconciliation report](v1.2/creation-engine-v1.2-reconciliation-report.md) |

The [machine-readable authority record](active-contract.json) pins this selection and its hashes. The reconciliation verifier checks that record as well as the selected files; a newly selected baseline cannot pass unnoticed merely because old files remain unchanged.

As checked on 27 September at HEAD `66b6fc4`, WP1–WP4 are committed. **WP5–WP8 are implemented and verified in the working tree**, including the three-mode authoring editor, private drafts/revisions and native flame-item sandbox execution. They remain uncommitted. The WP8 full repository run recorded **1,325 passes and one shared-browser-icon failure**; that defect was fixed, and the **final 113-test follow-up passed**, covering every implementation path changed after the full run began. Verification details and retained source hashes are in program §16. **Next is WP9: milestone acceptance evidence and the required ≥8-person user study.** The [runtime integration guide](runtime-integration.md) records installation, the separately pinned native runtime profile and the editor route. This is a dated snapshot; use the program and current checkout for later progress. The engine and adapter flags remain off by default, and G1 does not authorize live cutover.

**Scheduling update, 27 September:** the user reports the WP8 test is scheduled for **Tuesday, 29 September 2026** (Europe/Berlin; time and attendance not supplied). Human testing is deferred until that session; design, automated verification and fixture preparation can continue. Its results feed WP9, and the ≥8-person/four-task requirement is not waived. The [test backlog and study protocol](../vtt-design/test-backlog-2026-09-29.md) track missing capabilities and evidence separately. The companion [VTT design package](../vtt-design/README.md) defines the authoring-to-sandbox UI target and 16 proposed design contracts; it does not replace this engine baseline or claim that the UI redesign is implemented.

**UI implementation follow-up, 27 September:** the user authorized continuing into the bounded design implementation. [Slice 1](../vtt-design/deploy-slice1-2026-09-27.md) adds the server-controlled dashboard entry, shared book styling/navigation, localized orientation, protected dirty/pending navigation and the responsive editor layout. Its selected regression passed **111 tests**. This is partial design coverage in the working tree; the remaining technical matrix and Tuesday's human evidence stay open. Engine semantics, authority and default-off production flags are unchanged.

**UI slice 2, 27 September:** [conflict recovery, focus and copy identity](../vtt-design/deploy-slice2-2026-09-27.md) are implemented in the working tree. Competing saves preserve local input for read-only comparison and explicit resaving; validation/view/action focus is intentional, and same-named sandbox copies have distinct references. The selected regression passed **96 tests**, including 11 new browser cases. Open-page revocation, the remaining browser/accessibility matrix and Tuesday's human evidence remain open. No engine contract or production flag changed.

**UI slice 3, 27 September:** [open-page access handling](../vtt-design/deploy-slice3-2026-09-27.md) now clears protected content on confirmed denial or identity change, rejects stale responses, and refreshes authorized sandbox/capability data through existing reads. Connection-check failures retain input and exact pending commands while editing pauses. The selected regression passed **139 tests**, including 14 new access-state cases. Detection is request-driven, with visible-page checks every 15 seconds and on return; instantaneous push revocation is not claimed. Remaining lifecycle, browser/accessibility and human-study evidence is tracked in the backlog.

**Task-readiness follow-up, 27 September:** [manual conditional/choice and standalone lore authoring](../vtt-design/deploy-task-readiness-2026-09-27.md) now supplement the existing item editor. New profiles use separate registries; the flame artifact, existing drafts and native runtime pins remain intact. Conditional/choice cards are explicitly manual and reject executable quality/admission; the T45 acceptance owner must confirm their task depth before scoring. Tab loss, held-copy equip/use, worker timeout and manual clock-anomaly completion have fresh Chromium evidence. [Task cards](../vtt-design/study-task-cards-2026-09-29.md), [candidate source identity](../vtt-design/study-candidate-build-2026-09-27.json) and an [unfilled session manifest](../vtt-design/study-run-manifest-2026-09-29.json) prepare Tuesday without claiming attendance, session deployment or human acceptance.

The reconciled v1.2 keeps the approved body and T01–T56 intact, then adds research proposals T57–T74. It does not change the active wire version, reopen G0, or expand G1. The earlier workspace-only v1.2 rewrite is withdrawn because it was based on v1.1 and omitted approved corrections. Its schemas and unqualified T47–T64 citations must not be used as the implementation contract.

For future changes, first read this authority table and the latest program/approval status. Compare against the active specification, schemas, registry and all existing acceptance IDs. Preserve historical artifacts. Record new decisions as scoped deltas with the affected work package/gate and compatibility impact. Update this entry point only when an actual authority change is recorded. A research request or documentation rewrite alone does not reset the project phase.
