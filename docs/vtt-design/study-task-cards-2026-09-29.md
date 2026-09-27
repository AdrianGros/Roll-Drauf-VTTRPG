# Tuesday task cards and reset protocol

**Status:** prepared, not run. Human sessions remain deferred until **29 September 2026**,
Europe/Berlin. Record the actual time, roster, devices, build and task-fit decision in
the [run manifest](study-run-manifest-2026-09-29.json) before the study.

## Scope decision before scoring

The current candidate provides executable flame-item authoring, manual conditional-effect
and choice authoring, and standalone lore. The manual cards are saved typed definitions,
but people resolve their conditions/selections/consequences; no engine values or grants
are changed by those cards. The acceptance owner must record whether that depth meets the
intended T45 tasks. Until then their status is **scope review needed**, not accepted.
If executable conditional effects/choices are required, those tasks remain unsupported
for this candidate. Do not score a flame response as authored choice or quietly change
the task requirement after observing results.

## Participant prompts

Give goals without selecting values, alternatives, conditions, presets or a path through
the controls. The mode and language are the participant's choice. No answers from the
automated fixtures below are participant defaults.

| Core task | Neutral prompt | Evidence to record |
| --- | --- | --- |
| T45 item | Create a magic item involving flames as you intend it to work. Choose its limits, save a suitable revision and, if executable, try it privately. | Intended versus authored behavior; readiness chosen; private-test understanding; success/time/help/errors/defaults. |
| T45 conditional effect — manual candidate | Author an effect that changes a value only under a condition you choose. State what changes and when it ends. Save a complete manual instruction card and explain a case where it applies and a case where it does not. | Explicit value/condition/change/end; recognition of manual resolution; success/time/help/errors/defaults. |
| T45 choice — manual candidate | Author a choice with alternatives and consequences. Specify how many alternatives someone selects, save a complete manual instruction card, and explain how someone would make and resolve the choice. | Authored alternatives/consequences/cardinality; comprehension of manual use; success/time/help/errors/defaults. |
| T45 lore | Write and save a piece of lore without assigning unintended mechanics. Explain what the saved content does and does not execute. | Standalone descriptive revision; no inferred mechanics; success/time/help/errors/defaults. |

For the manual candidate tasks, disclose that this build supports manual instruction cards.
Do not coach which controls/values achieve success. Record the task wording actually used
and the scope decision before the first session. Supplemental conflict/access/recovery tasks
remain separate from the four-task denominator in the [study protocol](test-backlog-2026-09-29.md#5-deferred-human-backlog-and-t45-task-readiness).

## Engineering setup and repeatable reset

1. Use an isolated environment with PostgreSQL 16 and migrations M73–M78, the matching
   native RDL G1 1.1.0 host/worker, and CE_AUTHORING/CE_RUNTIME enabled only there. Record
   actual configuration/build identity; no production migration or flag change is implied.
2. Provision separate temporary accounts through the existing account workflow. Keep
   credentials out of the manifest and screenshots. Account setup, roster, attendance and
   deployment are **not completed** by this document. Store only participant codes in results.
3. Use a fresh private workspace/account per participant, with no authored answers, preset
   selection or previously chosen completion profile. Visiting the editor must create no draft.
4. For item sandbox tasks, seed only explicitly documented imported actor/target fixtures
   where required. Record their setup separately; never claim they are participant creations.
   The existing `native_world` automated fixture in `test_ce_native.py` is the engineering
   reference for isolated revisions, actors, resources, holder and worker setup.
5. Each participant creates their own draft for every task. Each mechanical trial uses a
   new sandbox with the exact selected revisions and fresh copies/resources. Do not overwrite
   or erase immutable revisions, command receipts or original observations to reset a task.
6. After a participant, sign out and discard that browser context. Preserve the private
   evidence under the study's retention/access arrangements, then use the next isolated
   account. A reset means fresh state, not deletion from a shared or production database.

## Engineering preflight and evidence separation

The new automated fixtures create their own accounts, drafts and state in disposable `ce_test`.
They cover all three manual profiles, the existing flame flow, tab loss, exact retry,
held-copy equip/use, optional timeout and manual clock-anomaly resolution. Their fixed names,
numbers and consequences are test inputs only.

Before a human session, verify the candidate hashes against the actual installed build;
record server/worker start, flags and device/browser versions. Confirm the required ≥8-person
novice/experienced roster and use the unchanged [result template](study-results-template.csv).
For eight participants the core denominator remains 32 tasks and ≥26 unassisted completions;
zero unnoticed creative defaults and resolution of recurrent confusion are separate gates.
There are currently **no participant results**. Automated passes do not fill that CSV.
