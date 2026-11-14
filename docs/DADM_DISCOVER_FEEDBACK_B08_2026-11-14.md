# B08 library, Journal and campaign maps

Status: Discover complete; retention permanent. Input: S05, S12, S20 and the
owner's instruction to finish the feedback program. B07 remains a separate release.

Inventory: `play-map-library.js` provides DM-only private-project selection,
exact PNG preview, explicit sharing consent and idempotent table-page import.
Its rows contain only titles/dimensions. Mapmaker `library.js` has the same
text-only overview. `snapshot.js` already validates/materializes documents and
renders reviewed assets/fonts with full PNG credits. Document limits are 4096
pixels per side and 32 million aggregate raster pixels.

The campaign hub has ordinary asset upload plus campaign-map creation and map
management, but no private-library import entry. Those existing two operations
are separate, unlike the atomic table import. Journal currently contains activity,
map notes and DM session controls, with no asset list/intake. Existing asset APIs
support membership-filtered listing/media, DM upload, soft delete and handout
reveal. The atomic campaign upload path enforces quota; the older session-upload
path uses a weaker read/modify/write quota update. Asset filenames double as
display labels; no metadata editing endpoint exists.

Permissions: `can_edit_campaign` lowers owner authority when a valid Player
context is carried. HTTP context middleware validates provided capabilities and
campaign path parameters. The asset membership helper does not currently reject
a mismatched carried context for asset-ID-only read URLs. New Journal media
requests must carry context headers, including thumbnails/downloads; cookie-only
image/link requests can lose the active Player boundary for an owner.

Additional medium read finding: the legacy asset version-history route uses
membership alone and can reveal hidden handout metadata. Apply the same resource/
handout visibility check to the requested asset and each returned version.

Medium risks: private handout disclosure through unscoped media fetches; source
project disclosure through sharing; concurrent full-size thumbnail memory;
upload retry duplicates/unknown outcomes; weaker legacy session upload quota.
Control them explicitly in Apply. No new third-party service or dependency is
needed. Player presentation must never initialize the DM asset-management code.

No owner question blocks this slice. Next: Apply a shared bounded thumbnail
queue, direct campaign image import through existing contracts, and separately
composed Journal reading/DM management with scoped media requests.

Entry-point verification: normal `/campaigns?campaign_id=…` uses BookScene's
`buildCampaignHubDetailMarkup`, not the older unused template hub builder.
The actual map overview/import entry belongs in that BookScene hub; successful
import must return there. `workspace=1` remains the existing preparation path.
