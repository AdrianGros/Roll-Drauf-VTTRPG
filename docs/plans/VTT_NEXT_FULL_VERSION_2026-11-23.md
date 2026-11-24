# Roll Drauf VTT next full version

Status: the owner defined this full-version goal on 23 November 2026; delivery remains outstanding. Phase: bounded packet Apply, Deploy and Monitor within the retained release scope. Completed work forms the baseline; all remaining packets below belong to the next full version.

## Full version goal

Complete, integrate, deploy and verify all retained outstanding packets below as the next full VTT version. Preserve delivered functionality, private data and server-enforced Player/DM separation. A packet closes only with delivery evidence or an explicit owner scope decision.

All retained outstanding packets from the two 2026-11-23 reviews, the older explicitly open feedback items, and current release-quality findings. Formerly lower-priority terrain, radial palette and curved-text requests remain in this version goal.

The goal baseline is `7e0a3c859`, with evidence `8a4dca5ed`. The current live application is `8395527e9`, image `sha256:287563aeb13e38f220b197e4b702d2ee2ad82d3b0089a8a5729467c59597a7bc`. The working release name is **next full version**; no version number or deadline has been assigned. Each functional slice is delivered separately; this register preserves the full release goal.

## Current packet progress

Owner assignment, 24 November: Claude implements FV07 and FV08 in `/home/admin/projects/roll-drauf-vtt-fv07-fv08-20261124` (branch `feat/mapmaker-fv07-fv08-20261124`). Both are now integrated, corrected, committed/pushed, deployed and live verified by Codex; see [delivery Monitor](../DADM_DEPLOY_MONITOR_FV07_FV08_2026-11-24.md). The handoff worktree is preserved.

Asset constraint, 24 November: scan the RD Team Discord for Ducky’s existing assets and permission notes. Generate no new images and use none of her artwork in a generative workflow. Preserve originals and source-specific restrictions; labeling never grants missing rights.

Owner content decision, 24 November: defer unavailable rules additions (including the missing English Oglan and additional character-background sources) from this full version and continue the technical packets. Technical workflows, available source provenance and Ducky's artwork constraints remain in scope. The [bounded Team source scan](../DADM_DISCOVER_FV16_CONTENT_SOURCES_2026-11-24.md) found no such rules inputs.

Owner decisions, 24 November: public AI-generated images are allowed with a required AI label and the existing rights confirmation (FV16). The unidentified older 0% report is disregarded at the owner’s instruction; FV17 closes by scope decision, without claiming a technical fix.

FV04 is [delivered and live verified](../DADM_MONITOR_FULL_VERSION_LAYERS_2026-11-23.md). FV05's occupied-grid safety/new-layer workflow and reference grid, plus FV06's File-menu Escape fix, are also live; the remaining features of both packets stay open. FV01 now has a [partly delivered creator interface](../DADM_MONITOR_FV01_CREATOR_LABELS_2026-11-24.md): cataloged labels follow the rules language, with safe live switching and unchanged canonical data. The [next content slice](../DADM_DEPLOY_MONITOR_FV01_CREATOR_CONTENT_2026-11-24.md) adds 663 reviewed core/spell names,52 terms and genuine English details, with stable spell checks and live DM/Player proof. The [equipment slice](../DADM_DEPLOY_MONITOR_FV01_CREATOR_EQUIPMENT_2026-11-24.md) adds 184 reviewed equipment identities and mastery/property/coin terms (847 names/74 terms total), with live canonical armor/mastery/settings/reload proof. The [species-label slice](../DADM_DEPLOY_MONITOR_FV01_SPECIES_LABELS_2026-11-24.md) adds73 source-backed traits/options/size/type/damage labels (147 terms total), with DM/Player settings/reload proof and scoped cleanup. Option descriptions, remaining labels, validation and editor coverage stay open. Rapid autosave/click timing remains an FV18 follow-up. Unused trinket data has no current UI consumer; this does not add a trinket feature. The earlier 339-spell facet inventory remains candidate-only; actual core/spell identities now have separate reviewed source pins. [Ducky source discovery](../DADM_DISCOVER_DUCKY_ASSETS_2026-11-24.md) preserves50 original graphics candidates without image processing or generative use. The overall goal remains active.

