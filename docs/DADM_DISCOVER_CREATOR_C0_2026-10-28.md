# DAD-M C0 Discover — character creator evidence baseline

**Status:** complete, 2026-10-28. This phase records facts only.

## Input summary

The product owner approved [program v1](decisions/CHARACTER_CREATOR_PARITY_PROGRAM_V1.md) with “Go ahead.” C0 must freeze the original 48-point scope into an evidence ledger and repeatable journey protocol before any creator feature milestone starts.

## Current state and relevant inventory

- The [October 18 inventory](DADM_DISCOVER_CHARACTER_CREATOR_2026-10-18.md) enumerates 48 capabilities and the P1–P13 roadmap. P1–P12 implementation records exist; they describe delivered slices and candid gaps, but do not form an item-level acceptance ledger. P13 has no equivalent complete acceptance record.
- The [October 28 creator audit](DADM_DISCOVER_CREATOR_UX_PARITY_2026-10-28.md) compared live-equivalent assets with Chromium at 390×844. It documented the first class choice below the initial viewport and a 14,765px all-fields Quick page. The [program Discover](DADM_DISCOVER_CHARACTER_CREATOR_PROGRAM_2026-10-28.md) mapped gaps by matrix section, but not each item to an observable proof.
- Existing browser fixtures use disposable local databases and accounts: `tests/test_srd_creator_browser.py` covers guided creation and mobile quick layout; `tests/test_creation_engine_eagle_browser.py` covers author→global Duckfolk→unrelated player→sheet/table; `tests/test_sheet_to_table_browser.py` covers a two-tab live roll. These are stronger than P-document claims but each proves only its own assertions.
- The C0 baseline rerun in `vtt-test:browser` passed the four selected Chromium cases: guided Fighter, quick/mobile layout, Duckfolk publication journey, and sheet→table roll (**4 passed, 37 warnings, 55.50 s**). No product or production data was changed. The warnings were framework deprecations and existing SQLAlchemy relationship warnings; they did not fail the run.
- `vtt/static/js/srd-creator.js` and `srd-creator-steps.js`, `vtt/rules_content/creator_sources.py`, `vtt/characters/srd_creator.py`, the P1–P12 records and the existing screenshots provide code/doc proof paths. There is no versioned 48-row machine-checkable ledger or documented C0 proof convention yet.

## Dependencies and constraints

- Program v1 is the approved scope. C0 may add documentation and a validation harness; it may not change creator behavior, schemas, production flags or deploy an image.
- The existing published German SRD 5.2.1 corpus is CC BY 4.0; the [ruleset program](decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md) pins its source/attribution. The external product benchmark is behavior from [D&D Beyond's public guide](https://www.dndbeyond.com/posts/1059-how-to-create-your-first-dungeons-dragons) and [October 2026 changelog](https://www.dndbeyond.com/changelog/), not third-party content or visual assets. Signed-in competitor detail was not inspected.
- The current proof screenshots are [creator phone](proofs/creator-ux-audit-2026-10-28/mobile-first-viewport.png), [Duckfolk publication and DM](DADM_MONITOR_AGENTIC_FRICTION_2026-10-28.md), and [sheet phone](proofs/sheet-layout-2026-10-28/phone-first-viewport.png). They are dated evidence, not new C0 screenshots.

## Risks and assumptions

| Severity | Finding | Disposition for Apply |
|---|---|---|
| Medium, evidence | Four browser cases do not prove all 48 broad capabilities. | Use `partial` or `open` unless an item's full criterion has direct proof; never infer acceptance from a P-document alone. |
| Medium, ownership | Historical records use different owner labels and lack item-level acceptance owners. | Assign the Roll Drauf product-owner role for acceptance and a technical area for follow-up; do not invent named people. |
| Low, benchmark | Public D&D Beyond material may omit signed-in details. | Freeze the dated public behavior and mark unobserved competitor details as unverified. |
| Low, environment | Baseline passed in the existing test image, while host Python lacks pytest. | Record the exact container command and image; no new dependency is required. |

## Open questions and next step

No question blocks the C0 design. The first later product decision is what defaults the C2 Quick path may make for rule choices; C4 owns the prerequisite rule completeness. Apply should define the ledger fields, status semantics, proof references, owner roles, validator, six journey IDs, and acceptance checks. The medium evidence and ownership findings are resolved for C0 by explicit conservative statuses and role ownership; feature gaps remain owned by C1–C10.

**Artifacts (retention):** this Discover record (keep); linked prior audits/proofs (keep); isolated test output summarized above (keep as result, disposable test data deleted). **Next step:** C0 Apply design.
