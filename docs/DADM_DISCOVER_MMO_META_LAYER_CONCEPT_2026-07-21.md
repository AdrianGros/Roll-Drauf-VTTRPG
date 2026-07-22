# DAD-M Discover: MMO Meta-Layer Concept (Session-as-Progression)

Date: 2026-07-21
Phase: DISCOVER
Scope: Turn roll-drauf-vtt into a persistent MMORPG where DM-run live sessions are the core progression mechanic, by combining three product metaphors (VTT, Civ/CK-style strategy layer for DMs, classic MMO for players) into one cooperative system instead of three silos.
Status: complete (all structural open questions resolved — Kingdom-and-below design, Gilden-faction layer, Encounters, and World Encounter Score are all confirmed; six items remain explicitly deferred by product-owner choice, not blockers; ready to move to APPLY)

## Objective

Research relevant competitor mechanics (Roll20, Inkarnate, Civilization, Crusader Kings, classic themepark MMOs) and inventory the current `roll-drauf-vtt` data model, in order to define a safe design boundary for a session-driven MMO meta-layer — no code changes in this phase.

Explicit scope correction: this concept targets `roll-drauf-vtt` (this repo) only. It does **not** extend the separate `rolldrauf_bot` Discord bot, and has **no Discord involvement** anywhere in the design.

## Current-State Inventory — roll-drauf-vtt

Flask + SQLAlchemy app, models under `vtt/models/`. Relevant existing entities:

- `Character` ([character.py](/home/admin/projects/roll-drauf-vtt/vtt/models/character.py)) — full D&D 5e sheet, already has `level`/`xp` per character.
- `Campaign` ([campaign.py](/home/admin/projects/roll-drauf-vtt/vtt/models/campaign.py)) — `owner_id` aliased as `dm_id`, one DM-owner per campaign, `max_players`.
- `GameSession` ([game_session.py](/home/admin/projects/roll-drauf-vtt/vtt/models/game_session.py)) — full state machine (preparing/active/paused/ended) and **already has `xp_earned` and `treasure_log` (JSON) at the session level** — the natural hook for awarding DM-side progression later.
- `TokenState` ([token_state.py](/home/admin/projects/roll-drauf-vtt/vtt/models/token_state.py)) — `token_type ∈ {player, npc, monster, object}`, `character_id` nullable. This is the existing "proxy" pattern: lightweight stand-ins for anything that isn't a full player character.
- `SessionInitiative` ([session_initiative.py](/home/admin/projects/roll-drauf-vtt/vtt/models/session_initiative.py)) — same proxy pattern duplicated at the combat layer (`character_name` fallback for NPCs).
- `Role` ([role.py](/home/admin/projects/roll-drauf-vtt/vtt/models/role.py)) — simple global RBAC (Player/DM/Admin), no per-campaign nuance beyond `CampaignMember`.
- `guild.py` ([guild.py](/home/admin/projects/roll-drauf-vtt/vtt/models/guild.py)) — NOT Discord. Four fixed, hardcoded narrative "Gilden" (Sternenwacht, Bernsteinkreis, Nebellaterne, Eichenbund) used for Book-UI theming. Currently cosmetic only, no gameplay effect — candidate substrate for the faction/alliance concept below.
- `CampaignMap` / `SceneStack` / `SceneLayer` / `SessionMapLayer` / `Asset` — layered map system with fog-of-war data and versioned assets (S3/local). Solid Roll20-equivalent foundation; no terrain-brush authoring or asset marketplace yet.
- `CombatEncounter` — session-scoped turn/round state.

Nothing currently exists for: DM-level progression, DM points, a resource ledger (wood/stone/tools equivalent), territory/claims, vassalage, or any cross-campaign persistent world state. This is greenfield.

## Findings from Competitor Research

### F-01: Roll20 (VTT layer)

Evidence: Dynamic Lighting / Fog of War (line-of-sight based, two generations — legacy and "Updated Dynamic Lighting"), a Compendium (rules reference), a Marketplace for pre-built maps/modules, LFG/player-finding, and Mod/API-driven automation of dice and lighting.

Implication: this is the layer `roll-drauf-vtt` already covers reasonably well (`TokenState`, `SessionMapLayer.fog_of_war_data`, `CombatEncounter`). No new concept needed here beyond continuing to build out what exists.

