# B08 visual libraries and authorized Journal intake

Status: Apply complete; retention permanent. Input: B08 Discover, S05/S12/S20.

Visual selection: display a small image with a short title below each project in
the table's Own Library, campaign-hub import and editor library. Reuse validated
Mapmaker snapshots with reviewed assets/fonts/credits; no editor or draw handlers
are initialized for previews. Observe visible rows and serialize project loading
and rendering through one queue. Bound thumbnail output to 256 pixels, release
temporary raster/renderer canvases, cancel obsolete rows, cache only small results
for the current account/project revision. A failed preview retains its title and
ordinary open/select action with a clear placeholder. No thumbnail storage/schema.

Campaign hub: add a DM-only Own Library entry beside normal map upload/manage.
Reuse the selection/preview/explicit consent dialog, with campaign wording and
an immutable selected revision. Import only its PNG (full embedded credits), title,
dimensions, grid and readable source summary. Use the existing authorized asset
upload then campaign-map creation; do not create a table context or session as a
side effect. Retain the uploaded asset ID for a failed map-stage retry; reconcile
an uncertain map response against maps referencing that asset before retrying.
An uncertain upload is visibly incomplete and cannot silently issue another upload.
Private source JSON is never copied to campaign storage or sent to members.
Existing atomic/idempotent table import remains unchanged.

Journal: a common read-only controller lists campaign/current-session files with
search/type/scope and pagination. Read image thumbnails/previews and downloads
through authenticated fetch with the actual table context; use data images or
download blobs locally, never privileged cookie-only media links. Preserve private
handout filtering. A separate DM-only module mounts/binds upload, rename, reveal/
hide and soft-delete controls; Player surface never loads that module. A visible
Tokens action opens the existing independently authorized token panel for token
placement/art/actions, preserving own-token permission checks. Edit means file
label/handout visibility and the existing token controls; this slice adds no file
content authoring engine.

Server contracts: extend the existing atomic campaign upload with optional
`session_id`, checked against campaign/current carried DM session; enforce the
existing 100-file session bound and normal atomic quota reservation. Journal uses
this path, avoiding the weaker legacy session-upload implementation. Default
uploads remain campaign-scoped. Add DM-only PATCH asset metadata accepting only
a validated filename label (bounded, no path/control characters), leaving storage
keys/MIME/content/ownership unchanged. All asset library read paths reject a
carried context for a different campaign. Existing Player-context lowering also
applies to upload/rename/reveal/delete. No new schema, quotas or entitlement.

Acceptance: actual image cards in all three entry points; selection/search/page
races do not install obsolete thumbnails; source project stays private. DM hub
import reaches a reusable campaign map and management entry without entering a
table. Journal DM uploads a current-session private handout, renames/reveals/hides
and deletes it; Player sees only revealed files and can preview/download with
their own context. Owner-in-Player mode cannot manage/read hidden handouts; foreign
campaign/session contexts fail. Tokens remain reachable through established UI.

Version-history reads also enforce the asset-library resource/handout boundary
for the requested asset and each returned version; no hidden metadata exception.
Journal listing uses `scope=current` plus the actual session ID for campaign
assets and that session's files in one paginated query. A carried table context
restricts list/media/version and asset-management resources to its campaign and
current session (campaign-wide assets remain valid). Requests cannot select a
different session by changing a filter or asset ID. The ordinary hub without a
table context retains its authorized campaign management scope.
Desktop/mobile and English/night controls fit; browser/domain tests and live role
journeys establish this, with own fixture cleanup.

Deploy handoff: focused tests, commit/push, reconcile actual running source/image,
guarded app-only deployment, normal UI live checks, source/image/rollback proof
and register update. Medium risks above are controlled by the specified boundaries;
no unresolved product choice is delegated to implementation.
