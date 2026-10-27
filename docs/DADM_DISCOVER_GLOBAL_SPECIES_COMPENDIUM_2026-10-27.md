# Discover — VTT-wide playable Species compendium

## Input
The user chose a VTT-wide compendium instead of publishing Duckfolk to one campaign. Everyone on the VTT should be able to create and publish content for everyone to use.

## Current state and inventory
- Eagle authoring is available to authenticated active users in a personal workshop and private Library. Campaign-world writes require DM/Co-DM rights (`vtt/creation_engine/routes.py`).
- Playable Species publications are immutable `CeSpeciesRevision` rows. The table and migration already support a 16-character `scope_kind` and integer `scope_id`; current code accepts only personal/campaign publication targets (`vtt/creation_engine/species_routes.py`).
- `vtt/characters/species_catalog.py` exposes personal and joined-campaign rows and re-checks access on draft, evaluation, finalization, import, and rebuild. Finalized characters pin a copy of the profile.
- The companion UI target selector comes from authoring worlds, which should remain private/campaign only. The player creator consumes the Species catalog.
- Current Duckfolk coverage includes API, browser author-to-player, character-sheet, live action, and DM party tests. No global read/write tests exist.

## Dependencies and constraints
Existing CE_AUTHORING and CE_PLAYABLE_SPECIES gates, active-user auth, canonical source digest, Species conversion diagnostics, and immutable revision table. No schema migration is needed for a global Species scope. The SRD rule compendium is a separate read-only corpus; Eagle's other document types have no playable adapters.

## Risks and assumptions
- **Medium:** Public selection must never broaden reads of unpublished Eagle source or personal/campaign Species.
- **Medium:** Two authors can publish the same campaign source over time. Global revision lineage must include the publishing user so one person cannot advance another person's revision series.
- **Medium:** Public homebrew can be inaccurate or unwanted. Publication requires an explicit scope choice and the existing playability check; provenance and version remain visible.
- **Low:** Calling the entire Eagle catalog playable would overstate support. The first public category is playable 2024 Species; other Eagle types remain editable but need adapters before use in character rules.

## Open questions and next step
No blocking question: the user explicitly authorized VTT-wide publication by everyone. Apply will define the public scope, listing, ownership, and acceptance checks for this first category.
