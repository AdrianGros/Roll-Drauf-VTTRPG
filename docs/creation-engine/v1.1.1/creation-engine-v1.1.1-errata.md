# Creation Engine v1.1.1 — errata E1 (G0 high-severity closures)

24 September 2026. Approved by Adrian (IT project lead / architecture lead) the same day. Decision
record: `dadm/artifacts/approvals/approval_creation_engine_g1_2026-09-24.md`.

v1.1.1 = v1.1 (Audit Candidate 1) plus the three closures below. Every other normative sentence of
v1.1 is unchanged. The v1.1 package in `../v1.1/` stays as the historical audit candidate, with its
original hashes.

## Changes

| Finding | Spec text changed | Wire contract changed | New acceptance |
| --- | --- | --- | --- |
| **G0-01** Unkeyed digests disclose restricted facts | §6 adds context tokens, and a content digest only goes to readers of all hashed content. §8 adds public receipts (no outcome digest, filtered event IDs, no omitted count). §10 renames the context digest to context token. §14 adds digests and tokens to the output boundary. The T10 wording changes | New `ContextToken` type (`ctx:` + 43 base64url characters). `PendingDecision.contextDigest` and `ResolveDecisionPayload.contextDigest` become `contextToken`. New `PublicReceipt` without `outcomeDigest`. The internal `Receipt` is never delivered as-is | T47 |
| **G0-02** Migration authority per character vs per scope | §5: migration state belongs to the RuntimeScope, all instances switch together, and per-character approvals are cutover preconditions. LEGACY/SHADOW engine evaluation is preview-only. A character without a campaign migrates in its owner's sandbox. A later campaign attach needs the transfer protocol, else `SCOPE_TRANSFER_UNSUPPORTED` | — | T48 |
| **G0-03** Invocation cannot name its source occurrence | §4: every occurrence reference on the wire is an `InstanceRef`. §8: `actorInstance` selects the actor, and `sourceInstance` names the occurrence that owns the activity and pays its costs | `InvokeActivityPayload`: `actorInstanceId` becomes `actorInstance` (`InstanceRef`), and `sourceInstance` (`InstanceRef`) is added and required. `AdjustResourcePayload.instanceId` becomes `instance` (`InstanceRef`) | T49 |

Traceability updates:

- The contract version is `1.1.1` (`urn:rolldrauf:creation-engine:contracts:1.1.1`).
- The G1 exit evidence adds T47–T49.
- Requirement mappings: CE-POLICY-01 adds T47, CE-MIGRATE-01 adds T48, CE-IDENTITY-01 adds T49.
- §23 gains a G0-closure table.
- Registry addendum A1 is retargeted to 1.1.1.

## Verification (document and schema checks only; no engine tests)

- The schema is valid Draft 2020-12. The updated `InvokeActivity` example and a `ResolveDecision`
  example with a context token both validate. A `PublicReceipt` validates, and one carrying an
  `outcomeDigest` is rejected.
- 10 negative cases are rejected. These are v1.1's five (spoofed principal, missing epoch, unknown
  operation, malformed hash, unknown payload field) plus five new ones:
  - contract version `1.1`;
  - a bare actor ID;
  - a missing source occurrence;
  - the old `contextDigest` field;
  - an unkeyed `sha256:` value sent as a context token.
- All 49 acceptance cases in JSON match the §21 table text. Every T-ID has a gate and a requirement.
- Details: `creation-engine-v1.1.1-verification.json`. Hashes: `review-package-manifest.json`.
- No PDF was produced for v1.1.1. The Markdown is the normative source.

## Still open from the G0 audit (not part of E1)

G0 exit needs the spec criterion ("no unresolved high-risk contradiction in proposed slice"). E1
meets it. The DAD-M phase transition additionally requires every medium-or-higher finding to be
resolved or explicitly accepted.

| Finding | Severity | Owner | Status |
| --- | --- | --- | --- |
| G0-04 suspension clocks, G0-05 commandId/idempotencyKey, G0-06 expectedScopeVersion, G0-07 epochs, G0-08 control/operator, G0-09 AdjustResource bounds, G0-10 formula schema, G0-12 inert legacy metadata, G0-14 manual-play coverage | medium | Adrian | Closures proposed in the audit; awaiting acceptance (would become errata E2) |
| G0-11 wire contracts for G1 commands | medium | Matt (review) | Addendum A1 drafted and retargeted to 1.1.1 |
| G0-13 token movement and the scope gate | medium | Matt (product decision) | Open |
| G0-15 reaction candidate order | medium | Adrian | Only affects G2; can be accepted as deferred |
| G0-16 … G0-20 | low | Adrian | Allowed with notes (DAD-M); fold into E2 |