FV02 [creator view clarity is delivered](../DADM_DEPLOY_MONITOR_FV02_CREATOR_VIEWS_2026-11-24.md): both starting views, same-draft switching/reload and independent language settings pass normal DM/Player journeys. Controls fit at390px; unavailable additional rules/background content closes by owner deferral, not by invented content. FV18 retains the recorded startup-timing observation.

FV06 [brush controls and quick palette are delivered](../DADM_DEPLOY_MONITOR_FV06_BRUSH_CONTROLS_2026-11-24.md): recent colors, opacity/size/material shortcuts and the temporary tools/colors palette pass DM/Player live journeys and scoped cleanup. FV15 is now [assigned to actual Claude Code](../CLAUDE_HANDOFF_FV15_2026-11-24.md) in an isolated worktree at base `1f9179d5b`, using the existing subscription and file tools only. Codex continues FV01 and retains all testing/integration/deployment. Assignment is not delivery.

## Already delivered

- Reliable solo session creation/start, scheduled/ready handling, double-click protection, retry visibility and explicit authorized DM entry.
- Consistent numbered contents with working destination links and an active navigation group that stays marked when closed.
- Map-editor bracket hotkeys, per-asset/crop sizes for the page session, honest unknown-trait filters/counts/reset, usable waypoint editing, recent place symbols, image-brush explanations and staged Escape.
- Bronze/teal surfaces and ordinary counters follow the chosen accent; class facts use a readable responsive layout.
- Earlier integrated work remains the baseline: grouped playtable tools, free pan/zoom/FIT, readable scene management, movable persistent windows, calendar notes/reminders/one-shots, companions, private chat threads, private own map assets, Atlas links/publication and masked 2D floors.

The goal baseline passed seven live journeys and the added contents-link regression; its temporary QA users and data were removed. The subsequent FV04 delivery passed two authenticated Maps journeys; the FV01 label slice passed two more creator/settings/reload journeys. Both deliveries record scoped QA cleanup in their own Monitors. Claude completed a source review with no supported blocking findings. The full repository suite has recorded pre-existing failures and verification gaps; these are assigned to FV18. See the [delivery monitor](../DADM_MONITOR_FEEDBACK_HARNESS_2026-11-23.md).

## Full version work packets

All eighteen packets below belong to the next full version. FV04 is delivered; other statuses show partial delivery, design progress or remaining work. Lower priority sets the order; it does not remove terrain tools, curved text or the radial palette from the goal. An unresolved design is not an approved implementation contract.

| Packet | Scope | Priority | Status |
| --- | --- | --- | --- |
| FV01 | Character module language | P1 | Partly live |
| FV02 | Creator workflow and backgrounds | P2 | Delivered live; unavailable rules additions deferred by owner |
| FV03 | Navigation and responsive page layouts | P1 | Planned |
| FV04 | Layer targets and editor panels | P1 | Delivered live |
| FV05 | Reference grids snapping and tile transforms | P1 | Partly live |
| FV06 | Brush controls colors and quick palette | P1 | Delivered live |
| FV07 | Object list and label placement | P1 | Delivered live |
| FV08 | Path drawing and editing modes | P1 | Delivered live |
| FV09 | Line styles node curves and text geometry | P1 | Plan and inputs needed |
| FV10 | Own images and tileset packages | P1 | Plan and inputs needed |
| FV11 | Catalog metadata and personal sets | P1 | Plan and inputs needed |
| FV12 | Land fill and coastline tools | P2 | Planned |
| FV13 | World campaign and map place relationships | P2 | Plan and inputs needed |
| FV14 | Campaign homebrew approvals | P2 | Planned |
| FV15 | Campaign quota extension request | P2 | Delivered and live verified |
| FV16 | Content provenance and publication policy | P2 | Plan and inputs needed |
| FV17 | Identify the deferred zero percent control | P2 | Closed by owner scope decision |
| FV18 | Integrated verification and full version release | release gate | In progress; five obsolete map assertions reconciled |

### FV01 Character module language

The selected rules language controls the entire character creator and editor while the surrounding website keeps its own UI language.

Sources: T3, 2026-11-23:N26.

Acceptance:

