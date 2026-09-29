# D&D homebrew race to character sheet — 28 September 2026

Status: bounded implementation complete; automated journey verification recorded below.
Production activation remains a separate release step.

The user explicitly requested visible Creation Engine entry points in every VTT
navigation view, D&D 5e homebrew races with features and traits, and application to
an imported character or creation of a new character from the authored race.
The current target for end-to-end testing is **Wednesday, 30 September 2026**
(Europe/Berlin), superseding the earlier Tuesday scheduling note. No participant
attendance, human acceptance or production activation is inferred.

## Discovery

The deployed G1 code supplies versioned private drafts, immutable revisions,
three editing modes and an RDL flame-item sandbox. It does not supply a D&D race
profile. The existing importer accepts only Roll Drauf Light, and the character
creator assumes its species/faction catalogue. Book navigation misses the editor;
the existing dashboard shortcut is hidden while live authoring is disabled.

## Bounded design and implementation handoff

- Add a separate versioned D&D race authoring registry using existing A1 draft
  commands; preserve the active 1.1.4/core 1.1.3/A1 contract and existing pins.
- Require an explicit 2014/2024 edition, creature type, size, speed in feet,
  language rules and one or more named features/traits. Each feature has rules
  and usage text, with optional choices and prerequisites. Never infer executable
  mechanics from prose. Complete races qualify as Sheet-ready.
- Provide a reviewed, owner-only handoff from an immutable race revision to an
  existing compatible D&D character or a new character with explicit core values.
  Store the revision association separately from legacy character_data. The
  public sheet exposes only intended race content, never private draft history.
- Applying a race replaces the prior race association. It preserves all existing
  stats, class/background features, equipment and import data. It does not add
  bonuses to imported totals, which may already contain racial contributions.
  New authored revisions do not silently change existing sheets.
- Separate the sheet adapter's versioned HTTP contract and idempotent application
  receipts from the frozen engine command vocabulary. Preserve account, CSRF,
  ownership, View As and ENGINE-scope write guards. Reject incompatible RDL and
  edition-mismatched targets explicitly.
- Add visible, contextual editor navigation across the book and table. Disabled
  authoring remains honestly unavailable until the host is activated with its
  migrations. Keep unsaved-input and session-leave guards.

The requested external import source is still being clarified. The bounded implementation adds the [VTT portable D&D JSON format](dnd5e-import-format.md) alongside RDL import/export. Direct D&D Beyond and Roll20 compatibility is not assumed.

## Risks and acceptance

Medium: this is a user-authorized scope extension beyond the G1 item slice, not
complete D&D runtime rules or a G1 exit. Trait choices and mechanical consequences
remain explicit manual instructions on the sheet. Medium: source ownership and
sheet audience differ; the review must explain that applied race content is shown
to people allowed to view the character. Medium: duplicate/lost requests need
durable receipts and stale-target detection. These are implementation requirements.

Verify real authoring/save/reload, multiple traits, existing/new character paths,
idempotency, replacement without stacking, source-revision stability, privacy,
incompatible-target rejection, navigation and the retained flame workflow. Use a
disposable database; record executed results below. Production deployment and
activation require a concrete tested release, not merely an editor link.


## Wednesday journey checklist

1. Enter the Creation Engine from dashboard, campaigns, campaign hub, characters,
   character sheet and desktop/mobile table menu. Confirm unavailable-state copy
   when authoring is disabled and proper return to the originating sheet.
2. Create a D&D race, choose 2014 or 2024, enter all required fields and add at least
   two distinctly named traits/features with explicit usage. Save, reload and switch
   Guided/Structured/Advanced modes. Confirm missing/duplicate rules block Sheet-ready.
3. Save a Sheet-ready revision, choose a new character, explicitly enter core values,
   review the shared content and open the resulting sheet. Verify all traits survive
   reload and a later draft edit does not alter the pinned sheet.
4. Export a D&D character in the supported portable format and import a copy through
   Characters → Import. Apply a saved race to that imported character; compare stats,
   equipment, class/background content and manual trait rules before and after.
5. Retry a lost application response; verify exactly one character/result. Replace
   a race revision after review; verify no duplicated traits or stacked bonuses.
6. Try another owner's references, mismatched editions, RDL/ENGINE targets and stale
   character edits. Confirm rejection without partial changes.

Rules-field design follows the explicit edition distinction and species/race fields
in the official [2024 character rules](https://www.dndbeyond.com/sources/dnd/br-2024/creating-a-character)
and [2014 SRD](https://media.dndbeyond.com/compendium-images/srd/5.1/SRD-OGL_V5.1.pdf).
No official race text or mechanical preset is copied into the profile.


## Executed verification and delivery

- Pure engine regression: `tests/creation_engine -m 'not postgres'` — **482 passed**.
- PostgreSQL authoring, transports, design, editor/access states, manual profiles and
  race handoff regression — **97 passed, 1 skipped**. The skip is the opt-in WebKit
  case; this host does not establish WebKit coverage.
- Real Chromium desktop/mobile race journeys — **9 passed**. These cover creation,
  traits, save/reload, new/existing character application, exact request retries,
  unsaved-change guards, successful application with a failed follow-up read,
  explicit revision replacement, actual export/download/import and navigation hit
  targets at 1280 and 390 pixels.
- Portable D&D import/export — **28 passed** on the initial final-source run,
  including resource/metadata preservation, public race content with new private
  provenance, atomic rollback and invalid input. Any export-policy follow-up is
  recorded with the final release evidence.
- Existing RDL import/export and sheet compatibility — **68 passed**. Existing
  compiler registry pins are unchanged. These suites overlap earlier targeted runs;
  the counts are not an aggregate distinct-test claim.

The implementation adds the D&D compiler profile, the separate `race-sheet:1`
adapter and M79 association/receipt tables, portable D&D import/export, readable
sheet traits, and shared engine navigation. M73–M79 are required before activating
this host. Authoring and the legacy adapter can be enabled together while runtime
and shadow remain off; this is not live campaign cutover or automatic D&D effects.
Pinned sheet rules remain readable and exportable if authoring is later disabled.

Task evidence is retained under
`/home/admin/deliverables/2026-09-28_creation_engine_race/`: six responsive browser
screenshots, a schema-validated import fixture, a Wednesday test guide and
`release/` with the exact source manifest, candidate image identity, isolated
PostgreSQL/Redis startup checks and their executed results. Live services have not
been changed by the implementation or these disposable tests. No human-study,
Wednesday attendance or G1 acceptance result is claimed.

Acceptance: authored race and named traits, save/reopen, public sheet projection,
new/existing/imported handoff, repeat/replacement safety, ownership and edition
checks, and visible navigation have automated evidence. Remaining limits are
manual mechanical resolution, the documented VTT import format, untested WebKit,
and the scheduled human journeys. The next release action is to activate the
concrete tested candidate under the existing production release boundary.