### F-02: Inkarnate (map editor)

Evidence: December 2025 "2.0 Update" introduced reworked custom layering, a Brush Tool 2.0 for terrain painting, and a new community Marketplace where artists sell asset packs/map templates; separate workflows for world maps, regional maps, and battlemaps; up to 16K export at the top tier.

Implication: this is a real gap versus the current `CampaignMap`/`SceneLayer` system, which supports layer stacking and fog data but not terrain-brush painting or an asset marketplace. If a real Inkarnate-level editor is wanted, it should be scoped as its own workstream rather than bundled into the MMO-progression effort.

### F-03: Civilization (nation/city-builder layer)

Evidence (general knowledge, stable/long-documented mechanics): tech tree, per-city production queues, diplomacy (treaties/alliances/war declarations), multiple victory conditions (domination/science/culture/diplomatic), neutral city-states, trade routes.

Implication: good template for the pure resource/building side of DM territory growth (wood/stone/tools → buildings, tech-like unlocks for new dungeon/quest templates). Treats territory as a container, not a character relationship — see F-04 for the contrast.

### F-04: Crusader Kings (character-driven diplomacy layer)

Evidence (general knowledge): CK is played through a dynasty/character, not an abstract nation; core systems are claims (fabricate/press a claim as casus belli), liege/vassal hierarchy, de jure vs. de facto territory, marriage/intrigue, council, and war-score-based peace deals.

Implication: correction to an earlier working assumption — the "spend points to lay a claim on a province, opposing side accepts or war follows" pattern discussed for this project is a CK3/EU4-style claims mechanic, not a Hearts of Iron one (HOI4 has no claims system, only production and front lines). Because the DM avatar is itself the central playable unit here (not an abstract nation), CK3 is the closer structural fit for the diplomacy/territory layer than Civilization.

### F-05: Classic themepark MMO (WoW-style, player layer)

Evidence (general knowledge): zones/instances, quests, group dungeons/raids with loot tables, gathering/crafting professions, a group finder, guilds, reputation systems tied to factions, recurring daily/weekly quests.