- Verify DE/DE, DE/EN, EN/DE, EN/EN and automatic selection, including reload and existing drafts.
- Translate module labels, help, validation, choices, class details, weapons, spells and invocations from approved content; preserve canonical IDs, user text, selections and derived values.
- Cover the character editor as well as the creator; retain one validated rules engine.

### FV02 Creator workflow and backgrounds

Make guided creation and the full form easy to distinguish while preserving existing approved background workflows.

Sources: T4 remaining, 2026-11-23:N22, 2026-11-23:N23.

Acceptance:

- Both modes remain available and use the same draft; mode labels and hierarchy explain their purpose.
- Available approved backgrounds preserve intended-language, choice and prerequisite behavior; unavailable additional rules content is deferred by the owner.

Dependencies: FV01.

Decisions or inputs:

- The exact additional backgrounds and their usable sources must be selected; FV16 tracks the shared content inputs.

### FV03 Navigation and responsive page layouts

Resolve the remaining Atlas, conversations, header and narrow-screen layout reports while retaining the delivered active navigation and contents.

Sources: T2 remaining, 2026-11-23:N19, 2026-11-23:N20, 2026-11-23:N10, feedback monitor character archive width.

Acceptance:

- Reproduce direct entry, internal navigation, Back/Forward and delayed loading; keep one header and stable page state.
- Check Atlas, conversations, the character archive and editor selects at 390/1440 pixels in both palettes and languages; separate native dropdown width from actual document reflow.
- Controls and content remain reachable without accidental horizontal overflow or canvas displacement.

### FV04 Layer targets and editor panels

Respect the deliberately selected compatible layer, provide a compact layer overview and keep frequently used tools and assets easy to reach.

Sources: M2, S2 layer controls, S4, 2026-11-23:E09, 2026-11-23:E10, 2026-11-23:E20, 2026-11-23:E21, 2026-11-23:E23, 2026-11-23:N01, 2026-11-23:N03, 2026-11-23:N16 remaining.

Acceptance:

- Drawing uses the selected lower compatible layer; reuse existing compatible layers and never silently convert raster layers or edit hidden layers.
- Layer controls expose type, object counts, filtering, visibility and a defined recent-use view; structural changes support Undo.
- Put asset choices before rare settings, keep panel and placement controls stable, and verify keyboard and touch access at 390/1440 pixels.
- Reproduce tile-as-symbol palette, preview and placed-object behavior separately; explain the distinct erase targets for raster pixels, tiles and stamps.

Decisions or inputs:

- Specify whether recent layer use lasts for the session or persists, and define the compact bar and panel interactions in the packet Apply.

### FV05 Reference grids snapping and tile transforms

Separate the visible reference grid, snapping, calibration and deliberate changes to tile content; add native tile rotation.

Sources: S2 reference grid, S10, 2026-11-23:N04, 2026-11-23:N05, 2026-11-23:N06, 2026-11-23:N07, 2026-11-23:N09.

Acceptance:

- Keep a reference grid visible during free placement without forcing snapping.
- Changing grid size must not silently move existing tiles; provide an explicit safe new-layer or transform workflow with Undo and preserved old documents.
- Support bounded numeric calibration and a clear field-count/map-size workflow; define the requested 2 by 2 snap example explicitly.
- Native cell rotation survives validation, save/reload, PNG/ZIP, library and Atlas/table snapshots.

Dependencies: FV04.

Decisions or inputs:

- Decide tile-grid transformation semantics, snap anchors and the versioned cell-rotation format before implementation.

### FV06 Brush controls colors and quick palette

Add the last eight reusable colors, opacity shortcuts, faster brush and size selection and the requested temporary radial palette.

Sources: M1 remaining, S5, S11 radial menu, 2026-11-23:E02, 2026-11-23:E04, 2026-11-23:E07, 2026-11-23:E08, feedback monitor File menu Escape.

Acceptance:

- Committed custom colors are selectable again; keys, sliders and previews show the same values.
- New shortcuts and modifiers preserve zoom, pinch, Alt-wheel ordering, middle-button pan, text entry and Undo.
- Define quick brush switching as well as sizing; the radial palette has a conflict-free trigger and keyboard/touch fallback.
- Escape closes the File menu without also changing the placement tool.

Decisions or inputs:

- Define the new gesture bindings and recent-color persistence in Apply; proposed bindings in the Claude plan are candidates.

### FV07 Object list and label placement

