# Human Decision Record — Creation Engine G1 pre-authorization

- **Milestone / phase:** Creation Engine G1 · Discover + Apply (no Deploy authorized)
- **Trigger:** DAD-M human-decision triggers. These are a high privacy finding (G0-01), dependency
  changes (D4), and a cross-gate scope ruling (D5). Spec §22 also requires a pre-authorization
  package.
- **Evidence:** `dadm/artifacts/programs/milestone_program_creation_engine_g1.md`,
  `docs/creation-engine/audits/creation-engine-v1.1-g0-audit-2026-09-24.md`,
  `docs/creation-engine/addenda/creation-engine-v1.1-registry-addendum-a1.md`.
- **Decider:** Adrian (IT project lead), 2026-09-24, unless noted otherwise.

| ID | Question | Decision | Value |
| --- | --- | --- | --- |
| D1 | Who runs the G0 audit | Claude runs it | **approve**. Done 2026-09-24. Result: not passed; closures proposed |
| D2 | Roles | Product owner Matt; IT project lead Adrian; project team = Legendary Rock + all `IT` role holders | **approve**. The spec-role mapping in plan §13 is confirmed (second reply, see below) |
| D3 | G1 test ruleset | Roll Drauf Light G1 subset (recommendation) | **approve** |
| D4 | Dependencies and PostgreSQL test harness | `rfc8785`, `jsonschema`, `hypothesis` (dev), disposable PostgreSQL 16 + 2-process harness, Redis message queue | **approve** |
| D5 | T-ID applicability rulings | T13 partial, T16 → G2, T26 archive sub-case → G3; all others in full (plus T47–T49) | **approve** |
| D6 | G1 magic item: flame sword + private curse | §24 traces as fixtures | **approve** |
| D7 | Wire contract for authoring and other G1 commands | Research and draft a tailored addendum in clean-code structure | **approve (modify)**. Addendum A1 drafted; needs non-author review (Matt) |
| D8 | Locales | German, English, French | **approve (modify)**: three locales instead of two |
| G0-01…G0-03 | Closures for the three high audit findings | Adopt as v1.1.1 errata E1 | **approve**. Published as `docs/creation-engine/v1.1.1/` |
| G0-04…G0-10, G0-12, G0-14, G0-15 | Closures for the medium audit findings put to Adrian | Adopt as errata E2. G0-15 is tested in G2 (T51) | **approve** (third reply: "medium are approved"). Published as `docs/creation-engine/v1.1.2/` |
| G0-16…G0-20 | Low audit findings | "Low findings matter": map each to a closure, then adopt the map as errata E3 | **approve** (fourth reply: "i approve"). Published as `docs/creation-engine/v1.1.3/`; adds T52–T54 to G1 and CE-RULESET-01 |

Second reply, 2026-09-24: "yes yes and approved". It was read as D4 = yes, D5 = yes, and "approved"
covering the remaining open asks: D6, the three G0 closures, and the D2 mapping. Correct this
record if that reading is wrong.

Fifth reply, 2026-09-24: "its imp time mat gave his go". It was read as follows:

- The product owner (Matt) approved registry addendum A1, closing G0-11.
- He approved the audit's proposed closure for G0-13: movement is gated only on maps with declared
  spatial mechanics.
- The IT project lead authorizes G1 implementation.

| ID | Question | Decision | Value |
| --- | --- | --- | --- |
| G0-11 | Review of registry addendum A1 | Approved as companion wire contract | **approve** (Matt) |
| G0-13 | Token movement and the scope gate | Adopt the audit closure as errata E4 (`docs/creation-engine/v1.1.4/`, T55 G1, T56 G5) | **approve** (Matt) |
| G0 | Gate exit | All findings closed (E1–E4); spec criterion and DAD-M transition rule met | **passed** 2026-09-24 |
| Deploy | G1 implementation authorization (spec §22) | Start with WP1 per the G1 plan | **approve** (Adrian, with Matt's go) |
