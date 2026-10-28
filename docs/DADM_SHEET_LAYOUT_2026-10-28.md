# Character sheet readability, 2026-10-28

## Discover — complete

- **Input:** A phone screenshot shows a cramped character sheet, clipped-looking controls and a large empty parchment area.
- **Current state:** In a 390×844 Chromium viewport, the sheet's first useful content begins at y=800. The route repeats a title, description and book-frame heading ahead of the character. The frame heading uses pale text on pale parchment. The SRD rules sheet is followed by a second page of disabled legacy inputs in view mode. The same fixture produces a 4,822px phone document and a 5,721px desktop document.
- **Inventory/dependencies:** `vtt/templates/character-sheet.html` owns the route markup, inline styles and mode state; `vtt/static/css/book-scene.css` and `book-shell.css` supply the shared book layout. Production adds `vtt-main-nav.css/js` on top of this template; rollout must retain those assets. The Playwright fixture in `tests/test_sheet_to_table_browser.py` supplies an authenticated SRD character.
- **Risks/assumptions:** **Medium usability:** the character and roll controls are below the fold on a phone. **Medium usability:** pale text and duplicated read-only fields undermine legibility. **Low uncertainty:** the exact Android gallery capture path is unknown; a matching full-page blank area was not reproduced locally, so validation will use browser geometry and both viewport and full-page captures.
- **Next step:** Apply a sheet-only layout that makes the playable character visible first and gives each page its natural height.

## Apply — complete

- **Design:** Keep the shared top navigation, but make this route's navigation row compact and horizontally scrollable on narrow screens. Suppress the route's decorative duplicate title and book-frame introduction; present the character name as the sheet heading. Use dark ink for the sheet header. Give the sheet's stacked pages natural height. For SRD characters, show the playable rules sheet in view mode and reveal the legacy form only in edit mode; keep the legacy sheet visible for non-SRD characters. Reduce empty identity artwork to a compact size and make its labels German.
- **Boundary/contracts:** No backend or character data changes. `data-sheet-mode` and `data-sheet-has-srd` on `<body>` drive the view/edit presentation. Existing `#sheetForm`, SRD roll controls, and navigation IDs stay intact.
- **Acceptance:** At 390×844 and desktop width, the character name and first roll control appear within the first phone viewport; no horizontal page overflow or clipped controls; the SRD view does not add a second disabled form; edit mode retains the form; sheet-to-table rolls still work.
- **Tradeoff:** The route loses redundant book-frame prose in favor of the character. The shared navigation remains available.
- **Deploy handoff:** Implement only the template and targeted browser regression check, then run sheet browser tests, stage the template over the current production image while retaining live navigation overlays, and smoke-check production.

## Deploy — complete

- **Implementation:** The sheet route now keeps a compact scrolling top navigation, starts with the character name and action buttons, omits duplicated chrome, removes the redundant SRD view-mode form, and uses a compact identity preview. Legacy characters retain their form, and SRD edit mode still exposes it.
- **Files changed:** `vtt/templates/character-sheet.html`; `tests/test_character_sheet_layout_browser.py`; this record and viewport proofs under `docs/proofs/sheet-layout-2026-10-28/`.
- **Verification/proofs:** Chromium at 390×844 and 1280×900 checks that the title and first roll fit in the first viewport, the document has no horizontal overflow, the page content fits its box, and the SRD form is hidden only in view mode. The layout test, sheet-to-table browser journey, and Duckfolk-to-sheet browser journey passed (3 tests). The phone and desktop viewport captures are stored with this record.
- **Production rollout:** `roll-drauf-vtt-app:sheet-layout-20261028-v5` is based on `official-publisher-20261027-v4` and changes only the sheet template. The live navigation CSS/JS references were preserved. The Compose override was backed up as `production.duck-species.override.yml.before-sheet-layout-20261028` before switching the app image.
- **Acceptance checklist:** Character visible first ✓; first roll in phone viewport ✓; no horizontal overflow or clipped page ✓; edit form retained ✓; live roll journey passes ✓.
- **Residual risk/next step:** The user's exact Android gallery capture path was unavailable; collect an in-browser screenshot if they still see blank parchment after refreshing the live sheet.

## Monitor — complete

- **Observed result:** `https://vtt.roll-drauf.de/api/admin/assets/health` returned `healthy` after rollout. The public route served the updated template with HTTP 200, and the shared navigation CSS and JS both returned HTTP 200.
- **Validation evidence:** Browser geometry measured the first roll inside the 844px phone viewport and the rendered sheet within the document bounds; the targeted browser journeys passed before deployment.
- **Residual finding:** **Low:** visual differences caused by a phone's browser zoom or an old cached page remain possible because no authenticated production account was used for a direct screenshot.
- **Recommended action:** Close this layout fix; if a phone still shows the old capture, verify its live viewport after a reload and investigate the device-specific scale.
