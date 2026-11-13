# B06a compatibility rework — Atlas credits

Status: Apply complete; retention permanent. Input: approved B06 full raster
source collection, B06a export proof and cross-entry inspection during B06b.

Discover evidence: `atlas_domain.bundle` and `atlas.validated_publication` bound
credit text to 20,000 characters. Reviewed catalog `exportCredit` texts alone
contain 93,750 UTF-8 bytes. The existing Atlas editor submits the complete
collection on save, and its publication validator reads the same field.
Medium finding: the full source collection can reject an otherwise valid map.

Target contract: share an explicit `MAX_CREDITS = 200000` character bound between
Atlas bundle writes and publication reads. Retain the 16 MiB map/bundle, 64 MiB
backup, quota, owner, lease, revision and publication visibility rules. This is
a bounded text-field compatibility correction, with no schema or access change.
No license text is truncated. Old short text remains valid.

Acceptance: actual reviewed catalog text passes bundle validation and PNG
metadata roundtrip; excessive text is rejected; Atlas map edit/lease and backup
roundtrips remain valid. Verify a real authenticated Atlas UI save and return.

Deploy handoff: isolate this correction from the still uncommitted B06b brush
work, commit/push, overlay the actual B06a image using the existing guarded
release tool, and retain the B06a rollback image. Record live proof and cleanup.
This corrected compatibility image becomes B06b's rollback reference.
