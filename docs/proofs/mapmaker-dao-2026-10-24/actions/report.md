# Mapmaker independent action acceptance review

**Phase:** DAD-M Monitor, standard profile. **Status:** validation complete with findings; medium V3 prevents unconditional acceptance.

**Input summary:** User requested independent agents to try every action, inspect visual structure and determine whether the required first prototype exists. This bounded review owns functional actions; product source remained read-only.

**Observed results:** 226 unique action/check entries: 221 tested-pass, 2 not-tested, 2 tested-fail, 1 blocked. Raw runs contain 272 entries including targeted reruns. The V3 visibility entry comes from the independent visual review; all other entries are this reviewer’s browser evidence.

**Environment:** Chromium 153.0.8010.12, real Canvas2D app, isolated localhost HTTP server with the repository’s actual CSP, fresh IndexedDB/browser context per scenario. Desktop 1440×1000 and mobile 390×844. Product JS/HTML/CSS hashes stayed unchanged through completion: False.

**Evidence:** [matrix.json](matrix.json) contains all action/check statuses, observations, source SHA-256s and static controls. [run_actions.py](run_actions.py) is the reproducible independent harness. [downloads.json](downloads.json) records verified download sizes/dimensions/hashes. Raw runs/logs remain alongside these artifacts. These are immutable Monitor evidence for the pre-aesthetic source revision.

The pass covers all six tools; all 11 material swatches with pixel changes; all 40 palette assets; stamp size/rotation/flip/variation/scatter and cancellation; every label style and place kind; all selected-item fields and text/lore; Places state selection; layer selection/show/hide/opacity/coast/reorder/rename/add/delete and limits; documented keyboard shortcuts; mouse/Space/middle-button pan; wheel/button/key zoom; help/tabs/menu and modal cancel/close; file download/open/cancel/rejected imports; New/restore choices; PNG 1× and 2× with verified 2400×1600 and 4800×3200 files; local autosave/quota/unavailable paths; failed encoding feedback and recovery; the hidden Reload action; mobile taps, sheets and browser-level two-finger pinch.

## Findings

**A1 · Low · Double-click layer rename is ineffective.** Open Ebenen, select Land, then double-click its name. No rename textbox appears. Reproduced again on an already-active layer. The first click rebuilds the layer list and replaces the button, so the double-click listener cannot receive the intended gesture. The explicit rename button succeeds with Enter, blur and Escape. See [screenshot](layer-rename-dblclick-blur-failure.png), `ui.js:468–469` and `ui.js:455–456`. Recommended next bounded action: let Claude decide a small fix in a separately scoped functional rework; Codex verifies it.

**V3 · Medium · Selected mobile place is covered by the inspector sheet.** Places → Hohenfurt centers the correct selected item, but its marker lies behind the open sheet at 390px, 320px and 667px. This action matrix distinguishes the successful state selection (`mobile-place-navigate`) from failed visible navigation (`mobile-place-visible-navigation`). Evidence/repro owned by the sibling visual review and independently confirmed by the parent. A visible placement above the sheet is required before this journey can pass.

## Rerun accounting and limitations

Initial label-kind/style failures and the first stamp-delete assertion were harness placement collisions: clicking a seeded label correctly selected it, and clicking a label above a symbol correctly selected that label. Targeted reruns on a blank map pass. The first 2× PNG check exceeded the harness’s 5-second click timeout; rerun with the normal 20-second limit produced a verified PNG. The initial New-map safety row was an incorrect harness expectation: the actual dialog explicitly warns that it replaces the current map and clears Undo, and instructs file saving. This was corrected and revalidated. Initial startup fault injection disabled Canvas before module evaluation, outside the initialization recovery branch; the corrected injection targets brush-preview initialization and the error/Reload controls pass. Raw failures are retained for audit and excluded from genuine product findings after these targeted reruns.

Symbol search has no control and is reported absent (`not-tested`), not passed. Hardware stylus pressure/palm rejection is blocked because no physical input device is attached; the pressure option uses a synthetic PointerEvent solely to reveal and toggle that option. Firefox/Safari/WebKit action coverage is not tested here. No claim covers every input combination, all corrupt files, physical-device behavior, production deployment or the whole VTT. A failure before JavaScript module initialization does not exercise the app’s recovery UI and remains outside that validation boundary.

