# C09 structured self-review

Owner-authorized Codex takeover. No independent reviewer claimed. Reviewed all API routes, pure validators/archive logic, storage compensation/quota/lock order, reader-only composition, author form lifecycle and existing editor bridge.

- World ownership/grants independent of global/campaign DM/Admin; fresh usable actor/owner/member after user/world locks; every read checks again. Reader never receives draft graph/map bundle or mounts author/editor module.
- Reader fields/links/assets are separate whitelist + immutable publication bundle. Hidden ancestors/maps reject; hidden link targets removed. Search runs only on published projection. Explicit pixel consent required. Subsequent draft/raster writes cannot modify published bytes; revoke checked on asset/data reads and clears Reader UI.
- UUID references/world-scoped map checks, acyclic hierarchy/finite coordinates, source project ownership+revision and normalized document/PNG; no HTML rendering or external asset URLs.
- User rows locked ascending then world, same shared storage accounting lock as library/assets. PostgreSQL contention proves single winners and quota enforcement. All new keys scoped and compensated if transaction fails; old objects removed after commit only. Backup contains no grants/leases/internal keys.
- ZIP never extracted, exact single member, inflated bytes bounded and full JSON/graph/image revalidation. World/map/place identities retained. Restore publication UUID reuse finding resolved in explicit Apply addendum with regression; new version UUID always minted.
- Existing editor used directly with dedicated Atlas save path and 120s actor/tab lease, 45s visible renewal, map revision. Lost lease never falls back to personal save; local file recovery available. No private IDB draft initialization; pagehide clears private document/history/canvas/DOM; pageshow reauthorizes.
- Full reviewed attributions retained while personal document title header excluded from Reader credits/PNG metadata. 64KiB headroom reserved for backup wrapper inside64MiB cap.
- Low: storage object deletion failure can leave a scoped orphan; logged, no live URL or grant emitted. Existing adapter operational cleanup remains applicable. No public publishing, CRDT, 3D or unprovided assets introduced.

No unresolved medium-or-higher finding. Four additive tables only. Live source/image/backup/normal-navigation evidence required before completion.
