# DAD-M C0 Apply — evidence ledger and journey protocol

**Status:** design complete, 2026-10-28. No implementation in this phase.

## Input summary and design boundary

Use [C0 Discover](DADM_DISCOVER_CREATOR_C0_2026-10-28.md) and approved [program v1](decisions/CHARACTER_CREATOR_PARITY_PROGRAM_V1.md). C0 delivers a conservative, repeatable baseline for 48 capabilities. It changes no character mechanics, UI, database, image or production service.

## Target state and artifacts

1. `docs/creator-parity-ledger-v1.csv` has exactly one row for each October 18 matrix ID 1–48. Each row has `id`, the original `capability` (compact paraphrase), `status`, `severity`, `acceptance_owner`, `area_owner`, an observable `criterion`, `evidence_refs`, `next_milestone`, and a present-tense `finding`. The acceptance owner is the **Roll Drauf product-owner role**; area owners are Creator UX, Rules, Sheet/VTT, Character lifecycle or Content/CE. A role is explicit ownership without inventing a person.
2. `tools/check_creator_parity_ledger.py` is a Python standard-library validator. It rejects duplicate/missing IDs, empty required fields, invalid statuses or milestone IDs, missing local evidence paths, and an `accepted` row lacking a test/proof reference. The command `python3 tools/check_creator_parity_ledger.py` works without the application virtualenv.
3. `docs/CREATOR_PARITY_PROTOCOL_V1.md` freezes six journey IDs, fixtures/accounts, phone/desktop measurements, artifact naming, provenance and privacy rules, and a dated public D&D Beyond behavior reference. Existing screenshots and Chromium tests are the C0 baseline. Future milestones attach new proofs to this protocol rather than rewriting historical results.
4. Program v1 status becomes `approved`, with the user's “Go ahead” and date recorded. The approved scope and dependency map do not change.

## Status and proof contracts

- `accepted`: the full row criterion has direct current evidence and the acceptance owner has signed it off. A past P-document or a passing test of only one subfunction is insufficient.
- `partial`: at least one relevant path exists but a subfunction or direct acceptance proof remains. The `finding` names the gap.
- `open`: no player-facing path meeting the criterion is present. An evidence reference may point to the limiting current code or audit.
- `inapplicable`: only after a recorded product-owner exception; no C0 row uses it.
- `evidence_refs` is a semicolon-separated list of repo-relative paths, optionally suffixed with `::pytest_node`. All paths must exist in this checkout. A path is an evidence pointer, not itself an acceptance claim. `next_milestone` is one owner among C1–C10, chosen from program v1's trace; C11 is the final gate.

## Six journey IDs and measurement contract

| ID | User journey | C0 baseline / future proof |
|---|---|---|
| J1 | Novice Guided Fighter on 390×844 phone, draft/reload/finalize | Fresh `test_guided_flow_builds_a_valid_fighter`; phone first-choice screenshot is dated earlier evidence. C1 adds focus/field-jump proof. |
| J2 | Three-decision Quick spellcaster, inspect/edit defaults | Current `test_quick_mode_and_mobile_layout` proves the existing all-fields mode, **not** J2 completion. C2 owns it. |
| J3 | Filtered Premade and class/species/level-constrained Random start | No complete current journey; C3 owns it. |
| J4 | Origin/feat subchoices, granted spells/tools, multiclass progression | Partial rule/API evidence; C4 owns complete proof. |
| J5 | Author publishes a validated global item; unrelated player selects it; DM sees provenance | Fresh Duckfolk Species browser journey passes; C6–C8 expand access and types. |
| J6 | Finalized sheet, starting gear/resources, bound two-tab roll, token and reconnect | Fresh sheet→table roll passes; C5 and C9 own the missing resource/token details. |

At 390×844 and 1280×900, record viewport dimensions, first actionable control's top/bottom, horizontal document overflow, step focus, current URL, finalization result, sheet/table destination, page errors and screenshots at first choice, blocker recovery, final sheet, and DM/table result. Keep a proof next to its milestone phase record under `docs/proofs/creator-parity/<milestone>/<journey>/`; include test command, commit and timestamp. Tests use disposable accounts/databases; screenshots must not contain real character prose or private content. No production write is required for C0.

## Rights, interfaces and rollout

The behavioral benchmark is D&D Beyond's [public first-character guide](https://www.dndbeyond.com/posts/1059-how-to-create-your-first-dungeons-dragons) and [October 2026 changelog](https://www.dndbeyond.com/changelog/). The SRD corpus and attribution stay governed by the [approved ruleset program](decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md). The ledger contains original capability descriptions and repo evidence, no copied competitor assets or non-SRD rules. C0 has no runtime/API contract change and no deployment flag. C1 onward uses the ledger as a read-only acceptance baseline; major benchmark or scope changes require plan v2.

## Acceptance and Deploy handoff

- `python3 tools/check_creator_parity_ledger.py` reports 48/48 valid rows and no unresolved paths.
- All four selected baseline Chromium tests pass in the existing test image; no skipped baseline test is counted as passed. The phone test controls horizontal overflow; the first-choice-below-fold finding remains `partial`, not falsely accepted.
- Every row has an owner role, criterion, evidence pointer, severity-bearing finding where applicable, and one mapped owning milestone. `accepted` is reserved until full proof and owner sign-off.
- The protocol clearly distinguishes passing slices from unimplemented journeys, records six IDs and provenance/rights constraints, and permits later milestones to append proof without rewriting this baseline.
- Only the four files above and phase records may change. Run `git diff --check`, validator, local-link check, and the focused browser command; record any gap in Deploy. Then Monitor verifies artifacts and recommends C1 Discover.

**Risks and tradeoffs:** medium evidence incompleteness is controlled by conservative statuses; low risk of CSV drift is controlled by the validator. A CSV is intentionally simple and diffable; it is not a new product database. **Artifacts (retention):** this Apply record (keep), planned CSV/protocol/validator (keep). **Next step:** C0 Deploy of documents and validator, then Monitor; no creator feature work in C0.
