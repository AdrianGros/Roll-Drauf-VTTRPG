# Apply addendum: playable Duckfolk milestone

Date: 2026-10-27. Supersedes only the broad first-fixture examples in
[the Species integration design](DADM_APPLY_EAGLE_PLAYABLE_SPECIES_2026-10-26.md).
The user's request authorizes Deploy for this bounded milestone. The goal is a
real end-to-end Species, not general Foundry feature parity.

## Rule fixture and acceptance boundary

The 2024 **Duckfolk** is a Small Humanoid with a 30 ft walking speed, a 30 ft
swimming speed, no darkvision, and a player choice of proficiency in Athletics
or Perception. Its **Telekinetic Quack** moves one unattended object weighing at
most 10 lb within 30 ft, up to 30 ft, as an action. It cannot attack, deal
damage, move a creature, or manipulate worn/carried items. The VTT records the
declared use and object/target description for the DM to adjudicate at the
table; it does not pretend to simulate map-object physics. This rule is the
provisional interpretation pending the user's answer about combat push/pull.

This first race can be fully played with the VTT's current table model:
creation choices and roll bonuses are server-derived; movement, senses and
traits display on sheet, token and DM views; the telekinesis action is launched
from the sheet/play context and becomes an auditable, visible table event. The
GM decides whether the described object is eligible. At-will use has no charge
or rest counter. No other Foundry advancements may be labelled playable unless
their conversion is implemented and tested.

## Interfaces and safety

- Eagle remains the authoring source. The Duckfolk fixture must be expressible
  as an Eagle Species document plus a VTT-owned typed action/skill-choice
  supplement. A GM can author another Species using the same supported fields;
  Duckfolk is an example, not a hard-coded species ID in the evaluator.
- The authoring page offers the Duckfolk example as a reviewed starting document
  and supplement. It creates a normal Eagle document in the selected world;
  the author still checks and publishes it, and may edit it like any other
  Species. The example is data, not a special rule path.
- Publication creates an immutable versioned profile with source digest and
  provenance. The player-facing list includes only authorized personal or
  campaign publications. A character pins a profile version at finalization.
- The SRD creator validates the choice and computes the proficiency. Sheet
  rolls, level-up, party/DM view and token-linked representation use the same
  pinned profile. Existing SRD-only characters keep their path.
- Telekinesis uses a server-authorized action command; owner or campaign DM
  may invoke it for the character. If tied to a live session, it writes one
  audit event visible through the existing table chat/activity surface. An
  idempotency key prevents duplicate use messages on retry. The command
  validates object description length and declared range/weight boundaries.
- The API rejects unsupported advancements/references and 2014 publication
  with actionable diagnostics. No private Library item becomes available to
  players merely because it exists.
- No new runtime dependency. New schema is additive and feature-gated.

## Acceptance checklist

1. Start from the Duckfolk example or author it in Eagle; run playability check
   and publish it to a campaign.
2. A campaign player sees it, selects Athletics or Perception, finishes a
   character, reloads the draft/sheet, and receives the chosen skill bonus
   without duplicate grants.
3. The sheet and DM party/table views show Duckfolk, walk/swim speed, absence of
   darkvision and the telekinesis rule. A linked token uses its existing
   character stats.
4. Owner or DM declares telekinesis in a live session; the session event is
   visible, attributable and appears once on retry. Unauthorized users cannot
   invoke it or read unpublished profiles.
5. Level-up, duplicate/rebuild and export either preserve the immutable origin
   and correct mechanics or refuse with a clear error before writing. Editing
   the Eagle document after publication does not change the existing character.
6. Chromium exercises the journey on a disposable account/database; targeted
   tests cover server validation, permissions, pinned revision stability and
   action idempotency. The original Eagle/SRD baseline remains green.

## Deploy handoff

Implement the reusable 2024 Species profile, publishing/selection and shared
evaluation first, then the duck action and hub surfaces. Keep broad features
from the earlier Apply design (arbitrary spells, resistances, resources,
generic Foundry effect execution) outside this milestone unless needed to make
the Duckfolk rules work. Unsupported features must block publication rather
than silently degrade. This preserves a clean path for later Species kinds.
