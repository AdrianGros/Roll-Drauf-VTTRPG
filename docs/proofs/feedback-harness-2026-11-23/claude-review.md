# FEEDBACK-R1-FINAL: MONITOR review, source only

**Scope:** commit `7e0a3c859` against base `2fcd28deb`. I reviewed T1, T2, C27-S1 and T4a using the supplied diff and excerpts. I ran no tools, tests or live checks.

## Blocking high/medium findings

**None supported by the source.** I could not show a defect in this slice that a user can trigger and that blocks release. The items below are low-severity or not yet verified. None of them blocks release.

## T1: session start, context, double click, navigation

- **Double-click guard.** `launchCampaignHubSession` (`book-scene.js`) adds the campaign to `pending` before its first `await`. A second click returns immediately. The guard is released in `finally`.
- **Failed start after create.** `created` triggers `renderCampaignHubDetail`, so the new session stays visible for a retry. Nothing deletes it.
- **Stale page.** `renderVersion` stops both `enterPlay` and the error text if the user has moved to another page. The server start already requested is allowed to finish, as the contract says.
- **DM context.** Only this explicit action calls `ensureTableContext(..., 'dm', true)`. The shared `makeAuthRequest` path is unchanged: a GET or a play page still does not upgrade a Player seat on its own. The follow-up start request reuses the forced context because its campaign and session match.
- **Server.** `start_session` now accepts only `scheduled` and `ready`. The existing `_is_dm` check and the check for another running session stay in place.
- **Low, not a defect.** Restoring the old `buttons` after a re-render touches detached nodes only. While `pending` is still set, freshly rendered buttons are clickable, but the guard swallows those clicks. Nothing needs to change.
- **Not verified.** The `POST /api/campaigns/<id>/sessions` (create) URL does not match the table regex. It therefore sends whatever `VTTTableContext` is already in memory, possibly for another session. The parametrized `other_session` case is meant to cover this; its result was not supplied.

## T2: navigation, capabilities, TOC

- **Active state.** `updateRouteState` (`vtt-main-nav.js`) recomputes `aria-current` and `has-active` on every scan and on `popstate`. It is idempotent. The `MutationObserver` watches `childList` only, so these attribute changes cannot cause a loop. The underline on the summary is presentation only.
- **Capability rows.** The hydrators now write into `.book-toc-label` and fall back to the whole entry. This keeps the numeral and leader structure intact. Hidden Regelwerk takes IX, so the visible rows run I–VIII, which matches the test.
- **Open risk: click handling for new TOC links.** The new rows (`/conversations`, `/mapmaker`, `/atlas`, `/regelwerk/compendium`) carry `data-book-route`. I have not seen whether `bindSceneNavigation` intercepts `data-book-route` and supports only the book routes. The browser test checks that the `href` is present but never clicks these rows.
  - Smallest check: click each new row in the TOC regression test.
  - If they are intercepted: emit `data-book-route` only for in-book routes.
  - This is unverified, not a finding.

## C27-S1: mapmaker

- **Bracket keys (E03).** `BRACKET_NUDGE` runs after the typing guard and the Alt+Arrow block, and before the `mod || altKey` early return. It matches the produced character, which covers both Shift on US layouts and AltGr/Option on DE layouts. Cmd and Ctrl-only brackets fall through to the browser. Alt+[ on US now nudges; this was accepted in the plan.
- **Per-asset size (E22).** Sizes live in memory only, keyed per asset and per crop. Nothing goes into the document or history.
- **Filters (E26).** Matching is strict on declared traits. "Ohne Angabe" is an explicit bucket and undeclared symbols are counted. No metadata is invented. The reset button returns focus to `#stampPack`.
- **Node editing (E11).** Checking `#pathNodeMode` switches to select while keeping the selection, because `setTool` preserves it for select. The hover cursor and highlighted handles appear only in node mode.
- **Image brush (N02).** No swatch is checked while the image brush is active, and the first swatch remains focusable.
- **Recent symbols (N17).** The options are grouped into recent symbols and the current palette page. `ensureSymbolOption` also sees options inside `optgroup`s.
  - `ed.assetAvailable` does not appear in the excerpts; I assume it exists.
- **Low: staged Escape (N16a).** Pressing Escape inside the File menu (`ui.js` menu `keydown`) closes the menu. It does not stop propagation, so the document handler can also leave a placement tool.
  - Smallest fix if wanted: `event.stopPropagation()` in that menu handler.
  - Not blocking.
- **Escape while typing.** Escape inside `#selText` is still ignored, because the typing guard comes first. This is unchanged.

## T4a: accents and class facts

- **Accent surfaces.** The `color-mix` override (specificity 0,2,1) beats the night theme rule (0,1,1) only for explicit bronze or teal. The default night palette is untouched.
- **Play table.** The play tabletop shell re-declares `--ui-panel` and `--ui-soft`, so the table keeps its own surfaces.
- **Step counters.** Error and success counters use `--ui-paper` text on the danger/success colour. Both themes give high-contrast pairs. Ordinary counters use the accent border on `--ui-soft`.
- **Class facts.** `sc-class-facts` is applied to definition lists and stat blocks. No text or rule values change.
- **Not computed here:** the contrast of the mixed surfaces against `--ui-ink`. The contract requires this calculation.

## Source review versus verification

| Kind of check | Status |
|---|---|
| Source review | Done above, from the diff and the earlier excerpts only. |
| Tests | None run in this pass. No results were supplied for the new browser and API tests, the regression set or `build_catalog.py --check`. |
| Live verification | Not done. Still open: DE/US keydown logs on physical keyboards, the hub start journeys at 390/1440 px in Chromium and Firefox, and accent contrast measurement. |

T3 (locale) and the later geometry and format packages are out of scope and were not reviewed.
