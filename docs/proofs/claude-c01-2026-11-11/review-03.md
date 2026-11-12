## Final C01 review: delta-03 over d53fd2c

This is a read-only review of `review-delta-03.diff` and `review-02.md`, plus targeted lookups. I ran nothing. The test results below are the coordinator's reports, not my observations.

### Previous findings
- **F5 (draft protection): resolved by reading.** `test_creator_draft_survives_language_save_and_reload` now covers the real flow:
  - A real field edit is made while the actual autosave PUT is held back, so the test asserts `app.saving` is true and the server value is still old.
  - The real display-dialog apply button, found by its accessible name, triggers the reload.
  - The `beforeunload` guard fires, is dismissed, and the typed value stays in the field.
  - The PUT is released and the server then holds the typed name.
  - After the reload, the page is English and the typed name is restored.
  - Authored English labels, the lifecycle status and a further pronoun edit are asserted, with the typed name verbatim.
  - `window.SrdCreator.app` exists at `srd-creator.js:15–16`, so the helper predicates are valid.
- **F6 (duplicate extras): resolved.**
  - The duplicate entries were removed from the later block.
  - The remaining English text consistently uses "DM". There is no "GM" or "game master" left in the file.
  - `build_catalog.py` now refuses duplicate object keys through `object_pairs_hook`. This also covers nested `de`/`en` objects and returns a normal dict.
  - The coordinator reports the negative compiler checks and `--check` (2800 sources) as passing.

### New delta checks, no defects found
- **Creator labels:** Each change wraps only an authored literal with `VTTUi`.
  - Wrapped: input and area labels, summary rows, override keys, level-table headers, the grant-kind dictionary, and "Regelbeitrag".
  - Left alone: the canonical values, `app.data.alignments` names, ability and skill names via the existing `SC` helpers, and typed user text.
  - Generic `h()` and `field()` are not changed.
  - "Körpergröße" maps to the German display "Größe", so the German UI is unchanged and English reads "Height". This is documented in the source.
- **Save status:** `setSaveText` is only called with the eight fixed lifecycle literals, never with server or error text, so no data passes through the catalog.
- **Night hub CSS:** The new `!important` rules are scoped to `html[data-vtt-theme=night] #book-dashboard-scene …` and run only in night. The scene wrapper is created in `book-scene.js`, so the selectors reach the hub, and paper is untouched. I found no state variants of `.hub-pill` or `.hub-badge` in `campaigns.html` that the flattening would erase. State colours use `.hub-step-state` classes, which are mapped to semantic tokens with text labels.

### Remaining defects
- **No Medium or High findings.**
- **Low (carried over, unchanged):** `loadSheet` still throws the authored error when `makeAuthRequest` returns `null` after setting `location.href` on a 401. The user may briefly see the error box and Retry before the login page loads. It is cosmetic and self-resolving.
- **Low:** The `!important` hub overrides in night are broad. Future hub styles that need their own text colour must account for them. Not a current defect.

### Residual verification gaps
- **Reruns:** The final CSS change needs one full rerun of the original suites (`presentation_browser`, `map_scale_contexts`, `table_contexts`) plus the C01 browser files, on the final commit. Only the targeted cases are reported as run since the CSS change.
- **Night hub coverage:** The night hub contrast evidence covers one 1440 px Chromium case with paper and night. There is no 320/390 px night hub case, and no Firefox or WebKit case for the new `!important` rules.
- **Creator EN coverage:** The EN label assertions cover the description step, summary and save lifecycle. Other creator steps may still hold unmarked literals. That is beyond this delta.
- **Catalog evidence:** The "590 marked literals present" and `--check` results are the coordinator's reports. I did not read the generated bundle.
- **Live evidence:** No live C01/P4 evidence exists yet. That is the coordinator's next phase and is not an observed regression.

**Verdict: ready_for_integration.** This is not deployment approval or live delivery.
