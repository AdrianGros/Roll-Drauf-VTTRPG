# Review: C01 PlayChrome contrast CSS (bounded, source only)

**Verdict: ready_for_integration.** I found no blocker or high-severity defect. The `.tabletop-shell` token rebind (`--ui-*`, `--vtt-*`) and the chrome-scoped `!important` colour rules look correct. Three low-severity items are listed below; none blocks integration.

I ran nothing. I read `play-contrast-review.diff`, `display-preferences.css` lines ~100–135, and `play.html` rules and ranges by grep. The diff I read already contains the field rule, but I did not check it against commit `4dca29475`. The "5 cases, 76.08s, all pass" result is your report, not mine.

## Findings

**No blocker, high or medium findings.**

**Low 1: state accent on `#tokenConnectionNotice` is lost.**
- **Where:** `play.html:2714` has `class="muted"` and inline `color:#e8b23f`. The new `.right-sidebar :is(.muted,…){color:var(--ui-muted) !important}` overrides it.
- **Trigger:** the "reconnecting" notice shows.
- **Expected vs actual:** the notice should keep its gold warning accent. It becomes muted `#c3cee6`. It stays readable (about 10:1 on navy), so this is a lost cue, not a contrast failure.
- **Impact:** none for acceptance. Optional fix: exclude it with `:not(#tokenConnectionNotice)`, or give it `color:var(--ui-warning) !important`, which the rebind already defines.

**Low 2: field rule may also hit non-text `input` types.**
- **Where:** `input:not([type=color]):not([type=checkbox]):not([type=radio]):not([type=range])`. It still matches `button`, `submit`, `file` and `image` inputs. `!important` on `background-color` would repaint them dark.
- **Trigger:** such an input exists inside `.right-sidebar` or `.floating`. I did not check whether any does.
- **Impact:** cosmetic and conditional. Fix if one exists: add `:not([type=button]):not([type=submit]):not([type=file])`.

**Low 3: field focus indicator is unverified.**
- **Where:** the same field rule forces `border-color:var(--ui-line) !important`.
- **Trigger:** if the spellbook theme's `input:focus` signals focus only through border colour, the indicator now reads the same as the resting state. I did not read that rule's `box-shadow` or `outline`.
- **Impact:** possible keyboard-focus visibility regression on fields. The mapScale test checks colour, not focus.
- **Fix if confirmed:** add `input:focus-visible,textarea:focus-visible,select:focus-visible{outline:2px solid #fdfaf3;outline-offset:1px}` inside the scope.

## Checked and consistent with the contract
- **Canvas, grid, SVG and map:**
  - The surface and text rules only match `.right-sidebar` and `.floating` descendants.
  - `play.html` uses the rebound `--vtt-*` tokens in only 8 places, all button or title colours. The only `--vtt-ink-muted` use, `.play-session-title`, sits before `.tabletop-shell` opens at line 2493, so it is not rebound.
  - `test_play_chrome_does_not_recolor_canvas_or_map_layers` pins `#mapWorld` and `.map-viewport` background colour and image across paper and night.
- **Roles and data:**
  - The CSS is role-agnostic and touches no API, storage or domain data.
  - The test types `1.5` into `#mapScaleMeters` without saving and appends a probe `<p>` that is never persisted.
  - It asserts that `#mapScalePanel` is absent for the Player.
- **Inline and book-skin overrides:** the field rule's specificity is roughly (0,7,3) and it uses `!important`, so it beats the book skin's `!important` field background and the inline colours. That matches the `mapScaleMeters` 1.03 failure being fixed. The test's `.muted` plus inline `color:#342b25` probe covers the override.
- **Plum controls:** `.tool-btn` and `.sidebar-tab` get `#fdfaf3 !important` on active, hover and focus. Existing `play.html` rules already use `var(--vtt-paper-panel)`, which the rebind sets to `#fdfaf3`. That fixes the night case where it resolved to a dark panel colour.
- **Rollback:** the change is one CSS block plus one new test file, so a revert is clean.

## Verification gaps (unverified, not defects)
- I did not read the `4dca29475` diff or run any test. Execution evidence is your report only.
- `.floating` widgets (dice, token) are covered by the CSS, but the test measures only the toolbar and sidebar-tab panels.
- The text rule lists `h*`, `label`, `p`, `dt`, `dd`, `th` and `td`. `div`, `span`, `li`, `a`, `strong` and `option` rely on inheritance from `.panel`, `.subpanel` or `.list-item`. The test's `PANEL_TEXT` selector has the same list, so those elements are not measured.
- I did not check whether any rule outside `play.html` (such as `components.css` or the book CSS files) reads `--vtt-*` or `--ui-*` on stage elements inside `.tabletop-shell`.
- The `contrast` helper starts from a white backdrop and ignores `backdrop-filter` and images. `PANEL_BUTTONS` only checks buttons that are currently visible and enabled.
- Firefox and mobile widths are not part of this test, and the CSS file's cache-busting on deploy is unchecked.

**ready_for_integration** is a source-review result only. It is not deployment approval or live delivery.
