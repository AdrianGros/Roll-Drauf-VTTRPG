# Creation Engine v1.1.4 — errata E1–E4; G0 passed

24 September 2026. Decision record: `dadm/artifacts/approvals/approval_creation_engine_g1_2026-09-24.md`.

- **v1.1.4** = v1.1 (Audit Candidate 1) + E1 (high) + E2 (medium) + E3 (low) + E4 (product-owner
  decisions).
- **Where E1–E3 are detailed.** `../v1.1.3/creation-engine-v1.1.3-errata.md` has them, unchanged here.
- **Older packages.** `../v1.1/`, `../v1.1.1/`, `../v1.1.2/` and `../v1.1.3/` stay unchanged, with
  their original hashes.
- **Wire contract.** It stays **1.1.3** (`urn:rolldrauf:creation-engine:contracts:1.1.3`, in
  `../v1.1.3/`); E4 changes no wire shape. Registry addendum A1 targets 1.1.3.

## E4 — product-owner decisions (Matt, relayed by Adrian, 2026-09-24)

| Finding | Decision | Spec change | Evidence |
| --- | --- | --- | --- |
| G0-13 token movement and the scope gate | Adopt the audit's proposed closure | §9: the gate covers token movement only on maps whose pinned geometry profile declares spatial mechanics; elsewhere movement is ungated representation state. §16: gated movement and enter/leave events exist only on such maps | T55 (G1): ungated move on a plain map. T56 (G5): SCOPE_BUSY on a map with spatial mechanics |
| G0-11 wire contracts for G1 commands | Registry addendum A1 approved (non-author review) | Addendum A1 becomes an approved companion wire contract | Addendum verification (24 operations) |

## G0 result

**G0 passed on 24 September 2026.**

- Every G0 finding is closed: G0-01…G0-03 (E1), G0-04…G0-10, G0-12, G0-14 and G0-15 (E2),
  G0-16…G0-20 (E3), and G0-11 and G0-13 (E4).
- The spec criterion ("no unresolved high-risk contradiction in proposed slice") and the DAD-M
  transition rule (no open medium-or-higher finding) are both met.
- G1 may enter Deploy under the approved plan.

## Verification

- All 56 acceptance cases in JSON match the §21 table text. Every T-ID has a gate and one of 20 requirements.
- The unchanged 1.1.3 wire schema is valid, and all 15 of its negative cases stay rejected (see
  `../v1.1.3/creation-engine-v1.1.3-verification.json`).
- All 24 registry addendum examples validate against it.
- Details: `creation-engine-v1.1.4-verification.json`. The manifest also pins the external companions by hash.