Implication: template for the "MMO content without a live session" requirement already discussed (DM-less dungeons per province, upgraded by the province's DM, generating resources back to that DM when played).

### F-06: Evil Bank Manager (specialist-hire management layer)

Evidence: the bank is organized into four departments (loans, diplomacy, investments, guards), with hires capped at one per department scaling up with HQ level (max 9 per department); each hired employee has stat spreads (Investment, Lending, Diplomacy, Guard) that directly drive that department's output; candidates are found through a paid, randomized search across three experience tiers (novice/experienced/expert), and both candidate availability and stat quality scale up as the game progresses.

Implication: clean template for a second, orthogonal DM growth axis that does not require subordinating to anyone — a DM spends DM points to search for and hire specialist NPCs who autonomously run parts of the province, with a hire cap that scales with the DM's own level, independent of vassal/liege status.

### F-07: Hearts of Iron 4 (advisor-slot reference for the "5th+ specialist slot" question)

Evidence: HOI4 gives each country a fixed set of always-available advisor slots (political advisor, foreign minister, economy minister, security minister, army/navy/air chiefs, chief of staff, high command); an empty or filled slot is appointed/changed by picking from a pool of mostly-generic candidates (some unique ones unlockable via national focus trees), at a flat political-power cost per hire or swap (150 PP). Slots themselves are static per category, not something that rotates which category is active — that part is not a literal HOI4 mechanic.

Implication: validates the general shape the product owner wants — fixed slots, flat cost, pick from a pool — as a genuinely simple, well-proven pattern worth copying for the specialist system. The specific "extra slots rotate which domain they boost" idea (below) is the product owner's own addition on top of this shape, not something borrowed directly from HOI4.

### F-08: Helldivers 2 (Major Order / Galactic War reference for the interstellar Gilden conflict)

Evidence: Major Orders are time-limited, community-wide (entire playerbase) collective objectives that drive the ongoing "Galactic War" narrative — common tasks include liberating a planet, holding a planet until the order expires, exterminating a set number of enemies, or defending a set number of planets. Individual mission contributions feed a shared planet-liberation percentage (a tug-of-war meter reaching 100% locks in the outcome); each contribution is scaled by a difficulty modifier and an "Impact Multiplier" that scales *inversely* with how many other players are active in the same window — so contributions stay meaningful whether population is high or low. Outcomes are not scripted: success or failure genuinely changes the state of the war based on aggregate player behavior, not authored plot.

Implication: this is the direct model for the interstellar Gilden-conflict loop the product owner wants — large-scale, time-limited collective goals issued by a faction, individual Kingdom/DM contributions aggregating toward it, and a genuinely emergent (not pre-scripted) outcome. The Impact Multiplier idea (scale contribution inversely with active-participant count) is worth carrying into APPLY as a candidate fairness/balancing mechanic, so an Encounter stays meaningful regardless of how many Kings happen to be active at a given time — not yet confirmed as adopted, just flagged as a good fit.

## Concept Direction (agreed with product owner so far)

**Cooperative loop, not three silos.** All three product metaphors feed a single shared resource/territory state instead of running independent progress tracks:

1. VTT session (live, DM-run) → generates DM points + campaign resources + player XP/loot (extends `GameSession.xp_earned`/`treasure_log`).
2. Strategy/diplomacy layer (DM-run, Civ-for-resources + CK3-for-territory) → DM points/resources spent on buildings, tech-like unlocks, and claims; claims are accepted or refused by the current owner, refusal can escalate to war (war resolution mechanic not yet designed — APPLY-phase item).
3. MMO layer (player-run, works without a live session) → players run DM-built/upgraded dungeons/quests, generating resources back to that DM and XP for themselves.
4. Faction bonus (candidate substrate: the existing `guild.py` narrative guilds) → allied DMs share a portion of yield or common tech/building bonuses, so an individual DM's session activity has value beyond their own realm.

**Vassalage (CK3-lite, deliberately simplified).** Kept to two variables instead of CK3's full intrigue/succession system, specifically to avoid the known toxicity failure modes of player-driven political power in grand strategy multiplayer (snowballing, forced war participation via alliance chains, permanent power gaps once a player falls behind, griefing of new/weak players):

- **Tribute percentage is a single fixed global value across all vassalage relationships (confirmed decision, resolves former open question 1)** — not scaled by the level difference between king and vassal. Exact number is a numeric-tuning detail for APPLY (placeholder range 10-15%), taken only from resources the vassal actually generates (so an inactive vassal owes nothing, and a king cannot pure-idle off tribute).
- A fixed, limited buff/treasure/magic-access catalog granted downward — not freely combinable, to keep the negotiation surface small.
- No war-locked exit: a vassal can dissolve the relationship at any time for a DM-point cost, without requiring combat.
- Vassal cap per king **starts at 0 and grows with the king's own DM level** (confirmed decision) — influence must be earned through play, not granted at creation. This is the liege-side capacity for how many incoming vassal commitments a king can hold; see "Personal service capacity" below for the complementary vassal-side resource.
- New/low-level DM protection window during which they cannot be claimed or vassalized.
- Contract has a renewal cadence rather than being permanent, giving both sides a built-in periodic exit point.
- **Liege insulation (confirmed decision):** a liege suffers **no negative consequences** if two (or more) of their vassals go to war with each other. This explicitly rules out CK3-style contagion, where vassal conflicts can destabilize or drag in the liege. A liege's own core gameplay loop stays exactly as it would with no vassals at all — vassalage is purely additive for the liege side, never a liability, which keeps the political layer from leaking risk into the moment-to-moment session/province experience.
- **Territory/claims model confirmed CK3-style end to end (resolves former open question 2)** — no Civ nation-as-container framing needed anywhere, including for unclaimed "expansion" provinces (those are just unclaimed, not administered as an abstract container).

**Correction to an earlier draft of this document:** a prior version of this section stated that every DM has a single fixed pool of 2 "Ämter" slots *shared* between their own specialist domains and vassal-service commitments. That was a misreading — the product owner has now clarified these are **two entirely separate resources**, corrected below.

**Specialists (Evil-Bank-Manager-lite) — a DM's own realm-management layer, independent of vassal/liege status:**

- **Domain list confirmed final (resolves former open question 3):** Bauwesen/construction, Verteidigung/defense against raids and claims, Diplomatie/claim-and-alliance handling, Dungeon-Verwaltung/MMO content quality.
- **Slot count (confirmed decision, corrects the earlier "2 shared slots" error):** every DM has **4 base specialist-domain slots** — i.e. every DM, even a brand-new one, can in principle staff all four domains from day one, not just 2. Slots then scale with realm size: **+1 extra slot per 6 provinces governed**.
- **What a 5th+ slot grants (confirmed decision, resolves former open question 1, informed by F-07/Hearts of Iron 4):** an extra slot beyond the base 4 becomes an **Assistant** attached to one existing domain (a deputy stacking on top of that domain's primary specialist, boosting its output further) rather than a whole new independent specialist. **Which domain currently receives the assistant slot rotates automatically** — it's system-decided, not a player choice. **Deliberately deferred:** whether/how players can influence or specialize this rotation later (e.g. steer it toward a preferred domain) is explicitly left open for now, same treatment as the other deliberately-deferred MVP items below.
- **Buffs apply realm-wide (confirmed decision):** a specialist's bonus is distributed across the DM's *entire administered realm*, not scoped to a single province. This is a broader scope than earlier drafts assumed.
- Specialists can be acquired two ways (confirmed decision, resolves former open question 6): **buy** — a paid, randomized search across experience tiers (novice/veteran/expert, Evil-Bank-Manager-style), paid in DM points, higher tiers cost more but roll better stats; or **create/customize** — a simple D&D-style point-buy system applied to the domain stats, letting the DM author a specialist directly instead of rolling one.
- Specialist stats directly modify that domain's output (e.g. a strong Verteidigung-specialist reduces incoming claim/raid success; a strong Dungeon-Verwaltung-specialist improves the loot/XP the MMO layer generates).
- **No attrition (confirmed decision, deliberate simplification vs. Evil Bank Manager):** hired specialists do not randomly leave, quit, or expire — no retention-management busywork. A domain slot only changes occupant when the hiring DM voluntarily replaces it.
- **Player-DMs as specialists are always coupled to vassalage (confirmed decision, resolves former open questions 4 and 5)** — corrects an earlier draft that framed this as a third, independent "lighter-weight" relationship with no tribute/hierarchy. That was wrong: a player-DM can only fill another DM's domain slot *by becoming their vassal*. The reciprocity question is therefore already answered by the standard vassalage buff/tribute exchange defined above — no separate reciprocity scheme is needed.
- **"Domänenherren" as live-session NPCs (confirmed decision):** a domain officeholder — NPC-bought, NPC-created, or vassal player-DM — can appear as an actual NPC inside the owning DM's live VTT sessions. This directly reuses the existing `TokenState`/`SessionInitiative` NPC-proxy pattern already inventoried above (`token_type='npc'`, optional `character_id`) — the strategic office-holder and the in-session NPC stand-in are the same conceptual entity, giving the strategy layer a visible, playable presence at the table instead of staying an abstract stat block.

**Personal service capacity — "2 Ämter" (confirmed decision, replaces the earlier shared-budget error entirely):** every DM-*character* additionally has exactly **2 personal office slots**, entirely separate from their own realm's specialist-domain slots above. These 2 slots represent how many *other* DMs' realms this DM-character can personally serve in — i.e. how many vassalage commitments to others they can hold. A DM can actively offer one of these slots to a liege (e.g. to form an alliance), which is exactly the mechanism by which they become that liege's vassal and fill one of the liege's domain slots.

- **Fan-out confirmed (resolves the last structural open question):** a DM's 2 personal slots **can** go to two *different* liege lords — but only if both lieges hold their title **within the same Kingdom**. Cross-kingdom personal service is not possible this way; that's the seam where an "overarching faction" concept above the Kingdom level becomes necessary (see below).

This cleanly separates three things that an earlier draft had conflated into one: **(1)** how large your own realm's specialist capacity is (scales with your own province count), **(2)** how much personal capacity you have to serve *elsewhere* (fixed at 2, independent of realm size), and **(3)** whether serving elsewhere requires vassalage (yes, always, per the confirmed decision above).

**Territory hierarchy — worked example ("Solaris"), as given by the product owner:**

- Sonic (a DM, DM-Level 20) holds the King title over the Nation **Solaris**.
- Solaris is subdivided into 3 **Herzogtümer** (duchies), each managed by one of Sonic's 3 vassals — consistent with the vassal-cap-grows-with-king-level rule above (level 20 supports at least 3 vassals in this example).
- The 3 duchies together make up the entire map of Solaris, which totals **64 provinces**, split as: Duchy 1 = 15 provinces, Duchy 2 = 23 provinces, Duchy 3 = 18 provinces (56 provinces claimed).
- The remaining 8 provinces (64 − 56) are **not managed by any player** and serve as open expansion space — available for new claims rather than being pre-assigned to anyone.

This is the first concrete numeric anchor for the Kingdom → Duchy → Province hierarchy, and matches the now-confirmed CK3-style character-driven shape (a king with named vassals holding named duchies, not an abstract nation container).

**Hierarchy levels and province typing (confirmed decisions):**

- Kingdom size is **variable, not fixed** — a kingdom is simply as large as the sum of provinces it currently holds. The Solaris example's "64" was illustrative, not a constant (resolves the earlier open question on this).
- Confirmed hierarchy depth: **Kingdom (Nation) → Duchy → Province**, and nothing smaller than Province. Duchy is explicitly *not* the smallest organizational unit — it exists to group provinces, not to be one itself.
- **Duchy composition (confirmed decision, resolves former open question 7):** a Duchy can consist of any number of provinces of any type — Werkzeug, Holz, and Mineralien can freely mix within one Duchy, no restriction to a single resource type.
- **Province types are tied to the resource they produce (confirmed decision):** a province's type determines what it produces and its status (power-center-eligible or not).
  - **Werkzeug (tools)** provinces contain a settlement and are the only type that can be a DM's **power center** (claimed as a capital/seat, defended, etc.).
  - **Holz (wood)** and **Mineralien (minerals/stone)** provinces are separate types; they can also contain settlements but are not power-center-eligible.

**Correction to an earlier draft of this section:** all three province types can host DM-run sessions — "Holz/Mineralien are not actively DM-run" (as an earlier version of this doc stated) was wrong. What's actually true is narrower: the province's *resource output* is automatic/system-controlled regardless of whether sessions happen there (see below) — but sessions themselves are not restricted to Werkzeug provinces, and from the players' side a session in a Holz or Mineralien province should feel like a completely normal D&D session, no different from one in a Werkzeug province (confirmed decision). This also means the "3 sessions run there" unclaimed-province purchase rule applies uniformly across all province types, resolving the earlier open question about its scope.

- **Automatic attribution for Holz/Mineralien output (confirmed decision, output only — not session eligibility):** these provinces produce automatically, with no active management *required* for output to flow — that output is simply attributed to whichever DM owns/holds the province, with the standard vassalage tribute percentage deducted if that DM is a vassal, exactly like any other resource. Sessions can still happen there on top of this; they just aren't what makes the resource output occur.
- **Upgrade mechanic confirmed (resolves former open question 8):** a simple level-based system with fixed costs in increments of 50 (currency: DM points, consistent with the rest of the economy) — deliberately kept as a plain scaling lever rather than a deep separate system, consistent with the "don't over-complicate" instinct behind the vassalage and specialist designs. Whether it ties into the Bauwesen specialist domain or stands alone is a minor remaining APPLY-phase wiring detail, not a design fork.
- **"Minimal skeleton, maximum DM freedom" (confirmed design principle — direct response to the narrative-freedom tension flagged above):** the system should only assert the bare minimum structural fact implied by a province's type — e.g. a Holz province is simply known to contain "a sawmill or a mill," a Mineralien province "a mine" — and leave everything else (why it's there, who runs it, what's actually going on, any quest/story content) entirely to the hosting DM. The system provides the skeleton; the DM provides the story. This is the concrete mitigation for the gamification-vs-storytelling tension — narrow, mechanical prescription at the province-type level, unlimited narrative latitude above it.

**First acquisition of an unclaimed province (confirmed decision, partially resolves the ownership-assignment question above).** Getting an *unclaimed* province is different from taking one that already belongs to another DM:

- Taking a province **already held by another DM** goes through the claims flow already defined above: spend DM points to lay a claim, the current owner accepts or refuses, refusal can escalate to war.
- Acquiring an **unclaimed** province is closer to a purchase than a negotiation: it costs **X DM points**, and the DM must have **run a minimum of 3 sessions** there first. Both conditions apply together (pay + demonstrated activity), not either/or.
- **Deliberately deferred for MVP crystallization (explicit product-owner scoping call, not an oversight):** exactly how DM points are earned/distributed, and whether "number of sessions run in the province" remains the *only* qualifying activity metric, or gets joined by others later. Both are intentionally left unresolved for now rather than locked in prematurely.

**Open tension flagged by the product owner, not yet resolved:** a DM must still be able to tell their own story — the session-count/DM-point gamification of province acquisition must not crowd out narrative/creative freedom. No mechanic for this exists yet; noted here so APPLY doesn't lose track of it as a real constraint, not just a nice-to-have.

**Overarching factions above Kingdom level (confirmed decision — reuses the existing `guild.py` Gilden).** Directly surfaced by the personal-service fan-out rule above (a DM's 2 Ämter can serve two different lieges, but only within the same Kingdom) — this draws a hard boundary at the Kingdom level for personal service, and this is the layer that operates above it. Connects back to two things already on record: the original brainstorm's "nations have alliances/conflicts on a continent" idea (never mechanically defined until now), and the existing `guild.py` inventory finding (four fixed narrative "Gilden": Sternenwacht, Bernsteinkreis, Nebellaterne, Eichenbund), which was flagged early on as a candidate substrate and is now confirmed as the actual vehicle.

- **Gilde affiliation is the King's decision alone (confirmed, resolves the last open question of this document):** Duchies and individual DMs cannot affiliate with a Gilde independently — only the King decides, for the whole Kingdom. Deliberate simplicity choice, and explicitly intended to seed political-intrigue stories: since only the King controls the Kingdom's Gilde allegiance, removing or replacing a king (e.g. "regicide") becomes a natural, story-worthy way to flip a Kingdom's faction alignment.
- **Critical role-terminology clarification (confirmed, corrects an implicit ambiguity in this document up to now):** "GM" (Game Master) and "DM" (Dungeon Master) are **different roles** in this design. Everywhere this document says "DM," it means the per-campaign/province-owning player role (runs sessions, holds titles, vassalage, etc.) — that has not changed. "**GM**" refers to what this document should now call **Admins** — a distinct, higher-privilege role, plausibly mapping onto the `Role` model's existing `Admin` RBAC tier already noted in the Current-State Inventory (`Role`: Player/DM/Admin). GMs/Admins are not DMs and do not hold provinces/titles themselves in this context.
- **The Gilden are a system-controlled instrument for GMs/Admins (confirmed):** unlike the DM-vs-DM political layer (vassalage, claims, wars), the four factions are administered top-down by Admins, not fought over bottom-up by DMs.
- **The overarching MMO story is told through the Gilden (confirmed):** the meta-narrative arc of the whole world is primarily resolved at the faction level, and **how the DMs within a faction act/perform determines how that overarching story progresses** — i.e. collective DM behavior inside a Gilde feeds upward into the Admin-driven meta-plot, the same "system provides the skeleton, players provide the substance" principle as "minimal skeleton, maximum DM freedom" above, just applied at world-story scale instead of province scale.
- **Scale confirmed: interstellar/multiversal, not confined to one world (confirmed decision):** the Gilden operate across planets and the multiverse (tying back to the very first brainstorm's Multiverse → World → Planet structure), not just within one continent or world.
- **Deep Gilden lore/backstory is deliberately deferred, kept as a MacGuffin/Deus Ex Machina (confirmed product-owner scoping call, same treatment as other Deliberately Deferred items):** working out *why* the four Gilden actually fight at a coherent interstellar/multiversal scale is explicitly ruled too complex to fully justify right now, and is intentionally postponed to a later pass with the specific people who'll own that lore work (worldbuilders/community, not this design doc). The Gilden are usable as a plot device without that backstory being fully resolved.
- **Core mechanical story loop confirmed (Helldivers-2-style, see F-08):** the four Gilden are in active competition with each other, expressed as periodic large-scale "Encounters" — time-limited, collective goals (e.g. gather a set amount of resources, defeat a set number of enemies) that Kings and their vassal hierarchies must respond to. Individual Kingdom/DM contributions aggregate toward the faction-wide goal; success or failure shifts the state of the interstellar Gilden conflict.

**World Encounter Score (WES) — the Encounter contribution metric (confirmed decision, resolves former open question 1):** a new, second currency, distinct from DM points — DM points remain the strategic-layer economy (leveling, titles, claims, specialists, vassal-dissolution); WES exists specifically to measure activity toward Gilden Encounters. It is a fixed value per completed activity, aggregated across every player and DM within a governed territory:

- A DM running one session: **+50 WES** (flat).
- **+10 WES per player** present in that same session, added on top of the flat 50 (confirmed additive — a session with 4 players contributes 50 + 4×10 = 90 WES from the DM's side alone).
- A player participating in a session: **+5 WES** per player (separate from and additional to the DM-side numbers above).
- A player completing an MMO dungeon (the DM-less content defined earlier): **+5 WES**.

These all sum together and aggregate upward through the territory hierarchy (province → duchy → kingdom), ultimately contributing to whichever Gilde the Kingdom's King has joined. Consistent with the "don't over-complicate" instinct running through this whole document — flat, fixed values per activity, no formulas or multipliers yet.

## Risks and Assumptions

- **Scar tissue precedent (different codebase, same lesson):** the sibling `rolldrauf_bot` Discord bot once built and then deleted a generic "game supertype" schema after it went unused (zero rows/callers). No equivalent has been found yet in `roll-drauf-vtt`, but any new "World"/"Territory" supertype here should stay narrowly scoped for the same reason.
- Multiplayer political systems (CK3/EU4 lineage) have well-documented toxicity patterns — snowballing, forced war participation, permanent power gaps, new-player griefing — these must be actively designed against (see vassalage guardrails above), not inherited by copying the reference games wholesale.
- Map-editor ambition (Inkarnate-level terrain brush + asset marketplace) is a substantial, separately scoped gap; bundling it into the MMO-progression workstream would blur scope boundaries.
- Art direction (2D sprite vs. isometric pseudo-3D/Disgaea-style) is undecided; an isometric shift would require new `TokenState` fields (z-order/height, facing) — deferred, but noted so APPLY doesn't have to rediscover it.
- **Gamification vs. narrative freedom:** quantifying province acquisition and DM progression through DM points and session counts risks crowding out a DM's ability to tell their own story on their own terms. Flagged explicitly by the product owner as an unresolved tension. Partial mitigation now confirmed — see "Minimal skeleton, maximum DM freedom" above — but only covers province flavor/content, not the acquisition gamification itself, so this stays a live risk to watch during APPLY.

## Open Questions

None remain. The full structural design — Kingdom-and-below (vassalage, specialists, territory, provinces, acquisition) and the Gilden-faction layer above it (affiliation, Encounters, WES) — is resolved. Only the items in Deliberately Deferred below are still open, and those are explicitly not blockers.

## Deliberately Deferred (explicit product-owner scoping call — not blocking APPLY, do not resolve prematurely)

- **DM point distribution/award formula:** exactly how DM points are earned from running sessions is intentionally left open for now.
- **Whether session-count is the only acquisition/qualification metric:** "3 sessions run in the province" is the only confirmed criterion today, but it's explicitly left open whether other criteria join it later — don't assume it's final just because it's the only one specified so far.
- **Exact tribute percentage value:** confirmed to be a single fixed global number, but the number itself is a numeric-tuning detail, not a structural decision.
- **Assistant-slot rotation influence:** whether/how players can eventually steer which domain's rotating assistant slot activates is explicitly left open (see the Specialists section above).
- **Deep Gilden lore/backstory and their mechanical rebalancing as symmetric MMO factions:** explicitly postponed to a later pass with the specific people who'll own that lore/community work — not part of this design doc's scope. The Gilden function as a MacGuffin/Deus Ex Machina in the meantime.
- **Impact-Multiplier-style contribution balancing (from F-08/Helldivers 2):** flagged as a candidate fairness mechanic for Encounters, not yet confirmed as adopted.

## Next Step

The structural design is complete — ready to move to APPLY. Design the concrete data model additions (DM progression/points ledger, resource ledger, WES ledger, territory/claims entity incl. Kingdom/Duchy/Province hierarchy and first-acquisition purchase path, vassalage contract entity, realm specialist-domain entity with its assistant-slot rotation, personal-office/service-capacity entity, Gilde/faction entity with Encounter tracking, session-NPC linkage) and their interfaces to `GameSession`/`Campaign`/`TokenState`, plus a first pass at war resolution for refused claims and a stance on the narrative-freedom tension. The Deliberately Deferred items remain open by design and don't need resolving first.
