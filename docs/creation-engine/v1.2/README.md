# Creation Engine v1.2 — reconciled reading edition

**G1 remains in implementation.** The active contract is approved spec **v1.1.4**, core wire **1.1.3**, and registry **A1**. This edition consolidates those contracts with research; it does not reopen G0 or supersede the implementation authorization.

- [Full specification — PDF](creation-engine-v1.2.pdf) · [Markdown](creation-engine-v1.2.md) · [HTML](creation-engine-v1.2.html)
- [Reconciliation and cause report](creation-engine-v1.2-reconciliation-report.md) · [PDF](creation-engine-v1.2-reconciliation-report.pdf)
- [Approved core contract, exact wire 1.1.3 copy](creation-engine-v1.2-contracts.schema.json)
- [Approved registry A1](creation-engine-v1.1-registry-addendum-a1.md) · [schema](creation-engine-v1.1-registry-a1.schema.json)
- [56 approved cases, 18 proposals, and old-ID mapping](creation-engine-v1.2-acceptance.json)
- [Approved wire examples](creation-engine-v1.2-wire-examples.json)
- [Source manifest](creation-engine-v1.2-source-manifest.json) · [verification](creation-engine-v1.2-verification.json) · [package hashes](creation-engine-v1.2-package-manifest.json)

Read §§1–25 for the preserved approved body, §26 for research, §27 for clean coding against the adopted architecture, §28 for scoped changes, §29 for proposed acceptance, and §30 for the current implementation handoff. The three editorial updates to historical status/provenance are listed separately in `approved-body-editorial-changes.json`. No other approved-body edits are permitted by the verifier.

The earlier v1.2 rewrite is withdrawn. Its T47–T64 research scenarios are now T57–T74 so existing T01–T56 keep their approved meanings. Its seven-command wire 1.2 schema is not an implementation target. The current schemas retain all **27 approved command shapes**. The accepted single-presence direction remains assigned to spatial design; plain-map token movement in G1 remains presentation behavior.

The repository's [active-contract entry point](../README.md) and [implementation program](../../../dadm/artifacts/programs/milestone_program_creation_engine_g1.md) govern ongoing work. In a downloaded ZIP those repository links may be absent; frozen inputs provide the evidence used for this edition. Current status is a dated snapshot, not a live dashboard.

Regenerate documentation in a separate Python environment with jsonschema, referencing, Python-Markdown, WeasyPrint, and Poppler's pdftotext utility:

```sh
python build_reconciled_spec.py
python verify_reconciliation.py
python build_spec_documents.py
```

The verifier checks frozen inputs and, when available locally, current approved source hashes. A changed active contract fails verification. It preserves all approved case/requirement/gate identities, checks the unchanged schemas and A1 references, and rejects lost privacy/source-identity protections. No application imports, migrations or engine tests run. Inspect the final PDFs and record the sampled pages in verification before running `package_spec.py`.
