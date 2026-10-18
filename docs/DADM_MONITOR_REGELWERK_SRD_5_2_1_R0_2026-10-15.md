# DAD-M Monitor: German SRD 5.2.1 Regelwerk R0

status: complete — R0 closed
date: 2026-10-15
profile: standard
phase: Monitor
milestone: R0 — Source, rights, and corpus foundation
deploy-input: `docs/DADM_DEPLOY_REGELWERK_SRD_5_2_1_R0_2026-10-15.md`

## Input summary

R0 Deploy implemented the approved source/rights lock, German attribution artifact, closed
semantic schemas, draft package skeleton, validator, deterministic coverage report, CLI, and
focused tests. Monitor independently rechecked identity pins, acceptance behavior, regression
compatibility, file scope, and expected incomplete-content state.

## Observed results

- The official German SRD PDF still hashes to the approved source SHA-256.
- The local German attribution artifact still hashes to the approved attribution SHA-256.
- The direct CLI entry point validates successfully with the R0 package digest explicitly pinned.
- The R0 draft correctly reports zero documents, required content pages 5–412 missing, and all
  twelve top-level sections missing. This is the expected pre-transcription state, not a defect.
- All fourteen R0 package tests pass.
- All twenty-five existing Creation Engine content tests pass alongside the R0 tests, confirming
  that reuse of canonical JSON behavior did not regress that boundary.
- No database, live container, production service, route, template, navigation, dependency, or
  runtime configuration was mutated.
- Existing unrelated dirty-tree changes remain present and untouched.

## Validation evidence

### Pinned package validation

Command:

```text
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 \
  -v /home/admin/projects/roll-drauf-vtt:/workspace:ro -w /workspace \
  sha256:dafaade1c9141917159e9aff316026e23158bcfd34d4c42923150b9c5ae867cf \
  python tools/validate_regelwerk.py \
  --expect-digest sha256:1949b44c24b385c4a576ec9835aaed147407cee359f58c81722d3367f7e96035
```

Result: exit `0`; the reported package and attribution digests match the approved R0 evidence.

### Targeted and regression tests

Command:

```text
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 \
  -v /home/admin/projects/roll-drauf-vtt:/workspace:ro -w /workspace \
  sha256:dafaade1c9141917159e9aff316026e23158bcfd34d4c42923150b9c5ae867cf \
  python -m pytest -q -p no:cacheprovider \
  tests/test_regelwerk_package.py tests/creation_engine/test_ce_content.py
```

Result:

```text
39 passed in 7.89s
```

### External and local identity recheck

Observed on 2026-10-15:

```text
official PDF sha256: f06989dcdf98c8e93b52ba5ea9db52d5e1b054d6d87a148ff295138bafe8a65b
attribution sha256: c0bd7a2a58d6ac29c8adbdf3e2750ec6262fcba6ecaed923c8cc2dede2fb87c9
```

Both match `vtt/rules_content/source-locks.json` and the package manifest.

### Scope and hygiene

- A read-only repository mount and `--network none` were used for package/test execution.
- The only network access was the explicit official-PDF digest recheck.
- No trailing whitespace was found in the R0 artifacts.
- The working tree contains pre-existing unrelated changes; R0 added only the files named in its
  Deploy record and updated its approved governance records.

## Acceptance validation

- [x] Source identity is externally re-verifiable and matches the independent source lock.
- [x] Attribution integrity is independently pinned.
- [x] Semantic schemas and coverage contracts validate.
- [x] Security/source/edition negative fixtures fail as designed.
- [x] Published-state completeness and same-version digest mutation are rejected.
- [x] Existing canonical-content tests remain green.
- [x] Expected R0 incompleteness is visible and prevents publication.
- [x] No out-of-scope application feature or production state changed.

R0 acceptance is met in full.

## Residual risks and assumptions

- **Medium — accepted for R1 Discover only:** `vtt/static/js/book-scene.js`, a required future R1
  navigation integration point, already contains unrelated user changes. R1 must inventory and
  preserve that diff before Apply/Deploy; this finding blocks a blind navigation patch, not R0
  closure or R1 fact gathering.
- **Low — open:** Named content, fidelity, integration, and final acceptance owners are still
  required at the later gates defined by the approved program.
- **Low — accepted:** R0 has no public reader or content documents by design; the validator makes
  that incompleteness explicit.

No unresolved medium-or-higher finding blocks R0 closure. The existing navigation-file overlap is
explicitly accepted only as a bounded R1 Discover input and must be resolved before R1 Deploy.

## Artifacts

- This Monitor record: retention class `immutable`.
- R0 Deploy record and test/validator outputs: retention class `immutable`.
- R0 package foundation: retention class `versioned`; its current digest is pinned above.

## Recommended next action

Close R0 and start R1 Discover. Inventory the current Book Scene/nav changes, select the exact
representative SRD section for the vertical slice, and map the read-only routes and test surfaces.
Do not change navigation or implement the reader until R1 Apply has resolved the dirty-file overlap
and defined the bounded slice.
