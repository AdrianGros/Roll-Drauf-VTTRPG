# Mapmaker visual and usability review — 2026-10-24

**Phase:** DAD-M Monitor. **Status:** before review complete; branding after review pending.
**Input summary:** Independently exercise rendered visual states and assess hierarchy, responsive structure,
branding, focus, and the first-use edit → editable file → PNG → campaign handoff journey.
**Boundary:** Read-only product sources; browser-local documents/downloads only. No production, account,
server data, fixes, or recursive agents. Existing map artwork and export palette are outside the chrome
redesign boundary.

## Evidence and observed results

- Chromium 1243, actual browser UI, five CSS viewports: 1440×1000, 1024×768, 390×844, 320×568,
  667×375 landscape. Fresh browser context for each viewport.
- `before-<viewport>-<state>.png`: 40 screenshots covering initial editor, file menu, export dialog,
  help dialog, layers, places, selected place inspector, stamp palette. Screenshots were viewed, not
  judged solely from DOM bounds.
- `before-metrics.json`: geometry, visible control sizes/font/colors, page overflow, runtime errors.
  Offscreen controls inside scroll containers are recorded, **not automatically classified as defects**.
- `before-probes.json`: measured selected marker occlusion, header help visibility, help overflow,
  keyboard focus styling, actual download journey.
- `before-*-place-probe.png`, `before-*-help-top.png`: focused reproduction screenshots.
- `before-dialogs.json` plus six `before-*-new/import-error/restore.png` screenshots: New Map,
  invalid-import feedback, and local autosave recovery dialogs at1440 and320. No horizontal overflow;
  recovery restores the edited title through the visible action. Destructive New Map selection was not
  needed for this visual check (dialog cancel was exercised).
- `before-journey.rdmap.json`, `before-journey.png`: actual UI downloads after one paint action.
  The JSON retains five editable layers; PNG is 2400×1600. Export dialog gives the existing campaign
  upload workflow and explains that JSON is required for future editing.
- No JavaScript page errors in the 40 captured baseline states. This is not a security audit.
- Desktop and tablet have a coherent left-tool / map / inspector hierarchy. The responsive bottom
  toolbar and scrollable sheet preserve the same concepts. Mobile tool targets are about 52×53 px.
  Desktop layer action icons are 30×30 px; top icon actions nominally 34×34 px.

## Findings

| ID | Severity / type | Evidence and impact | Recommended bounded next action |
|---|---|---|---|
| V1 | medium / layout defect | At 320 px, Help is at x336.42…358.42 and fully outside the viewport; at 390 px, its right edge is392.23. Clicking via automation scrolls the root left38 px at320, shifting the entire editor. See `before-smallphone-initial.png`, `before-metrics.json`, `before-probes.json`. | CSS header sizing/spacing must keep every header action within viewport at320 and390, with no root horizontal scroll. |
| V2 | medium / layout defect | Help keyboard grid overlaps adjacent columns on desktop/tablet, and overflows horizontally when narrow. `before-desktop-help.png` shows Bearbeiten descriptions crossing behind the Ansicht shortcuts, although dialog scrollWidth equals clientWidth. At320: dialog clientWidth294 vs scrollWidth340; grid width250 vs scrollWidth318. At667: dialog641 vs649; grid597 vs627. Descriptions are visibly cut. See also `before-smallphone-help-top.png`, `before-landscape-help-top.png`. | Help columns/shortcut rows must wrap or stack without overlap; no horizontal help overflow at the five viewports. Vertical scrolling is acceptable. Visual inspection is required in addition to width checks. |
| V3 | medium / functional usability | Places→Hohenfurt centers its map point behind the open properties sheet. At390 point(195,416), sheet top410.64; at320 point(160,278), sheet top256.09; at667 point(333.5,181.5), sheet top148. `elementFromPoint` at each marker returns `tab-layers`, not mapCanvas. Desktop/tablet markers are visible. See `before-probes.json` and `before-*-place-probe.png`. | Separate Apply/Deploy follow-up: when choosing a place, keep its marker visible in the actual uncovered map rectangle while opening inspector. Preserve current zoom, selected object, place text/lore, and desktop behavior. Test all three narrow viewports, including closed→open and already-open sheet. No JS fix belongs inside the aesthetic pass. |
| V4 | medium / visual accessibility | Actual keyboard focus on the layer visibility button is a2 px `#f2c66d` outline on `#fffaf0`: contrast1.54:1. On paper `#f3e8cc` it is1.32:1; white1.61:1. The same ring on dark chrome is9.06:1. A bright ornament color is difficult to distinguish on pale controls. | Chrome aesthetic pass should use a dark, visible paper-surface focus indicator while retaining visible dark-surface focus. Verify actual keyboard navigation. |
| V5 | low / usability | Opening Help on short viewports focuses the only button, Close, scrolling content to bottom: initial scrollTop300 at320,198 at667. Heading and tool intro are initially hidden. `before-smallphone-help.png` vs `before-smallphone-help-top.png`. | Start Help at its heading while keeping keyboard focus visible and dialogs keyboard dismissible. |
| V6 | medium / requested branding gap | Existing chrome uses teal `#1f2b2e`/`#283639`, yellow parchment `#f3e8cc`, brown actions, Literata on tool controls, and a generic star without visible Roll Drauf identification. Canonical `vtt/static/css/theme.css` specifies plum binding, paper/ink, rubric actions, gold ornament, system UI sans on tools. | Complete the explicitly requested aesthetic harmonization using canonical values and existing brand assets, without changing map artwork, generated document content, or exports. |

Contrast figures use relative luminance `(max(L1,L2)+0.05)/(min(L1,L2)+0.05)` after standard sRGB
linearization. They are measured style observations, not a claim of a complete WCAG audit.

## Design judgments and non-findings

- The narrow map is deliberately top-aligned (`app.js` fit), leaving blank dark stage on a tall phone.
  This keeps the starter map clear of an open sheet. That tradeoff is **not classified as a bug**.
- Panel scrolling, and long stamp palettes scrolling within the panel, keep controls reachable.
  A DOM rectangle below the viewport is not sufficient evidence of an inaccessible control.
- At320 the last tool is partially clipped by a horizontally scrollable rail. All six tools remain
  reachable, but discoverability of horizontal scrolling is modest (low usability observation).
- World-map text is small at fit zoom on a phone; zoom controls are provided. No change to exported
  label sizes or artwork is requested by this chrome review.
- Campaign upload is documented, not integrated in this prototype. No claim was made that a live
  account campaign upload was exercised.

## Residual risks and next step

Physical touch/pen, Safari, Firefox, mobile browser chrome/safe-area behavior, assistive technology,
and the authenticated live campaign handoff remain outside this visual run. Automated Chromium
viewport simulation is evidence for responsive CSS, not a real-device certification.

Artifacts: screenshots, metrics, probes, downloaded sample files, this report (retention: milestone proof;
baseline images and JSON are immutable). Harnesses `capture.py`, `probe.py`, and `dialogs.py` are included
here, with working copies under `/tmp/roll-drauf-mapmaker/dao-visual/`. Set `DAO_PHASE=after` to retain
the immutable before proofs when re-running with the prepared Python/Playwright environment.
Product sources were not edited by this reviewer.

**Recommendation:** do not close visual acceptance while medium findings remain unresolved/unaccepted.
Parent coordinates the bounded branding implementation and explicit functional follow-up for V3;
repeat the same five-viewport captures after sources settle.
