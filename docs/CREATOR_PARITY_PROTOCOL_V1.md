# Character creator parity protocol v1

**Frozen:** 2026-10-28 for C0 under [approved program v1](decisions/CHARACTER_CREATOR_PARITY_PROGRAM_V1.md). This is a behavior and evidence protocol, not a claim that parity is complete. The [48-row ledger](creator-parity-ledger-v1.csv) is its scope index.

## Benchmark and rights boundary

The public [D&D Beyond first-character guide](https://www.dndbeyond.com/posts/1059-how-to-create-your-first-dungeons-dragons) describes Standard, Quick Build from species/class/name, parameterized Randomize and Premade. Its [October 2026 changelog](https://www.dndbeyond.com/changelog/) confirms active Quickbuilder and Premade browsing with Category/Class/Level/Species filters. The [2026 roadmap](https://www.dndbeyond.com/posts/2132-d-d-beyonds-2026-development-roadmap) states intentions for deeper building; those are not treated as shipped requirements. No signed-in competitor session was inspected. Later competitor changes are new planning input, not silent acceptance changes.

Roll Drauf may match **functions and user outcomes** using its own UI, code and words. Content is limited to the published German SRD 5.2.1 under CC BY 4.0 and original or properly licensed publications. Preserve the SRD attribution route and source pins. Do not copy competitor assets, proprietary rule text, UI screenshots or account data into fixtures or proofs.

## Evidence statuses

`accepted` requires direct proof of the **entire** row criterion and product-owner sign-off recorded in a milestone Monitor result. `partial` means a working slice exists but the full criterion or proof does not. `open` means no qualifying player-facing path exists. `inapplicable` requires an owner-approved exception in the ledger finding and Monitor record. A passing test of a narrower journey is evidence of that slice, not automatic acceptance of all related rows. C0 starts with **43 partial and 5 open; 0 accepted**.

Each milestone may advance a row only after attaching a test node or screenshot/protocol record and noting the product-owner decision. The validator checks syntax and paths; a reviewer checks whether the evidence actually proves the criterion. Keep historic proofs immutable and add new artifacts with a new milestone/date. The `next_milestone` is the single accountable owner from plan v1; cross-cutting work may appear in other cycles without changing ownership silently.

## Disposable accounts and environments

| Journey | Fixture identity and isolation |
|---|---|
| J1–J4 | `tests/test_srd_creator_browser.py` creates a SQLite database in `tmp_path` and a synthetic wizard account; Chromium uses a test JWT cookie. No production account or campaign. |
| J5 | `tests/test_creation_engine_eagle_browser.py` creates synthetic DM/player/contributor accounts and campaign, publishes Duckfolk in its isolated test database, and tears it down. The built Eagle bundle is required. |
| J6 | `tests/test_sheet_to_table_browser.py` creates synthetic DM/player accounts, a campaign and two sessions in `tmp_path`; it binds a sheet to the correct test table. |

Use the existing `vtt-test:browser` image with the checkout mounted at `/app`. The host Python currently lacks pytest, while the test image has pytest 9.0.3 and Chromium. The exact C0 baseline command is:

```bash
docker run --rm --network host -v /home/admin/projects/roll-drauf-vtt-eagle:/app -w /app vtt-test:browser python3 -m pytest -q \
  tests/test_srd_creator_browser.py::test_guided_flow_builds_a_valid_fighter \
  tests/test_srd_creator_browser.py::test_quick_mode_and_mobile_layout \
  tests/test_creation_engine_eagle_browser.py::test_duckfolk_publish_creator_sheet_and_live_action \
  tests/test_sheet_to_table_browser.py::test_a_sheet_roll_in_a_second_tab_appears_live_at_the_table_and_stays
```

The 2026-10-28 C0 run passed **4/4 in 55.50 seconds** with 37 pre-existing deprecation/SQLAlchemy warnings. This proves the selected isolated paths, not live production publication or all 48 rows. A future production write-path smoke needs its own scoped approval and disposable identities; C0 uses no production write.

## Six repeatable journeys

| ID | Start and actions | Required end evidence | Current C0 state / owning milestones |
|---|---|---|---|
| J1 | At 390×844 start Guided; choose Fighter and a legal origin; visit each section; reload a saved draft; resolve a blocker; finalize. | Correctly saved choices and character ID; legal evaluation; first-choice geometry; no horizontal overflow; focus and blocker-control jump. | Fighter finalization passes. First class choice remains below initial viewport and exact blocker jump is missing. C1. |
| J2 | Start Quick at level 1; choose class and species and name; inspect defaults; edit one detail; finalize and open sheet. | Three mandatory decisions; legal generated provenance; reload persistence; playable sheet. | Existing Quick renders all eight sections; mobile overflow test passes but J2 does not. C4 then C2. |
| J3 | Filter Premades by category/class/level/species; choose one; separately constrain Random by level/class/species; edit both drafts. | Template/source pin and random seed or reproducible policy; valid evaluator result; clear unavailable-source state. | No complete journey. C3. |
| J4 | Build an origin/feat combination with required subchoices; advance and multiclass; inspect spells/tools/languages on sheet. | Blockers for missing choices; granted mechanics visible after reload and level-up; old character repair path. | Core rules/progression exist; subchoice and grant gaps remain. C4. |
| J5 | Contributor authors and validates Duckfolk; publishes globally; unrelated player selects it; DM inspects provenance and action. Repeat for each new playable type. | Publication/revision/scope proof; private revision invisibility; sheet and table effects; DM DTO display. | Isolated Duckfolk journey passes; DM action summary mismatch remains documented. C6–C8 and C9. |
| J6 | Finalize Fighter and caster; open sheet with starting gear/resources; spend/use/rest; roll from a second tab to bound table; reconnect token. | No duplicate gear; correct resource recovery; named destination and one chat roll; sheet/token/DM agreement. | Two-tab roll passes; gear handoff and resource accounting are incomplete. C5 and C9. |

## Capture and measurement rules

At minimum use a 390×844 phone viewport and a 1280×900 desktop viewport with Chromium. Record device scale factor, reduced-motion setting, test commit, timestamp, route, account role, viewport, `document.documentElement.scrollWidth`, actionable control bounding rectangle, focused element after navigation, finalizer HTTP/result, page errors and table destination. For a phone first action, record whether the entire actionable choice is within `0..844` without scrolling. A screenshot alone does not establish keyboard focus or server legality; pair it with DOM/API assertions.

Store milestone proofs under `docs/proofs/creator-parity/<milestone>/<journey>/` with names such as `phone-first-choice.png`, `blocker-recovery.png`, `sheet-ready.png`, `table-roll.png`, and a short `run.md` containing command, commit, date, assertions and any skipped checks. Keep current dated proofs where they are: [creator first viewport](proofs/creator-ux-audit-2026-10-28/mobile-first-viewport.png), [Duckfolk friction](DADM_MONITOR_AGENTIC_FRICTION_2026-10-28.md), [sheet phone](proofs/sheet-layout-2026-10-28/phone-first-viewport.png). Use synthetic character text and accounts. Do not put JWTs, credentials, private homebrew prose or real user data in artifacts or aggregate telemetry.

Before a row becomes `accepted`, compare the proof to its exact ledger criterion, verify no newly failing related journey, and record the product-owner sign-off in the owning milestone Monitor. The final C11 gate checks all 48 rows and all six journeys; it does not retroactively reinterpret a partial C0 baseline as success.
