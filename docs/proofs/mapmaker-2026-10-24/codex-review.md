# Codex independent Monitor review

Status: complete. Scope: verify Claude Opus 5.5’s map-maker prototype, preserve existing work, curate and verify free assets. No production deployment or schema changes.

## Resolved findings

| Finding | Final disposition |
|---|---|
| R1: stale raster cache and mixed asynchronous save snapshots | Raster revisions/pixels, metadata and items captured synchronously; actual Chromium red→blue recheck passes |
| R2: cancelled drag/scatter persisted in autosave | All mutating gestures defer autosave; completion/cancellation requeue it; regression tests pass |
| R3: added raster layers exceed the importer’s area limit | Cumulative area checked before allocation; exported projects remain within the contract |
| R4: newer edits lose unsaved protection while a file save finishes | Document generations retain dirty state and distinguish newer edits/replacements |
| R5: off-map placement/drag emits invalid coordinates | Off-map placement rejected and drag coordinates constrained; independent minimum-zoom export validates |
| Low: implicit favicon request returns404 in full Chromium | Explicit relative local SVG icon; failing cleanliness test rerun successfully |
| Medium operational: root-owned 0600/0700 prototype files | Codex normalizes only new prototype/artifact paths to admin ownership, 0644 files and 0755 directories; admin read check passes |

## Evidence

- Full targeted suite: 34 passed under headless-shell Chromium 1234.
- Independent Chromium 1243 run: seven review/Flask checks passed; the eighth’s data assertions passed but its console check found the favicon404. After the favicon fix, that test and all seven static checks passed (8 passed in 7.63 s).
- Independent asynchronous snapshot and off-map placement reproductions now pass.
- Final desktop 1440 × 1000 and phone 390 × 844 screenshots reviewed; no page/console errors or horizontal overflow.
- Editable sample project and 2400 × 1600 PNG downloaded through the actual editor UI.
- All 38 curated stamps and 2 textures match their SHA-256 manifest values.
- 49 pre-existing modified/untracked files retain their original contents; no unexpected tracked or staged changes.

Artifacts: prototype-desktop.png, prototype-mobile.png, prototype-stamps.png, silbermark.png, silbermark.rdmap.json, codex-verification.json, codex-final-tests.txt, asset-contact.jpg. Retention: immutable proof of this prototype.

Residual low risks: no Safari/Firefox or real pen/touch device verification; canvas memory may be high on small phones. Local draft storage is per browser. Campaign upload uses the existing PNG workflow. Wider repository tests were not run because the change is an additive static prototype.

Next step: use the prototype and capture map-making feedback. A future Apply pass can define authenticated campaign publishing and server-side drafts.
