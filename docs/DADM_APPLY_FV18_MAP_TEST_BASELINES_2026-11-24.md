# FV18 bounded reconciliation of older map tests

Status: Apply approved for test maintenance within the retained FV18 verification scope; no application change. Permanent. Inputs: Claude's FV07/FV08 handoff, its reproduced baseline failures, the delivered FV04/FV05 contracts and current source. This does not close FV18 or authorize weakening security/geometry assertions.

The old label-placement tests expect automatic name-field focus. Delivered FV04 explicitly preserves canvas focus and repeated placement, with a deliberate `editPlacedLabel` action to focus the existing name field. Update those two tests to assert the delivered focus rule, use that action when testing text-entry/lore safety, and retain every Escape/literal-text/XSS/Undo assertion.

The old occupied tile-grid test expects silent rescaling from 32 to 48. The delivered FV05 safety contract explicitly refuses that operation. Assert identical grid/cells/history after the refused change, choose the explicit new empty layer, verify its 48-pixel grid, then Undo that layer creation and retain all original file/autosave/roundtrip/pixel assertions.

The narrow panel scrolls independently. Explicitly scroll the brush-size control into view through Playwright's normal scroll action before checking its viewport position; retain panel toggling, actual painting and no-horizontal-overflow assertions. A failed scroll remains a failure, not an exemption.

The static preview test confuses the authenticated app's root login navigation with a required preview asset. Parse resource/anchor tags: permit exactly the `libraryLogin` anchor's `/login.html` app route, while continuing to reject remote URLs, other absolute paths and missing local script/style/asset files. Do not make the real login route relative to the static directory.

Severity: medium stale assertions are resolved by the explicit shipped owner contracts above. No new dependency, schema, permission, source artwork or image generation. Existing playtable hidden-layer-widget failure is outside this bounded map test maintenance and remains FV18 pending separate discovery. Next: implement these test-only corrections and run the five affected cases; include their evidence in integration Monitor, without a blanket full-suite claim.
