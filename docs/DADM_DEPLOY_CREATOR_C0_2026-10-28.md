# DAD-M C0 Deploy — evidence baseline delivered

**Status:** complete, 2026-10-28. This is a documentation and validation-harness Deploy, with no application or production release.

## Input summary

The owner approved [program v1](decisions/CHARACTER_CREATOR_PARITY_PROGRAM_V1.md) and C0 [Apply](DADM_APPLY_CREATOR_C0_2026-10-28.md) defined a conservative 48-item ledger, a standard-library validator and a six-journey protocol. The [Discover record](DADM_DISCOVER_CREATOR_C0_2026-10-28.md) identified existing test paths and evidence gaps.

## Implementation summary and files changed

- Marked `docs/decisions/CHARACTER_CREATOR_PARITY_PROGRAM_V1.md` approved with the user's 2026-10-28 “Go ahead” as the approval record. No milestone scope or dependency changed.
- Added `docs/creator-parity-ledger-v1.csv` with one owner, technical area, severity, observable criterion, evidence path, current finding and follow-up milestone for each matrix item 1–48.
- Added `tools/check_creator_parity_ledger.py` to validate the ledger's schema, ID coverage, evidence paths/test nodes and alignment with program v1's C1–C10 matrix trace.
- Added `docs/CREATOR_PARITY_PROTOCOL_V1.md` with a dated public behavior benchmark, rights boundary, isolated fixtures, six journey IDs and proof/measurement conventions.
- Added phase records `docs/DADM_DISCOVER_CREATOR_C0_2026-10-28.md`, `docs/DADM_APPLY_CREATOR_C0_2026-10-28.md`, this Deploy record and the following Monitor record.

## Verification and proofs

| Check | Result |
|---|---|
| `python3 tools/check_creator_parity_ledger.py` | Passed: exactly 48/48 rows; 43 partial and 5 open; all owners and evidence paths valid. |
| `python3 -m py_compile tools/check_creator_parity_ledger.py` | Passed. |
| Temporary negative ledger fixtures | Passed: missing ID 48 and missing evidence path are both rejected. |
| Local Markdown link/path check for new phase and protocol docs | Passed: no missing local target. |
| Four focused Chromium cases in `vtt-test:browser` | Passed: **4 passed, 37 warnings, 55.50 s**. Command and fixture boundaries are recorded in the [protocol](CREATOR_PARITY_PROTOCOL_V1.md). |
| `git diff --cached --check` after staging | Passed: no whitespace errors. |

The Chromium run used disposable fixture databases and synthetic users. It covered a guided Fighter finalization, existing quick/mobile layout, an unrelated-player Duckfolk publication journey, and a live two-tab sheet roll. It did **not** prove the entire 48-point matrix, a real three-decision Quick Build, or a production write path. Existing screenshot evidence remains linked from the protocol; C0 did not create new screenshots. The warnings were existing framework deprecations and SQLAlchemy relationship warnings, not test failures.

## Acceptance checklist

- [x] Program approval is recorded without widening v1.
- [x] Ledger has all 48 unique IDs and every row has an owner role, criterion, evidence reference, severity/finding and owning milestone.
- [x] Validator rejects missing IDs/paths and mismatched milestone ownership by design; valid ledger passes.
- [x] Six journeys and 390×844/desktop proof rules are documented, with current pass/fail limits explicit.
- [x] SRD attribution and competitor-behavior-only rights boundaries are stated.
- [x] No creator code, database, Docker image or production service changed.

**Risks and assumptions:** medium remaining product gaps are represented as partial/open ledger rows and owned by C1–C10; no C0 evidence gap is hidden. **Artifacts (retention):** approved plan, ledger, validator, protocol and phase records (keep); test data (discarded by fixtures). **Next step:** C0 Monitor validates the staged artifacts and recommends C1 Discover.
