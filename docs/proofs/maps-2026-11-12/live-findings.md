# C04 Live Monitor: Medium mobile header overlap

Source8848c621c is committed, pushed and deployed as image75338d7e….
36 focused integrated checks pass;9 JS files/396 authored literals and2855 DE/EN
catalog sources verified. New dense scatter dedup and eraser cancel/undo/redo pass.

**Medium:** at390px the new Import/Export controls wrap to y74,height34, while
the existing main navigation overlays their centres. `to_be_visible` and no
horizontaloverflow passed but do not prove receiving pointer events. Actual
centre hit-test returns `mm-global-nav vtt-main-topbar` for both controls, while
Library/Save receive pointer normally. Screenshot and `mobile-hit-test.json`
prove it. C04 cannot close until real Import chooser and Export dialog are
reachable on mobile after header/navigation layout rework. Desktop editor/grid/
save succeeded through normal Maps navigation; table-sharing journey passes in live-maps-result.json with the normal mobile
Tisch-sheet entry, explicit sharing consent, failed activation and retry uploads once.

Required native rework is pinned in the C04 worker's live-rework.md. No hidden
URL, source-layout hack or falsely passing visibility-only test substitutes for
that fix. No schema changes. Claude quota currently blocks new implementation.
RetainedLow variantpool/frozenretry/replayedge notes stay in review-final.md.
