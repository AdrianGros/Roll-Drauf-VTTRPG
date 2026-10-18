# DAD-M Deploy: German SRD 5.2.1 Regelwerk R0

status: complete
date: 2026-10-15
profile: standard
phase: Deploy
milestone: R0 — Source, rights, and corpus foundation
approved-by: human product owner
approval: `docs/decisions/APPROVAL_REGELWERK_SRD_5_2_1_V1_2026-10-15.md`

## Input summary

Program version 1 was approved with authorization to implement R0 only. R0 establishes the
digest-pinned official German SRD source, exact attribution artifact, closed semantic schemas,
deterministic package identity, coverage reporting, negative security/source fixtures, and focused
tests. Reader UI, navigation, bulk transcription, publication, and mechanics integration remain
outside this deployment.

## Implementation summary

- Recorded the approved human decision and closed the Apply approval checkpoint.
- Added an external source-lock registry for `srd-5.2.1-de` containing the official source URL,
  publication/retrieval dates, 412-page count, verified PDF SHA-256, CC BY 4.0 identity and URL,
  attribution filename, and attribution SHA-256.
- Added the exact German attribution required by page 1 of the official source.
- Added closed JSON Schema 2020-12 contracts for source locks, package manifests, documents, safe
  semantic blocks, and stable rule references.
- Added the draft `srd-5.2.1-de` package manifest with all 412 source pages accounted for: legal
  and table-of-contents pages 1–4 are explicitly represented/excluded, and content pages 5–412
  are required across twelve official top-level sections.
- Added strict package validation for source-lock equality, attribution integrity, coverage
  partitioning, document inventory, schema closure, edition identity, deterministic document and
  package digests, stable rule IDs, safe plain-text content, table dimensions, internal references,
  publication completeness, and caller-pinned immutable package identity.
- Added a read-only CLI that prints deterministic package and coverage evidence.
- Added fourteen focused tests for the trusted path and required rejection cases.

## Files changed

Governance and phase records:

- `docs/DADM_APPLY_REGELWERK_SRD_5_2_1_2026-10-15.md`
- `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`
- `docs/decisions/APPROVAL_REGELWERK_SRD_5_2_1_V1_2026-10-15.md`
- `docs/DADM_DEPLOY_REGELWERK_SRD_5_2_1_R0_2026-10-15.md`

Content foundation:

- `vtt/rules_content/__init__.py`
- `vtt/rules_content/validator.py`
- `vtt/rules_content/source-locks.json`
- `vtt/rules_content/schemas/regelwerk-source-locks-v1.schema.json`
- `vtt/rules_content/schemas/regelwerk-package-v1.schema.json`
- `vtt/rules_content/schemas/regelwerk-document-v1.schema.json`
- `vtt/rules_content/srd-5.2.1-de/manifest.json`
- `vtt/rules_content/srd-5.2.1-de/attribution.txt`
- `vtt/rules_content/srd-5.2.1-de/documents/.gitkeep`
- `tools/validate_regelwerk.py`
- `tests/test_regelwerk_package.py`

No dependency, database, production configuration, running service, template, or navigation file
was changed.

## Proofs

### Upstream source identity

Command:

```text
curl -fsSL https://media.dndbeyond.com/compendium-images/srd/5.2/DE_SRD_CC_v5.2.1.pdf | sha256sum
```

Observed:

```text
f06989dcdf98c8e93b52ba5ea9db52d5e1b054d6d87a148ff295138bafe8a65b
```

This matches the approved source lock and package manifest.

### Package validation

The repository host has no project virtual environment, so verification used the already-local VTT
application image with a read-only repository mount and networking disabled:

```text
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 \
  -v /home/admin/projects/roll-drauf-vtt:/workspace:ro -w /workspace \
  sha256:dafaade1c9141917159e9aff316026e23158bcfd34d4c42923150b9c5ae867cf \
  python -m tools.validate_regelwerk
```

Observed identity and expected R0 coverage state:

```text
rulesetId: srd-5.2.1-de
rulesetVersion: 0.1.0-r0
status: draft
packageDigest: sha256:1949b44c24b385c4a576ec9835aaed147407cee359f58c81722d3367f7e96035
attributionSha256: c0bd7a2a58d6ac29c8adbdf3e2750ec6262fcba6ecaed923c8cc2dede2fb87c9
requiredPageCount: 408
coveredPageCount: 0
missingPageRanges: 5–412
missingSections: 12
```

The missing coverage is intentional at R0; bulk transcription is not authorized yet.

### Focused tests

Command:

```text
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 \
  -v /home/admin/projects/roll-drauf-vtt:/workspace:ro -w /workspace \
  sha256:dafaade1c9141917159e9aff316026e23158bcfd34d4c42923150b9c5ae867cf \
  python -m pytest -q -p no:cacheprovider tests/test_regelwerk_package.py
```

Observed:

```text
14 passed in 6.09s
```

The suite proves the valid draft/published fixture paths and rejection of attribution tampering,
source replacement, cross-edition documents, arbitrary markup, unknown schema fields, malformed
tables, unresolved internal rule references, document digest mismatch, incomplete publication,
same-version package mutation, and manifest/document inventory drift.

## Acceptance checklist

- [x] Official source URL, publication date, page count, retrieval date, and verified SHA-256 are
  recorded outside the package manifest.
- [x] The package manifest must exactly match the approved source lock.
- [x] The required attribution exists and is independently hash-pinned.
- [x] Source-lock, package, and document schemas are closed and validate as Draft 2020-12.
- [x] The safe content vocabulary has no arbitrary HTML/script field.
- [x] Stable document/rule IDs and edition-scoped references are enforced.
- [x] Every source page is classified as required content or explicit front matter.
- [x] The twelve official top-level sections partition all required pages.
- [x] Published or retired packages cannot have incomplete coverage.
- [x] Caller-pinned package digests reject mutations under the same version.
- [x] Valid fixtures pass and all required negative fixtures fail.
- [x] No new dependency or production mutation was introduced.

## Risks and assumptions

- **Low — open:** A named content lead, independent source-fidelity reviewer, VTT integration lead,
  and final acceptance owner are still required before the corresponding later publication gates.
- **Low — accepted:** R0 intentionally contains no rule documents, reader, search index, or public
  route. Its incomplete coverage report is the control that prevents premature publication.
- **Low — accepted:** Validation imports the repository's existing canonical JSON implementation
  and dependencies; no duplicate canonicalization algorithm was introduced.

No medium-or-higher R0 Deploy risk remains unresolved.

## Artifacts

- R0 source lock, schemas, package skeleton, validator, CLI, and tests: retention class
  `versioned` until R0 Monitor closes; published successors become immutable.
- This Deploy record and the approval record: retention class `immutable` after phase closure.
- Test output and validator output recorded above: retention class `immutable` phase evidence.

## Next step

Run R0 Monitor against the implemented boundary. Confirm the acceptance evidence, inspect the
working-tree scope, and decide whether R0 closes and R1 Discover may begin. Do not implement the
Regelwerk reader during R0 Monitor.