Provide one selectable overview of map objects, a translucent label-and-symbol preview and convenient rotation presets.

Sources: S3, 2026-11-23:E16, 2026-11-23:E17 discoverability, 2026-11-23:N12, 2026-11-23:N13.

Acceptance:

- The list and map select the same paths, stamps, tile content and labels; filtering uses existing document and selection state.
- Preview the actual label and optional symbol before placement without making advance configuration mandatory.
- Rotation presets and existing free rotation produce the same stored result and a clear Undo step; keep path naming discoverable.

Dependencies: FV04.

### FV08 Path drawing and editing modes

Allow paths to be drawn by clicking individual nodes and make switching between drawing and editing explicit.

Sources: S6, 2026-11-23:E12, 2026-11-23:E14.

Acceptance:

- Freehand drawing and click-to-add-node mode coexist; finish, remove-last-node and cancel actions are defined.
- Editing reuses the delivered select/node controls; existing paths remain unchanged until deliberately edited.
- Undo/Redo and save/reload preserve the exact committed path.

Dependencies: FV04.

### FV09 Line styles node curves and text geometry

Add local node curvature, road/trail/river/border styles, dashed and dotted lines, free colors, river-to-sea color treatment, place relations, letter spacing and curved labels.

Sources: S7, S11 curved text, 2026-11-23:E13, 2026-11-23:E15, 2026-11-23:E17 relations, 2026-11-23:E18, 2026-11-23:E19, 2026-11-23:N14, 2026-11-23:N15.

Acceptance:

- Local corner/curve controls remain distinct from whole-path smoothing; crossings connect only on an explicit action.
- Path-to-place relations and the two-color sea treatment have defined semantics; existing names and IDs remain valid.
- Tracking and curved text have matching preview, selection geometry and exported appearance.
- Client/server validation, resource limits, Undo, save/reload, PNG/ZIP, library, Atlas and table snapshots agree; old documents retain their appearance.

Dependencies: FV07, FV08.

Decisions or inputs:

- Define optional/versioned line, node, relation and text fields and compatibility behavior in Apply.

### FV10 Own images and tileset packages

Make upload, crop and pixel tools discoverable, support editing existing private assets and add a genuine tileset-package workflow.

Sources: M5 content tools, S8, 2026-11-23:E24, review web existing custom asset editing gap.

Acceptance:

- Existing upload/crop/pixel creation remains available from relevant tools, including tiles.
- Define the sheet/package format, grid metadata and errors; enforce limits before expensive decoding.
- Edit an existing own image without silently changing unrelated references; preserve source and license metadata.
- Import/edit/place/Undo/save/reload/library/Atlas/table/PNG/ZIP round trips keep pixels and provenance; foreign projects cannot use cached private assets.

Dependencies: FV04, FV05.

Decisions or inputs:

- Confirm the tileset package contract and the edit/revision behavior for existing assets; FV16 governs any public release.

### FV11 Catalog metadata and personal sets

Complete catalog classification and world-map/battlemap discovery, personal sets and hidden assets, and address confirmed content gaps.

Sources: M4 remaining, S9, 2026-11-23:E26 remaining, 2026-11-23:E27, 2026-11-23:N08, clipped tree report.

Acceptance:

- Audit actual metadata and inventory before assigning style, perspective, resolution, category or intended use; retain the delivered unknown bucket, counts and reset.
- Personal hidden choices and named sets have defined scope and persistence; project asset IDs remain stable.
- Add approved artwork only for demonstrated gaps; inspect the reported clipped tree against its exact source/crop.

Dependencies: FV04.

Decisions or inputs:

- Choose account or local persistence for sets; supply the clipped tree asset ID; additional artwork needs approved content tracked in FV16.

### FV12 Land fill and coastline tools

Fill a closed land outline, add rough/triangular/polygon brush options and render coastline waves.

Sources: M6, S11 terrain, 2026-11-23:E01, 2026-11-23:E05, 2026-11-23:E06.

Acceptance:

- Fill only the intended active raster region with one Undo action; preserve coastline, sea and other layers.
- New tips and roughness preserve current brush feel, texture toggle, image brushes and chosen colors.
- Coast waves and new marks survive save/reload and exports within defined budgets.

Dependencies: FV04, FV06.

