# Creation Engine v1.1.3 — errata E1 + E2 + E3

24 September 2026. All three errata were approved by Adrian (IT project lead / architecture lead)
the same day. Decision record: `dadm/artifacts/approvals/approval_creation_engine_g1_2026-09-24.md`.

- **v1.1.3** = v1.1 (Audit Candidate 1) + E1 (G0 high findings) + E2 (G0 medium findings put to
  Adrian) + E3 (G0 low findings). Every other normative sentence of v1.1 is unchanged.
- **Older packages.** `../v1.1/` (historical audit candidate), `../v1.1.1/` and `../v1.1.2/`
  (superseded) stay unchanged, with their original hashes.
- **Contract version** is `1.1.3` (`urn:rolldrauf:creation-engine:contracts:1.1.3`). Registry
  addendum A1 is retargeted to it.

## E1 — high findings

| Finding | Spec change | Wire change | Evidence |
| --- | --- | --- | --- |
| G0-01 unkeyed digests disclose restricted facts | §6 context tokens; §8 public receipts; §10 context token; §14 output boundary | `ContextToken`, `contextToken`, `PublicReceipt` | T47 |
| G0-02 migration authority per character vs per scope | §5 scope-level migration state, cutover preconditions, `SCOPE_TRANSFER_UNSUPPORTED` | — | T48 |
| G0-03 invocation cannot name its source occurrence | §§4, 8 `InstanceRef` for occurrences, `sourceInstance` | `actorInstance`, `sourceInstance`, `AdjustResourcePayload.instance` | T49 |

## E2 — medium findings

| Finding | Spec change | Wire change | Evidence |
| --- | --- | --- | --- |
| G0-04 two suspension clocks | §10: SUSPENDED at the mandatory deadline; reissue is an operator command | — | T11 |
| G0-05 `commandId` vs `idempotencyKey` | §8: correlation ID outside the request digest; retries reuse the key | — | T06, T07 |
| G0-06 `expectedScopeVersion` semantics | §8: exact match for mechanical commands; `ResolveDecision` bound by decision version and token | — | T04, T09–T12 |
| G0-07 epochs | §§9, 12: internal fencing epochs; restore increments the authority epoch | — | T05, T06, T42 |
| G0-08 control and operator undefined | §§5, 14: `controls` / `operates` relations and VTT default grants | — | T09, T24 |
| G0-09 `AdjustResource` at bounds | §7: mandatory adjustment bound policy, `RESOURCE_BOUND_EXCEEDED` | — | T02, T04 |
| G0-10 formula schema vs prose | §6: core function set; boolean logic in Predicates | `Predicate`, `Formula` description | T14, T15, T43 |
| G0-12 inert legacy metadata | §5: `legacyMetadata` container | `LegacyMetadata` | T01 |
| G0-14 manual play untested | §23: CE-MANUAL-01 | — | T50 (G1) |
| G0-15 reaction candidate order | §10: candidate list fixed per slot; operator reorder restarts the slot | — | T51 (G2) |

## E3 — low findings

| Finding | Spec change | Wire change | Evidence |
| --- | --- | --- | --- |
| G0-16 no path from PROPOSED to CANCELLED | §9: `PROPOSED → CANCELLED` on withdrawal or precommit expiry; no cost, no checkpoint, admission count released | — (enum unchanged) | T52 (G1) |
| G0-17 capacity/budget responses ambiguous | §17: four rows (413 `PAYLOAD_TOO_LARGE`, 422 `BUDGET_EXCEEDED` at admission, 429 `ADMISSION_LIMIT`, 422 `BUDGET_EXCEEDED` mid-action with status). §18: 503 never reports a deterministic budget failure | error codes only | T53 (G1) |
| G0-18 forward-clock anomaly undefined | §10: shared time authority read once per commit; 30 s watermark heartbeat while decisions are open; anomaly = gap beyond interval + tolerance (default 30 s); affected actions SUSPENDED for operator review; a backward step never reopens | — | T54 (G1) |
| G0-19 no requirement for ruleset independence | §23: CE-RULESET-01 → T34; T34 removed from CE-GUIDE-01 | — | T34 (G2) |
| G0-20 naming drift; non-UTC timestamps | §10: PendingDecision fields named as in the schema; slot consumption is a slot property | `Timestamp` requires UTC `Z` | Schema checks |

## Verification (document and schema checks only; no engine tests)

- The schema is valid Draft 2020-12.
- These examples validate:
  - the `InvokeActivity` example (`actorInstance`, `sourceInstance`);
  - a `ResolveDecision` with a context token;
  - a `PublicReceipt`;
  - a compound Predicate;
  - a `PendingDecision` with UTC timestamps.
- 15 negative cases are rejected:
  - spoofed principal;
  - missing epoch;
  - unknown operation;
  - malformed hash;
  - unknown payload field;
  - superseded contract version;
  - bare actor ID;
  - missing source occurrence;
  - old `contextDigest` field;
  - unkeyed digest as token;
  - three malformed Predicates;
  - a timestamp with an offset;
  - a timestamp without a zone.
- A `PublicReceipt` carrying an outcome digest is rejected.
- All 54 acceptance cases in JSON match the §21 table text. Every T-ID has a gate and one of 20 requirements.
- Details: `creation-engine-v1.1.3-verification.json`. Hashes: `review-package-manifest.json`. No PDF
  was produced; the Markdown is the normative source.

## Still open with the product owner

These are the only open G0 findings. G0 is recorded as passed once both are closed.

| Finding | Owner | Status |
| --- | --- | --- |
| G0-11 wire contracts for G1 commands | Matt (non-author review) | Addendum A1 drafted and retargeted to 1.1.3 |
| G0-13 token movement and the scope gate | Matt (product decision) | Open. §9 still gates all token movement |
