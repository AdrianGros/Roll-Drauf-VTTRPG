# C04 live follow-up: mobile header collision (Medium)

Source7474692d5 integrated in8848c621c, image75338d7ed86ad5e80854b2e672015a3716c2050fc16a9df37ffffb7494d8ee22.
36 integrated checks pass:20API,11new browser,5PlayChrome. PriorMedium scatter/grid
andLow eraser scratchmemory are closed, independently source-reviewed and pointertested.
C04 remains INCOMPLETE until this live responsive issue is fixed and verified.

Real390px editor screenshot and center hit-test show Library/Save receive pointer,
Import/Export do not: they wrap to y74,height34 while .mm-global-nav.vtt-main-topbar
overlaps their centre. Import rectx6,w87.6; Exportx95.9,w86.5; both center element
is globalnav. to_be_visible + no horizontaloverflow did NOT detect this. Desktop
editor/save/gridundo works, library→table sharing/retry live journey being completed.

Required bounded native fix within existing C04 markup/mapmaker.css/ui.js ownership:
account for actual wrapped header action height and existing global navigation,
keep both authored labels and filemenu/actions reachable, no hidden special URLs.
Preserve map viewport coordinates, gestures, newhistory/eraser, source snapshot and
P1 role separation. Check DE/EN and paper/night at390 and1440 after real auth/global
nav mounted; editor static preview fixture alone lacks this exact live navigation.
Do not edit shared navigation globally without explicit file handoff.

Real browser regression must open Import chooser (cancel without selecting), open
and close Export dialog through these visible buttons, Library, save ownproject,
actual centre receivesclick, no horizontaloverflow and no overlapped targets.
Recheck gridplacement/undo/erasercancel and table sharing follow-up after CSS.
Coordinator owns git/generator/review/tests/deployment/syntheticdata/credentials.
No worker Bash/prod/credentials or API fallback. Claude session735da98a-2ade-4535-8e75-bf97251a8652
can resume after quota reset19:10 Europe/Berlin. Other retained Low findings stay
recorded in review-final.md; do not silently turn them into new architecture.