### FV13 World campaign and map place relationships

Make Atlas/world-to-editor navigation and map-place linking coherent, including multiple campaigns in a DM world.

Sources: T5, 2026-11-23:N11.

Acceptance:

- Use the existing authorized Atlas editing and publication paths; link locations to the intended world entries.
- Define how several campaigns use one world, which data is shared and who can edit or publish it.
- World grants and campaign membership remain separate; Reader and Player responses never reveal private sources or DM-only geometry.

Dependencies: FV09, FV10.

Decisions or inputs:

- The cross-campaign ownership, sharing and publication contract needs its own explicit Apply decisions.

### FV14 Campaign homebrew approvals

Let an authorized DM approve specific published homebrew choices for a campaign using an explicit allowlist.

Sources: 2026-11-13:N07, B04 remaining.

Acceptance:

- Only approved published choices appear in that campaign and use the existing creator/progression validation.
- A DM approval does not bypass arbitrary prerequisites, authorize unpublished content or elevate a Player context.
- Test unauthorized changes, revocation, existing characters and creator/editor consistency.

Dependencies: FV01.

### FV15 Campaign quota extension request

Expose the existing authorized route for requesting campaign-capacity extensions.

Sources: 2026-11-13:S15, B10.

Acceptance:

- Users can find the request path, understand the current capacity and see the request outcome.
- Keep approval and actual quota changes under the existing authorized administration contract; a request cannot grant itself slots.
- Do not automatically alter real users, add a Donutarian test slot or introduce a payment system.

Implementation assignment: [completed Apply](../DADM_APPLY_FV15_CAMPAIGN_QUOTA_2026-11-24.md), [exclusive Claude handoff](../CLAUDE_HANDOFF_FV15_2026-11-24.md). Finite existing quota/creator eligibility, one pending request, bounded submission history, explicit owner/admin review and stale/account guards are specified. Submission never grants slots. No default entitlement or billing change. Claude has returned [implementation/proposed tests and a precise handoff](../DADM_DEPLOY_FV15_CAMPAIGN_QUOTA_2026-11-24.md) in the isolated worktree. Codex corrected the DB pending-key check, conflict response helper and native hidden-state CSS, and verified114 distinct cases across overlapping API/browser/isolated-PostgreSQL/existing-profile runs. See [actual handoff/root review evidence](../proofs/fv15-claude-handoff-2026-11-24/assignment.json). [FV15 is now delivered and live verified](../DADM_DEPLOY_MONITOR_FV15_CAMPAIGN_QUOTA_2026-11-24.md): final catalog preserves newer species work,114 targeted cases plus4 overlapping integration checks pass, additive schema/constraints verify, four normal synthetic role journeys and audit/state checks pass, all scoped QA data/credentials removed. No real quota adjustments.

### FV16 Content provenance and publication policy

Preserve truthful content provenance, implement the decided public AI-content policy and resolve the outstanding requests for additional approved rules or artwork.

Sources: 2026-11-23:E25, 2026-11-23:N08 content inputs, 2026-11-23:N23 content inputs, review web English Oglan and additional system content.

Acceptance:

- Keep source/license information and rights confirmation through private editing and export; public policy is a separate explicit owner decision.
- Use genuine approved material for available artwork; unavailable rules additions including English Oglan/backgrounds are deferred by the owner. Never fabricate an official translation or content rights.
- Record the DSA/additional-system request against available sources and actual required mechanics before promising support; do not imply a complete new rules engine.
- Missing inputs remain visible until supplied or explicitly deferred by the owner.

Decisions or inputs:

- Public AI policy is decided: require an AI label and the existing rights confirmation. Unavailable rules content is explicitly deferred; available artwork provenance and the non-generative-use restrictions remain technical scope.

### FV17 Identify the deferred zero percent control

Closed by explicit owner scope decision, 24 November 2026. The owner does not know the origin of the old 0% report and instructed that it may be disregarded unless its identity is known. Existing evidence only records an unidentified deferred control; it establishes no reproducible identity.

Sources: 2026-11-13:N11 and the owner's 24 November reply. No range/minimum was changed. This closure is a scope decision, not an implemented fix. It does not reinterpret the report as brush size, eraser softness or grid calibration.

### FV18 Integrated verification and full version release

