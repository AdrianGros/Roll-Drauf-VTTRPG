# Discover — official Roll Drauf publication owner

## Status and input summary
`complete`. The user requested a Roll Drauf Default account that owns publications made by the VTT team. The immediate pending publication is the Duckfolk starter in the global playable Species compendium.

## Current state and inventory
- Production has no global Species revisions and no Duckfolk Eagle document. The reviewed starter bundle is `vtt/static/examples/duckfolk-2024.json`; it contains the Eagle Species source and the typed VTT supplement.
- `users` requires a unique username, unique email, password hash, and role. `User.is_usable()` rejects inactive or deactivated accounts. The Creation Engine's normal HTTP authoring routes likewise reject accounts that are not active.
- `CeEagleDocument` records the source owner through personal scope and `created_by`/`updated_by`. `CeSpeciesRevision` records the publisher through `published_by`, and the global catalog displays that username as provenance. Global rows remain selectable even if their author account is inactive.
- The existing Species converter, document validator, canonical digest, immutable revision model, and public catalog already support a publication owned by a durable user ID. No schema change is required.

## Dependencies
The production app and database, existing Player role, the Duckfolk starter asset, Eagle document validation, Species conversion, and the global catalog. A server-side publication operation can use these existing components without issuing a login session.

## Risks and assumptions
- **Medium, security:** A shared human-login account would create unclear access and ownership. The official owner should remain non-login while retaining a durable user row for attribution.
- **Medium, integrity:** A direct publication operation must apply the same source validation, playability check, digest, and revision lineage as the HTTP path. A failed check must leave no partial account/source/publication writes.
- **Low, attribution:** “Roll Drauf Default” should be the visible author name; no existing user has that name in production.

## Open questions and next step
No blocking question remains: the user explicitly chose a dedicated Roll Drauf account. Apply will define its non-login state, a repeatable server-side publication contract, and checks for first publication and future revisions.

## Artifacts
This discovery note is retained in the repository; the live DB inventory was read-only.
