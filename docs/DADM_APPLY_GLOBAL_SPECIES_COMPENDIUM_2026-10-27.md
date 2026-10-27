# Apply — VTT-wide playable Species compendium

## Design summary
Add a global target to the existing immutable Species publication workflow. Any authenticated active contributor who can read an Eagle Species from their personal workshop, Library, or a campaign world they lead can publish a validated 2024 Species for all VTT users. The public catalog exposes only the converted profile and provenance, never an unpublished Eagle document.

## Solution boundary and contracts
- The target string `global` maps to `scope_kind=global, scope_id=0`; it is a **publication target**, not an editable Eagle world. Authoring worlds and private Library access stay as-is.
- A global lineage includes the publisher ID and source identity. Re-publishing the same source by the same author creates the next immutable revision; unchanged retry is idempotent. Contributor listings include only their own global rows.
- `species_catalog.catalog` includes the latest global revision of each lineage for every active authenticated user. `can_select` accepts global rows for those users; finalization pins the exact revision. Personal/campaign restrictions stay unchanged.
- The Creation Engine companion offers the global target distinctly, describes its audience, and keeps the target selected through check/publish. The character creator shows the global origin. An authenticated global Species listing provides a clear discovery surface with name, author, revision, and profile summary.
- Existing feature flags guard the functionality. Do not expose full Eagle source through public APIs. No new schema or dependency.

## Acceptance criteria
1. A normal player can create Duckfolk in a personal workshop and publish it globally; an unrelated authenticated user can see, select, finalize, and play it in another campaign.
2. Unpublished, personal, and campaign-only Species remain inaccessible to outsiders, including direct revision-ID attempts.
3. One contributor cannot publish another's private source or access another's personal publication history. Authors with the same campaign source get independent global lineages.
4. Changed source/supplement requires the existing check; unchanged retry creates no extra revision. Character pins remain stable after later publication.
5. Chromium author-to-unrelated-player journey and focused API regressions pass.

## Risks and tradeoffs
This is the first VTT-wide compendium category. Eagle spells, items, classes, and other documents still need explicit use/adaptation contracts. The UI must name this as a playable Species category, not imply all Eagle types already work in live play.

## Deploy handoff
Implement the global target in Species publication, catalog access, and companion UI, then run focused tests and browser journey. Roll out behind the existing flags after review, preserving the current live navigation overlays.