Deliver and verify the complete retained scope on the live VTT, with an accurate owner checklist and recoverable releases.

Sources: B11, feedback harness residuals, tool groups residuals, canvas scenes residuals, new full version acceptance.

Acceptance:

- Every required packet is implemented and verified, or has an explicit owner-approved scope disposition; a missing input is never counted as delivered.
- Run the affected API, permissions, storage, format and browser checks; triage obsolete capability/string/gesture expectations and investigate the template-placement, square measurement, two-client fog, initiative and floor timing gaps.
- Verify Chromium/Firefox, 390/1440 pixels, DE/EN and both palettes; retain 320-pixel/touch coverage for the playtable. Exercise a physical DE keyboard and actual external/OAuth journeys when the owner can supply that interaction; report any agreed gap.
- Repeat complete normal UI journeys across campaigns/session entry, Player/DM, character creation/editing, map editing/library/Atlas, chat, calendar, companions and floors.
- For each functional slice commit/push, reconcile the running source/image, preserve unrelated live work, record backup/migrations/rollback, deploy only the app when appropriate, verify live and remove QA data.
- Resolve blocking findings, record owner acceptance for the new full version and keep the previously accepted playtable baseline intact.

Claude returned [bounded source discovery](../DADM_DISCOVER_FV18_INTERACTION_TIMING_2026-11-24.md), with [root qualifications](../proofs/fv18-interaction-timing-2026-11-24/discovery.json). Local instrumentation and later Apply remain required; no causal fix is claimed.

FV18 timing follow-ups: rapid Firefox390 creator autosave/card/source clicks sometimes did not apply; settled label journeys pass without a cause/fix claim. One quota profile-entry/nav composition click exceeded8s after DOM replacement, then passed unchanged on retry. Retain these with the existing creator startup observation.

Dependencies: FV01, FV02, FV03, FV04, FV05, FV06, FV07, FV08, FV09, FV10, FV11, FV12, FV13, FV14, FV15, FV16, FV17.

## Work order

- 1: FV01, FV03, FV04, FV05. Language, remaining navigation/layout, layer targeting and protection against silent grid movement.
- 2: FV02, FV06, FV07, FV08. Creator clarity, faster controls, object/label UX and path modes.
- 3: FV05, FV09, FV10, FV11, FV12. Complete grid/format work, lines/text, private assets, catalog and terrain.
- 4: FV13, FV14, FV15. World/campaign relationships, homebrew approval and quota requests.
- Throughout: FV16, FV17, FV18. Request needed decisions and inputs early; maintain verification per slice and finish combined acceptance.

FV05 has an early safety slice and later format extensions. FV16 and FV17 inputs should be collected early rather than waiting for their implementation wave. FV18 verification accompanies every slice and ends with the combined release acceptance.

## Feedback coverage

IDs are namespaced by review date: for example, the November 13 N07 is campaign homebrew approval, whereas the November 23 N07 is map-grid calibration. Existing capabilities are not counted as missing features.

### First editor review

| Source item | Current status | Remaining packet | Note |
| --- | --- | --- | --- |
| E01 | open | FV12 |  |
| E02 | open | FV06 |  |
| E03 | delivered | FV18 | DE character-based hotkeys delivered; physical DE hardware verification remains. |
| E04 | open | FV06 |  |
| E05 | open | FV12 |  |
| E06 | open | FV12 |  |
| E07 | open | FV06 |  |
| E08 | open | FV06 |  |
| E09 | delivered | Delivered | FV04 delivered and verified at 207c8e9fc. |
| E10 | delivered | Delivered | FV04 delivered and verified at 207c8e9fc. |
| E11 | delivered | Delivered | Existing waypoint editing is now reachable through the correct select mode. |
| E12 | open | FV08 |  |
| E13 | open | FV09 |  |
| E14 | open | FV08 |  |
| E15 | open | FV09 |  |
| E16 | open | FV07 |  |
| E17 | partial | FV07, FV09 | Path naming exists; discoverability and explicit place relations remain. |
| E18 | open | FV09 |  |
| E19 | open | FV09 |  |
| E20 | delivered | Delivered | FV04 delivered and verified at 207c8e9fc. |
| E21 | delivered | Delivered | FV04 delivered and verified at 207c8e9fc. |
| E22 | delivered | Delivered | Per-asset and crop sizes are remembered for the page session. |
| E23 | delivered | Delivered | FV04 delivered and verified at 207c8e9fc. |
| E24 | partial | FV10 | Private upload, crop and pixel creation exist; full tileset packages and existing-asset editing remain. |
| E25 | policy decided; implementation open | FV16 | Required AI label and existing rights confirmation. |
| E26 | partial | FV11 | Honest filter matching, unknown traits, counts and reset delivered; semantic classification and catalog completion remain. |
| E27 | open | FV11 |  |

