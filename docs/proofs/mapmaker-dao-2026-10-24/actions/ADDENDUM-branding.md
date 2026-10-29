# Addendum to the action review — source change during the run (2026-10-24)

**Author:** Claude Opus 5.5 (Monitor). [`report.md`](report.md) and [`matrix.json`](matrix.json) are immutable evidence and were not edited.

`report.md` says "Product JS/HTML/CSS hashes stayed unchanged through completion: False". That is expected and fully explained by the parallel, user-authorized aesthetic Deploy:

- The `matrix.json` `source_sha256` for `index.html` (`f501fb06…`) and `mapmaker.css` (`b93d5e39…`) equals the pre-Deploy hashes in [`../branding/hashes-before.json`](../branding/hashes-before.json).
- `source_hash_differences` lists exactly `mapmaker.css` and `index.html`.
- All 10 JS modules in the matrix equal the final source. [`../review-helpers/monitor_check.py`](../review-helpers/monitor_check.py) shows a mismatch only for those two files.

What changed in those two files is recorded in [`../branding/deploy.md`](../branding/deploy.md) and [`../branding/deploy.diff`](../branding/deploy.diff):
- `index.html`: brand block only (ornament `<img>` + wordmark spans; the `aria-hidden` was removed). No ids, controls or structure changed.
- `mapmaker.css`: colors, fonts, focus/selection, header flex sizing and help-grid layout.

No JS behavior changed, so the functional action results stay valid for the final source. Selector-level DOM is unchanged, and the parent's full final-source regression passed (34 tests).

Matrix recount (unique ids, last status): **226 rows = 221 tested-pass, 2 tested-fail (A1 `layer-rename-dblclick-blur`, V3 `mobile-place-visible-navigation`), 2 not-tested (`stamp-search`: no control exists; `alternate-browsers`), 1 blocked (`physical-stylus`)**. This matches the report. The raw rerun rows (272 total) include harness collisions and timeouts that the report correctly excluded from product findings.
