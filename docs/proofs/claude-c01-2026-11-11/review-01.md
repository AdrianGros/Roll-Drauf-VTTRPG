Unabhängiger Claude-Quellreview, keine vom Reviewer ausgeführten Tests. Geschätzte Häufigkeiten sind ungemessene Reviewerannahmen. Umsetzung/Nacharbeit und Live-Status werden separat geführt.

## Independent C01 review: base fb9642e, candidate 32bade3

This is a read-only review of the diff plus targeted source reads. I ran no tests. The five new browser tests are unrun evidence, so nothing below counts as passing.

### Findings

**F1: Medium. Hub primary-action buttons are still German in the English UI, next to localized labels.**
- **Where:** `vtt/templates/campaigns.html` ~2687, 2696, 2705, 2711 and 2799, in the next-action builder that returns `{label, hint, action}`. Raw literals remain in `<button>` and `<span>` markup: "Einladung eingeben", "Spieler einladen", "Karte + Session vorbereiten", "Session anlegen", "Warte auf die Spielleitung".
- **Trigger:** English UI, campaign hub with DM or member primary-action state.
- **Expected:** An English card, per the contract's DE/EN Kampagnen-Hub acceptance.
- **Actual:** The same card mixes an English `label` and `hint` with a German button. The sibling builder at ~2070–2150 was fixed with `VTTUiHTML`, and the catalog already holds these keys in extras. `display-preferences.js` `translate()` only handles `data-ui-*` attributes, so there is no fallback.
- **Also in this file:**
  - About 34 hints still interpolate `session.name` in German, for example `Für "${session.name}" ist noch keine aktive Karte…`.
  - `campaigns.html` ~1742 renders `member.campaign_role (member.status)` raw.
- **Rework:** Wrap the five literals in `VTTUiHTML`. Either convert the name-bearing hints to `{name}` templates, which also needs extras entries, or list them as an accepted residual.

**F2: Medium. The new tests do not exercise the main data boundary or the main surfaces.**
- **Where:** `tests/test_c01_navigation_browser.py`.
- **Covered:** sheet loading and failure states, the speed unit, and the creator frame.
- **Not covered:** the contract's "Benutzer-/Charaktername „Speichern" bleibt" check on the new localized surfaces. That means the campaign ledger, hub, characters archive and book dashboard, where authored labels meet user text. The only existing check is the sheet field in `test_presentation_browser`.
- **Also missing:**
  - No English-UI assertion for the campaign hub or characters views.
  - No contrast check for book overviews or the hub; the new contrast check covers only the creator.
  - No 320 px or 1440 px creator case.
  - No assertion that the main navigation remains present exactly once. The tests only check that the duplicates inside `.sheet-journey-nav` are gone.
  - No language-reload test for creator draft protection.
- **Impact:** The "genaue Befunde statt Freigabe" acceptance rests on the 40 existing tests plus unrun new ones.
- **Rework:** Add one seeded EN-UI check. Use a campaign named "Aktiv" and a character named "Speichern" or "Stufe 1". Assert the data stays verbatim while the status and label strings are localized. Add a positive assertion that the main navigation exists once on the sheet.

**F3: Low. First-load state edge cases in `loadSheet` and `renderSheet`** (`character-sheet.html` ~2056–2115).
- **Partial render:** `renderSheet()` calls `setSheetLoadState('ready')` and unhides `#sheetSpread` before `renderCore`. If a render function throws, the catch (with `firstLoad` true) shows the error box while a half-filled legacy form stays visible. A retry then has `firstLoad` false, so it shows only a banner.
- **Late failure:** There is no request token. A late first-load failure can overlay the error box on an already rendered sheet.
- **Stuck loading:** `if (!loaded) return;` leaves the state on "loading" forever for any null result. `auth.js` also returns `null` for non-JSON responses, not only after a 401 redirect.
- **Rework:** Set ready only after a successful render. Re-hide `#sheetSpread` in the first-load error path. Treat `null` without a redirect as an error.

**F4: Low. Catalog builder silently lets extras override inventory entries.**
- **Where:** `tools/i18n/build_catalog.py`.
- **Trigger:** An extra whose source hashes to an existing inventory key but carries a different de/en translation. The new collision check only rejects a different `source`.
- **Actual:** The extra replaces the inventory text without any warning.
- **Rework:** Fail, or at least log, when the key exists and `de` or `en` differ.

### Checked, no issue found
- **User text:** Names, status values and `class`/`race` pass only as `{param}` into a single-pass substitution, and fallbacks apply only when the field is empty. Campaign status is mapped only for enum values, and unknown values stay as delivered.
- **Seeded copy:** `content()` translates only text equal to the repository fallback, so DM-edited site copy is shown as written. The `play_launch.title` fallback "Spieltisch" matches `content_defaults.py` and its migration.
- **Sheet edit control and navigation:** `#sheetModeActionBtn`, `#campaignContextBtn` and `toggleSheetMode()` are kept. The main ribbon keeps the Creation Engine link, so the JS that sets `data-creation-engine-nav` IDs still finds its target. `test_character_journey_productization` still passes by reading.
- **Speed hook:** `data-sheet-stat="speed"` is set on the cell and the legacy label fallback is kept. The conversion maths is unchanged.
- **CSS:** `--ui-accent` and `--ui-action-*` are set by `display-preferences.js`. The creator active-state specificity beats the base `.sc-step` rule. Active states use weight and underline, not only colour.
- **Scope and roles:** No role, kick or leave logic changed. Hardcoded template keys `u_ced1b5bd9dd5` and `u_00e5baddf108` exist in the catalog indexes.

### Verification gaps (not observed regressions)
- No test run of the five new tests or the full matrix (DE/EN × paper/night at 320/390/1440). Paper-theme contrast for muted kickers on non-solid book backgrounds is unmeasured.
- I did not check that every `VTTUi("…")` literal added in the diff has a catalog entry. A missing entry silently falls back to German in English. Only a sample was spot-checked.
- The global night `.btn-secondary`, `.vtt-map-nav` and `.mm-global-nav` rules affect map and nav surfaces and are unverified. In `templates/`, `.btn-secondary` appears only in campaigns, characters, invite and character-sheet.
- The initial speed render always shows metres with a decimal comma. A stored `ft` preference at load is untested. The shared sheet's "Bewegung {value} m" ignores the unit preference. Both predate this diff.
- New campaigns and sessions still get German stored names ("Meine erste Kampagne", "Session …", `de-DE` dates). This is documented as intentional but is visible in an English UI.
- The creator active step border grows from 1 px to 2 px, a small layout shift.

**Verdict: rework_required.** F1 and F2 are small and bounded, and there are no High findings. Re-review after the five literals are wired and the EN data-boundary test plus the five new browser tests pass. This is not deployment approval or live evidence.