### Second review

| Source item | Current status | Remaining packet | Note |
| --- | --- | --- | --- |
| N01 | supported case verified report specific catalog follow up | FV11 | Fixture preview and placement work with the chosen tile; no asset-loss fix claimed for unspecified original content. |
| N02 | delivered | Delivered | Image-brush original colors and material switch are explained. |
| N03 | delivered | Delivered | FV04 targeting and layer overview delivered; distinct raster/tile/stamp representations and mixed erase/Undo scopes verified at 207c8e9fc. |
| N04 | design needed | FV05 |  |
| N05 | delivered | Delivered | Reference grid retained across tools independently of snapping at legible grid zoom, verified at 207c8e9fc. |
| N06 | open | FV05 |  |
| N07 | design needed | FV05 |  |
| N08 | open | FV11, FV16 |  |
| N09 | design needed | FV05 |  |
| N10 | reproduce | FV03, FV04 |  |
| N11 | design needed | FV13 |  |
| N12 | open | FV07 |  |
| N13 | open | FV07 |  |
| N14 | design needed | FV09 |  |
| N15 | open | FV09 |  |
| N16 | delivered | Delivered | Stable placement controls, explicit existing-field label editing and staged/menu Escape verified at 207c8e9fc. |
| N17 | delivered | Delivered | Place-symbol picker offers recent symbols and the current palette. |
| N18 | delivered | Delivered | Solo ready/new sessions start safely through an explicit authorized DM context. |
| N19 | partial | FV03 | Numbered consistent contents and actual destination links delivered; layout reports remain. |
| N20 | reproduce | FV03 |  |
| N21 | delivered | Delivered | The active navigation group remains marked when closed. |
| N22 | open | FV02 |  |
| N23 | Owner deferred unavailable rules | FV02, FV16 | Technical workflows retained. |
| N24 | delivered | Delivered | Bronze/teal affect semantic surfaces and ordinary counters. |
| N25 | delivered | Delivered | Class facts use responsive readable definition lists. |
| N26 | open | FV01 |  |

### Earlier feedback and quality findings

| Source item | Current status | Remaining packet | Note |
| --- | --- | --- | --- |
| 2026-11-13:N07 | open | FV14 | Campaign-specific published homebrew allowlist. |
| 2026-11-13:S15/B10 | open | FV15 | Authorized campaign-quota extension request. |
| 2026-11-13:N11 | closed by owner scope decision | FV17 | Unidentified report disregarded on 24 November. |
| B11 | open | FV18 | Combined acceptance for the new full version; previously accepted playtable behavior stays accepted. |
| review-web-existing-custom-asset-editing | open | FV10 |  |
| review-web-English-Oglan-and-additional-system-content | Owner deferred unavailable rules | FV16 | No fabricated translation/content rights. |
| review-web-clipped-tree | asset id needed | FV11 |  |
| feedback-harness-menu-Escape | delivered | Delivered | FV06 menu propagation subcase verified at 207c8e9fc; other FV06 work remains. |
| feedback-harness-character-archive-width | reproduce | FV03 |  |
| inherited-test-and-hardware-gaps | verification needed | FV18 |  |

## Relationship to the earlier plans

| Previous slice | Full version packet |
| --- | --- |
| S2 | FV04, FV05 |
| S3 | FV07 |
| S4 | FV03, FV04 |
| S5 | FV06 |
| S6 | FV08 |
| S7 | FV09 |
| S8 | FV10, FV16 |
| S9 | FV11 |
| S10 | FV05 |
| S11 | FV06, FV09, FV12 |
| T3 | FV01 |
| T4_remaining | FV02, FV16 |
| T5 | FV13 |