**Risks and assumptions:** Medium V3 remains open. Low A1 has a working explicit rename-button alternative. Starter/Empty replacement behavior is warned and intentionally replaces the single local draft; downloadable JSON is the device-transfer/backup path. No product code, architecture, dependencies or live campaign data were changed.

**Recommended next action:** complete the bounded aesthetic pass and review V3’s functional visibility correction through DAD-M Apply/Deploy; verify changed journeys and run the existing regression suite after the final source settles. Do not silently close the medium finding.

## Complete consolidated matrix

| Action/check | Status | Evidence/notes |
| --- | --- | --- |
| Open fresh editor with seeded map, fonts and asset palette (`startup-desktop`) | tested-pass |  |
| Click pan tool and expose its options (`tool-pan`) | tested-pass |  |
| Click brush tool and expose its options (`tool-brush`) | tested-pass |  |
| Click eraser tool and expose its options (`tool-eraser`) | tested-pass |  |
| Click stamp tool and expose its options (`tool-stamp`) | tested-pass |  |
| Click label tool and expose its options (`tool-label`) | tested-pass |  |
| Click select tool and expose its options (`tool-select`) | tested-pass |  |
| Open Help dialog (`help-open`) | tested-pass |  |
| Close Help with button (`help-close`) | tested-pass |  |
| Close Help with Escape (`help-escape`) | tested-pass |  |
| Open File menu then Escape returns focus (`menu-escape`) | tested-pass |  |
| Click outside closes File menu (`menu-outside`) | tested-pass |  |
| Edit map title and Enter leaves field (`title-edit`) | tested-pass |  |
| Type tool keys and spaces in title without tool changes (`title-shortcuts-safe`) | tested-pass |  |
| ArrowRight cycles tab focus and panel (`tab-key-right`) | tested-pass |  |
| ArrowLeft cycles back (`tab-key-left`) | tested-pass |  |
| Desktop interactions have no JS or CSP errors (`startup-no-console`) | tested-pass |  |
| Select Land and paint a dab (`material-land`) | tested-pass |  |
| Select Wiese and paint a dab (`material-meadow`) | tested-pass |  |
| Select Wald and paint a dab (`material-forest`) | tested-pass |  |
| Select Steppe and paint a dab (`material-steppe`) | tested-pass |  |
| Select Wüste and paint a dab (`material-desert`) | tested-pass |  |
| Select Schnee and paint a dab (`material-snow`) | tested-pass |  |
| Select Sumpf and paint a dab (`material-swamp`) | tested-pass |  |
| Select Fels and paint a dab (`material-rock`) | tested-pass |  |
| Select Flachwasser and paint a dab (`material-shallow`) | tested-pass |  |
| Select Fluss and paint a dab (`material-river`) | tested-pass |  |
| Select Weg and paint a dab (`material-road`) | tested-pass |  |
| Adjust #brushSize to 2 (`brushSize-2`) | tested-pass |  |
| Adjust #brushSize to 400 (`brushSize-400`) | tested-pass |  |
| Adjust #brushOpacity to 1 (`brushOpacity-1`) | tested-pass |  |
| Adjust #brushOpacity to 100 (`brushOpacity-100`) | tested-pass |  |
| Adjust #brushSoftness to 0 (`brushSoftness-0`) | tested-pass |  |
| Adjust #brushSoftness to 100 (`brushSoftness-100`) | tested-pass |  |
| Paint continuous stroke (`brush-drag`) | tested-pass |  |
| Undo stroke restores exact pixels (`undo-button`) | tested-pass |  |
| Redo stroke restores exact pixels (`redo-button`) | tested-pass |  |
| Erase painted raster and undo (`eraser-stroke`) | tested-pass |  |
| Escape cancels in-progress stroke (`brush-cancel-escape`) | tested-pass |  |
| Pen PointerEvent exposes pressure checkbox; toggle off/on (`pressure-option`) | tested-pass | Synthetic DOM pen event; physical stylus behavior not claimed. |
| Brush actions have no JS/CSP errors (`brush-no-errors`) | tested-pass |  |
| Select Bergkette and place it (`stamp-asset-kenney-mountains`) | tested-pass |  |
| Select Felsnadeln and place it (`stamp-asset-kenney-crags`) | tested-pass |  |
| Select Felsen and place it (`stamp-asset-kenney-rocks`) | tested-pass |  |
| Select Tafelberg and place it (`stamp-asset-kenney-mesa`) | tested-pass |  |
| Select Vulkan and place it (`stamp-asset-kenney-volcano`) | tested-pass |  |
| Select See and place it (`stamp-asset-kenney-lake`) | tested-pass |  |
| Select Nadelwald and place it (`stamp-asset-kenney-forest`) | tested-pass |  |
| Select Tanne and place it (`stamp-asset-kenney-pine`) | tested-pass |  |
| Select Hohe Tanne and place it (`stamp-asset-kenney-tall_pine`) | tested-pass |  |
| Select Laubbaum and place it (`stamp-asset-kenney-tree`) | tested-pass |  |
| Select Palme and place it (`stamp-asset-kenney-palm`) | tested-pass |  |
| Select Kaktus and place it (`stamp-asset-kenney-cactus`) | tested-pass |  |
| Select Busch and place it (`stamp-asset-kenney-scrub`) | tested-pass |  |
| Select Stadt and place it (`stamp-asset-kenney-town`) | tested-pass |  |
| Select Dorf and place it (`stamp-asset-kenney-village`) | tested-pass |  |
| Select Langhaus and place it (`stamp-asset-kenney-longhouse`) | tested-pass |  |
| Select Burg and place it (`stamp-asset-kenney-castle`) | tested-pass |  |
| Select Zitadelle and place it (`stamp-asset-kenney-citadel`) | tested-pass |  |
| Select Tempel and place it (`stamp-asset-kenney-temple`) | tested-pass |  |
| Select Turm and place it (`stamp-asset-kenney-tower`) | tested-pass |  |
| Select Leuchtturm and place it (`stamp-asset-kenney-lighthouse`) | tested-pass |  |
| Select Windmühle and place it (`stamp-asset-kenney-mill`) | tested-pass |  |
| Select Wassermühle and place it (`stamp-asset-kenney-watermill`) | tested-pass |  |
| Select Ruinen and place it (`stamp-asset-kenney-ruins`) | tested-pass |  |
| Select Mine and place it (`stamp-asset-kenney-mine`) | tested-pass |  |
| Select Friedhof and place it (`stamp-asset-kenney-graveyard`) | tested-pass |  |
| Select Lagerfeuer and place it (`stamp-asset-kenney-campfire`) | tested-pass |  |
| Select Lager and place it (`stamp-asset-kenney-camp`) | tested-pass |  |
| Select Schiff and place it (`stamp-asset-kenney-ship`) | tested-pass |  |
| Select Brücke and place it (`stamp-asset-kenney-bridge`) | tested-pass |  |
| Select Hängebrücke and place it (`stamp-asset-kenney-rope_bridge`) | tested-pass |  |
| Select Hafen and place it (`stamp-asset-kenney-harbor`) | tested-pass |  |
| Select Brunnen and place it (`stamp-asset-kenney-well`) | tested-pass |  |
| Select Wachturm and place it (`stamp-asset-kenney-watchtower`) | tested-pass |  |
| Select Gefahr and place it (`stamp-asset-kenney-danger`) | tested-pass |  |
| Select Windrose and place it (`stamp-asset-kenney-compass`) | tested-pass |  |
| Select Banner and place it (`stamp-asset-kenney-banner`) | tested-pass |  |
| Select Flagge and place it (`stamp-asset-kenney-flag`) | tested-pass |  |
| Select Windrose (einfach) and place it (`stamp-asset-builtin-compass`) | tested-pass |  |
| Select Ortsnadel and place it (`stamp-asset-builtin-pin`) | tested-pass |  |
| Browse all categorized symbol groups (`stamp-palette-groups`) | tested-pass |  |
| Search symbols by text (`stamp-search`) | not-tested | No search control exists; 38 curated assets are displayed in categorized grids. |
| Place with exact size/rotation/flip and variation off (`stamp-options`) | tested-pass |  |
| Select newly placed stamp and inspect it (`stamp-select`) | tested-pass |  |
| Resize selected symbol (`stamp-inspect-size`) | tested-pass |  |
| Rotate selected symbol (`stamp-inspect-rotation`) | tested-pass |  |
| Unmirror selected symbol (`stamp-inspect-flip`) | tested-pass |  |
| Drag selected symbol to new position (`stamp-move`) | tested-pass |  |
| Finish deselects symbol (`stamp-deselect`) | tested-pass |  |
| Delete selected symbol and undo on a clear map (`stamp-delete-button`) | tested-pass |  |
| Scatter several symbols as one undo step (`stamp-scatter`) | tested-pass |  |
| Escape removes in-progress scatter (`stamp-scatter-cancel`) | tested-pass |  |
| Stamp actions have no JS/CSP errors (`stamp-no-errors`) | tested-pass |  |
| Create label in realm style (`label-style-realm`) | tested-pass |  |
| Create label in region style (`label-style-region`) | tested-pass |  |
| Create label in city style (`label-style-city`) | tested-pass |  |
| Create label in town style (`label-style-town`) | tested-pass |  |
| Create label in water style (`label-style-water`) | tested-pass |  |
| Create label in feature style (`label-style-feature`) | tested-pass |  |
| Create plain label kind (`label-kind-plain`) | tested-pass |  |
| Create city kind (`label-kind-city`) | tested-pass |  |
| Create town kind (`label-kind-town`) | tested-pass |  |
| Create castle kind (`label-kind-castle`) | tested-pass |  |
| Create harbor kind (`label-kind-harbor`) | tested-pass |  |
| Create ruin kind (`label-kind-ruin`) | tested-pass |  |
| Create landmark kind (`label-kind-landmark`) | tested-pass |  |
| Create label without a pin (`label-pin-default`) | tested-pass |  |
| Edit selected name (`label-text`) | tested-pass |  |
| Change selected style resets matching style size (`label-inspect-style`) | tested-pass |  |
| Change selected text color (`label-inspect-color`) | tested-pass |  |
| Change selected text size (`label-inspect-size`) | tested-pass |  |
| Rotate selected label (`label-inspect-rotation`) | tested-pass |  |
| Enable selected place pin (`label-inspect-pin`) | tested-pass |  |
| Change selected place kind (`label-inspect-kind`) | tested-pass |  |
| Edit selected lore and preserve line breaks (`label-lore`) | tested-pass |  |
| Open Places list and find edited place (`places-list`) | tested-pass |  |
| Click place list item selects and centers corresponding item (`places-navigate`) | tested-pass |  |
| Convert place to plain label disables lore and removes list entry (`label-remove-kind`) | tested-pass |  |
| Blank name is rejected and previous text restored on blur (`label-blank-name`) | tested-pass |  |
| Delete selected label with toolbar button and undo (`label-delete`) | tested-pass |  |
| Add Place switches to label creation tool (`place-add-button`) | tested-pass |  |
| Label actions have no JS/CSP errors (`labels-no-errors`) | tested-pass |  |
| Select Land raster layer (`layer-select`) | tested-pass |  |
| Hide Land reveals sea (`layer-hide`) | tested-pass |  |
| Show Land restores exact pixels (`layer-show`) | tested-pass |  |
| Set active layer opacity to 40% and undo (`layer-opacity`) | tested-pass |  |
| Toggle coast effect and undo (`layer-coast`) | tested-pass |  |
| Move Land one layer up (`layer-up`) | tested-pass |  |
| Move Land down restores order (`layer-down`) | tested-pass |  |
| Bottom down and top up actions disabled (`layer-boundary-disabled`) | tested-pass |  |
| Rename layer and commit with Enter (`layer-rename-enter`) | tested-pass |  |
| Escape cancels layer rename (`layer-rename-cancel`) | tested-pass |  |
| Double click active layer name enters rename (`layer-rename-dblclick-blur`) | tested-fail | Native double click did not open the layer rename textbox |
| Add raster layer (`layer-add-raster`) | tested-pass |  |
| Add stamps layer (`layer-add-stamps`) | tested-pass |  |
| Add labels layer (`layer-add-labels`) | tested-pass |  |
| Delete selected new layer and undo (`layer-delete`) | tested-pass |  |
| 32-layer cap disables all Add controls (`layer-count-limit`) | tested-pass |  |
| Layer actions have no JS/CSP errors (`layers-no-errors`) | tested-pass |  |
| Keyboard H selects pan (`key-tool-h`) | tested-pass |  |
| Keyboard B selects brush (`key-tool-b`) | tested-pass |  |
| Keyboard E selects eraser (`key-tool-e`) | tested-pass |  |
| Keyboard S selects stamp (`key-tool-s`) | tested-pass |  |
| Keyboard T selects label (`key-tool-t`) | tested-pass |  |
| Keyboard V selects select (`key-tool-v`) | tested-pass |  |
| Right bracket grows brush (`key-brush-grow`) | tested-pass |  |
| Left bracket shrinks brush (`key-brush-shrink`) | tested-pass |  |
| Shift+] grows brush softness (`key-soft-grow`) | tested-pass |  |
| Shift+[ shrinks brush softness (`key-soft-shrink`) | tested-pass |  |
| Right bracket grows stamp (`key-stamp-grow`) | tested-pass |  |
| Left bracket shrinks stamp (`key-stamp-shrink`) | tested-pass |  |
| Pan tool moves map without changing document (`pan-tool-drag`) | tested-pass |  |
| Hold Space temporarily pans with brush selected (`pan-space`) | tested-pass |  |
| Middle mouse pans without painting (`pan-middle`) | tested-pass |  |
| Zoom In button increases zoom (`zoom-in`) | tested-pass |  |
| Zoom Out button returns previous scale (`zoom-out`) | tested-pass |  |
| Plus key increases zoom (`zoom-plus-key`) | tested-pass |  |
| Minus key decreases zoom (`zoom-minus-key`) | tested-pass |  |
| Mouse wheel zooms (`zoom-wheel`) | tested-pass |  |
| F fits entire map (`zoom-fit-key`) | tested-pass |  |
| Delete removes selected stamp (`key-delete`) | tested-pass |  |
| Ctrl+Z restores deleted stamp (`key-undo`) | tested-pass |  |
| Ctrl+Shift+Z repeats deletion (`key-redo-shift`) | tested-pass |  |
| Ctrl+Y repeats deletion (`key-redo-y`) | tested-pass |  |
| Backspace removes selected stamp (`key-backspace`) | tested-pass |  |
| Escape clears selection (`key-deselect`) | tested-pass |  |
| Keyboard and view actions have no JS/CSP errors (`view-no-errors`) | tested-pass |  |
| Download editable map JSON (`save-json`) | tested-pass |  |
| Cancel New Map leaves document unchanged (`new-cancel`) | tested-pass |  |
| Create empty map with same working size (`new-empty`) | tested-pass |  |
| Import saved map restores content and raster pixels (`open-json`) | tested-pass |  |
| Cancel file picker leaves document unchanged (`open-cancel`) | tested-pass |  |
| Reject malformed import and preserve current map (`import-malformed`) | tested-pass |  |
| Reject wrong-format import and preserve current map (`import-wrong-format`) | tested-pass |  |
| Reject array import and preserve current map (`import-array`) | tested-pass |  |
| Cancel PNG export leaves document unchanged (`export-cancel`) | tested-pass |  |
| Export PNG at 1x actual dimensions (`export-1x`) | tested-pass |  |
| Export PNG at 2x actual dimensions (`export-2x`) | tested-pass |  |
| New Starter creates seeded map (`new-starter`) | tested-pass |  |
| File actions have no JS/CSP errors (`files-no-errors`) | tested-pass |  |
| Title mutation produces local saved status (`autosave`) | tested-pass |  |
| Reload offers correct draft title (`restore-offer`) | tested-pass |  |
| Escape cannot accidentally discard restore decision (`restore-escape`) | tested-pass |  |
| Restore returns previous title/content (`restore-yes`) | tested-pass |  |
| Choose fresh Starter instead of restored draft (`restore-no`) | tested-pass |  |
| Restore actions have no JS/CSP errors (`restore-no-errors`) | tested-pass |  |
| Protect existing unique edits when replacing map without a file backup (`new-unsaved-safety`) | tested-pass | The New Map dialog explicitly warns that the current map is replaced and Undo cleared, and tells the user to save a file first. Confirmed Empty replacement clears content/history and subsequently updates the sole browser draft; this is warned, intentional behavior. |
| 390px fresh map opens without overflow (`mobile-initial`) | tested-pass |  |
| Open/close tool bottom sheet (`mobile-sheet-tool`) | tested-pass |  |
| Open/close layers bottom sheet (`mobile-sheet-layers`) | tested-pass |  |
| Open/close places bottom sheet (`mobile-sheet-places`) | tested-pass |  |
| Tap pan tool at 390px (`mobile-tool-pan`) | tested-pass |  |
| Tap brush tool at 390px (`mobile-tool-brush`) | tested-pass |  |
| Tap eraser tool at 390px (`mobile-tool-eraser`) | tested-pass |  |
| Tap stamp tool at 390px (`mobile-tool-stamp`) | tested-pass |  |
| Tap label tool at 390px (`mobile-tool-label`) | tested-pass |  |
| Tap select tool at 390px (`mobile-tool-select`) | tested-pass |  |
| Touchscreen tap paints with chosen brush (`mobile-paint-tap`) | tested-pass |  |
| Mobile Undo restores tap pixels (`mobile-undo`) | tested-pass |  |
| Touchscreen tap places symbol (`mobile-stamp`) | tested-pass |  |
| Touchscreen tap creates editable place sheet (`mobile-place`) | tested-pass |  |
| Mobile Places entry opens inspector (`mobile-place-navigate`) | tested-pass |  |
| Mobile Help opens and closes (`mobile-help`) | tested-pass |  |
| Mobile File menu can open/cancel export (`mobile-file-dialog`) | tested-pass |  |
| Two-finger browser-level touch pinch increases zoom (`mobile-pinch`) | tested-pass |  |
| Mobile actions have no JS/CSP errors (`mobile-no-errors`) | tested-pass |  |
| Blocked IndexedDB shows unavailable status while tools still work (`autosave-unavailable`) | tested-pass |  |
| Manual JSON backup remains usable without IndexedDB (`manual-save-without-idb`) | tested-pass |  |
| Quota failure displays explicit recovery guidance (`autosave-quota-failure`) | tested-pass |  |
| Manual JSON backup remains usable after quota failure (`manual-save-after-quota`) | tested-pass |  |
| Escape cancels live vector drag and restores exact position (`label-and-stamp-move-cancel`) | tested-pass |  |
| Drag a label to a new map position (`label-move`) | tested-pass |  |
| Explicit rename button supports committing on blur (`layer-rename-blur`) | tested-pass |  |
| Hidden raster refuses paint and explains recovery (`hidden-layer-paint-guard`) | tested-pass |  |
| Missing symbol layer refuses stamp and explains adding layer (`missing-layer-stamp-guard`) | tested-pass |  |
| Last remaining layer cannot be deleted (`last-layer-delete-guard`) | tested-pass |  |
| Failed PNG encoding gives inline error and retry/cancel controls (`export-error-recovery`) | tested-pass |  |
| Cancel closes failed export dialog (`export-error-cancel`) | tested-pass |  |
| Failed JSON raster encoding opens readable error dialog (`save-error-dialog`) | tested-pass |  |
| 2000-item cap refuses additional stamp with feedback (`item-count-limit`) | tested-pass |  |
| Failure during editor initialization exposes error and Reload action (`startup-fatal-ui`) | tested-pass |  |
| Reload after transient initialization failure restores usable map (`startup-reload`) | tested-pass |  |
| Operate with a real pressure-sensitive stylus and hardware palm rejection (`physical-stylus`) | blocked | No physical input device is attached; DOM pen events and CDP touch do not establish hardware behavior. |
| Run action inventory in Safari/WebKit and Firefox (`alternate-browsers`) | not-tested | This independent action pass uses installed Chromium 150 only; no cross-browser claim. |
| Places selection keeps chosen marker visible above the mobile inspector sheet (`mobile-place-visible-navigation`) | tested-fail | Independent visual reviewer and parent confirmed Places → Hohenfurt centers its marker behind the open bottom sheet at 390px, 320px and 667px. Selection-state assertions pass; actual visibility/navigation fails. See sibling visual review report for repro/screenshots. |
