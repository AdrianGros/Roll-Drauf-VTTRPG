# Monitor: playable Duckfolk Species rollout

Date: 2026-10-27. Phase: Monitor. Input: [Deploy record](DADM_DEPLOY_DUCK_SPECIES_2026-10-27.md).

## Observed results and evidence

- The live app container is running `roll-drauf-vtt-app:duck-species-20261027-v2` with
  `CE_PLAYABLE_SPECIES=true`. Its app configuration reports the flag true and the
  `ce_species_revisions` table exists. The health endpoint at
  `https://vtt.roll-drauf.de/api/admin/assets/health` returned HTTP 200 with `healthy`;
  the Duckfolk starter asset returned HTTP 200; an unauthenticated Species catalog
  request returned HTTP 401.
- The exact derived container image passed a test-app schema/asset/route smoke check.
  The disposable Chromium journey passed on SQLite and on PostgreSQL. It covered the
  GM starter, check and publish; player catalog, skill choice, finalize and sheet;
  live action declaration; and the GM party card. The focused Species suite passed
  30 tests and the existing Eagle/SRD regression suite passed 180 server cases plus
  the 10 browser sheet cases once browser shared libraries were supplied.
- The prior live navigation layer was retained in the two merged templates. The
  original Compose JSON remains available for image rollback. No live campaign
  Species publication or test character was created.

## Inconveniences found during the journey

- The GM had no fast way to start a valid Duckfolk document. Added a normal editable
  Duckfolk starter button that preloads the typed supplement, then requires review
  and publication.
- Changing only the publication campaign disabled an already successful check.
  Scope selection now leaves that check valid.
- Reopening a supplement replaced its action and choice identifiers. The companion
  now keeps the saved identifiers, avoiding needless changes to player choices.
- The full telekinesis rule made the narrow DM party card hard to scan. It now shows
  the name and limits, with the complete rule expandable.
- A retry could reuse an idempotency key for a different object declaration and
  receive the old receipt. It now returns HTTP 409.
- The host initially lacked the Playwright browser and its shared libraries, and
  has no `node` binary on PATH. Chromium was installed into the test environment,
  its existing library bundle was supplied, and the browser suites passed. The
  release image and app runtime do not require host Node.
- The SQL migration was hidden by the repository's `*.sql` ignore rule; it must be
  force-added to source control. It was checked against a disposable PostgreSQL
  schema before live rollout.

## Residual risks and next bounded action

- No particular live campaign was named, so the starter is available but no
  Duckfolk has been published to live players. The intended campaign's GM should
  create the example, review the playability report, and publish it there.
- Telekinesis is the provisional non-combat object-moving rule. It is a logged,
  DM-adjudicated table action; it does not simulate object movement on the map.
- Other Foundry mechanics (ItemGrant, Trait advancement, Active Effects, spells,
  resistances and rest resources) block publication with diagnostics. They require
  separate adapters and rules tests before broader Species are playable.
- The catalog has no withdraw/retire workflow. Existing characters retain an
  immutable pin even if their source document changes or is deleted.
- A separate live user-account journey was not run because that would create
  content in an unspecified campaign. The disposable browser and live smoke checks
  cover the implementation without changing user content.