The full-version goal adopts the remaining scope. Proposed shortcut bindings, geometry fields, tileset formats, persistence choices and world-sharing rules still need their packet Apply. E26 is partially complete: the filter defect is delivered, while full catalog classification and suitability remain in FV11. The unidentified zero-percent control retains its owner deferral until it can be identified.

## Release completion criteria

- Complete packet Apply with contracts, permissions, exact base/file ownership, limits, acceptance and rollout before implementation.
- Keep source/image/backups/schema/rollback and normal live UI journeys per functional slice.
- Preserve all delivered map, role, camera, scene, window, calendar, chat, companion and floor behavior.
- Do not silently defer a packet, claim an unavailable input implemented, restore superseded G1, or change a real user quota for testing.
- Keep Claude collaboration within the existing subscription and explicit file ownership; no extra usage/provider fallback; Codex owns integration, verification and delivery.
- Full version closes only after retained required packets and the final acceptance checklist are complete; blocking inputs need an explicit owner resolution or scope decision.

## Risks and assumptions

- Medium: Map formats and private assets. FV05/FV09/FV10 define backwards compatibility, server validation, budgets, Undo and all storage/export consumers before implementation.
- Medium: Locale and authorization contracts. FV01 preserves canonical rule IDs; FV13/FV14 separately enforce campaign/world/seat permissions.
- Medium: Open product and content inputs. FV16/FV17 and the relevant packet decisions remain visible; private tooling and independent fixes can progress.
- Medium: Inherited verification failures. FV18 separates obsolete assertions, test timing and confirmed runtime issues; no blanket green-suite claim.

The following previously excluded directions are not introduced by this consolidation: Superseded G1 restoration, 3D/Godot editor, Animation, Universal autotiling without transition metadata, A complete new DSA rules engine, A new billing system or automatic quota increases. Genuine content/source questions remain in FV16; they do not promise new system mechanics. Historical acceptance of the previous playtable remains valid; FV18 covers the changed full version.

## Planning artifacts and handoff

This plan and its [machine-readable register](VTT_NEXT_FULL_VERSION_2026-11-23.json) are permanent repository artifacts. They are the active scope register for the next full version; earlier Discover, Apply and delivery reports retain their evidence and constraints. Packet statuses must be updated with actual verification and delivery references, not inferred from an implementation branch or a present button.

Implement FV01 with reviewed canonical-ID display mappings and module-scoped locale; preserve live FV04. Complete the remaining FV05/FV06 contracts and all other retained packets. Await explicit policy/source/control inputs only for dependent work.

Sources:

- [DADM_MONITOR_FEEDBACK_HARNESS_2026-11-23.md](../DADM_MONITOR_FEEDBACK_HARNESS_2026-11-23.md)
- [DADM_DISCOVER_MAPMAKER_REVIEW_2026-11-23.md](../DADM_DISCOVER_MAPMAKER_REVIEW_2026-11-23.md)
- [DADM_DISCOVER_EDITOR_CREATOR_FEEDBACK_2026-11-23.md](../DADM_DISCOVER_EDITOR_CREATOR_FEEDBACK_2026-11-23.md)
- [DADM_APPLY_CLAUDE_MAPMAKER_2026-11-23.md](../DADM_APPLY_CLAUDE_MAPMAKER_2026-11-23.md)
- [DADM_MONITOR_REVIEW_WEB_2026-11-22.md](../DADM_MONITOR_REVIEW_WEB_2026-11-22.md)
- [DADM_MONITOR_TOOL_GROUPS_2026-11-23.md](../DADM_MONITOR_TOOL_GROUPS_2026-11-23.md)
- [DADM_MONITOR_CANVAS_SCENES_2026-11-23.md](../DADM_MONITOR_CANVAS_SCENES_2026-11-23.md)
- [DADM_DEPLOY_MONITOR_SESSION_FEEDBACK_2026-11-16.md](../DADM_DEPLOY_MONITOR_SESSION_FEEDBACK_2026-11-16.md)
- [FEEDBACK_IMPLEMENTATION_2026-11-13.md](../plans/FEEDBACK_IMPLEMENTATION_2026-11-13.md)
- [FEEDBACK_REMAINING_SCOPE_2026-11-13.md](../decisions/FEEDBACK_REMAINING_SCOPE_2026-11-13.md)
