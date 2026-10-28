# DAD-M Discover: character creator parity program, 2026-10-28

**Status:** Discover complete for planning; facts and risks only. No application changes.

## Input summary

Audit whether Roll Drauf's character creator is usable, minimal, segmented, and functionally comparable to D&D Beyond's creation paths. Turn the findings into a complete DAD-M milestone program. Preserve Roll Drauf's own presentation, SRD 5.2.1 and authorized homebrew content, and the VTT/Play/DM integration.

## Current-state summary and evidence

- The original [48-point inventory](DADM_DISCOVER_CHARACTER_CREATOR_2026-10-18.md) and [P1–P12 records](DADM_APPLY_CHARACTER_CREATOR_P12_2026-10-18.md) show a substantial delivered SRD creator, rules evaluator, sheet, rolls, inventory, level-up, multiclass, party sharing, and export. The October 18 Discover's statement that no SRD creator exists is historical, not current.
- The [October 28 browser audit](DADM_DISCOVER_CREATOR_UX_PARITY_2026-10-28.md) checked the live-equivalent creator assets and Chromium at 390×844. Guided Fighter creation and quick-mode browser checks passed. It found the first class choice below the phone viewport, step changes returning to the top, and a 14,765px all-sections “quick” page. [Phone proof](proofs/creator-ux-audit-2026-10-28/mobile-first-viewport.png).
- `vtt/static/js/srd-creator.js` has eight guided sections and a quick mode that renders all sections; `vtt/static/js/srd-creator-random.js` can generate levels 1–20, but the home route starts a level-1 random character without a parameter screen. `vtt/static/js/srd-creator-steps.js` explicitly says origin-feat detail choices and species spells are not modeled.
- `vtt/rules_content/creator_sources.py` registers only `srd-5.2.1-de`. Published global Species are appended through `/api/srd-creator/species-catalog`; other Creation Engine categories do not enter the creator as selectable, rule-evaluated options. The [Duckfolk browser journey](DADM_MONITOR_AGENTIC_FRICTION_2026-10-28.md) proves an isolated author→global Species→unrelated player→sheet/table path in test, and records a separate DM action-summary rendering mismatch. It does not prove every live global publication state.
- P7 requires players to import selected starting equipment after creation; P8/P9 leave hit dice, rests, consumed spell slots and some tool proficiency modeling open. P10–P12 leave history/undo, companion mechanics, full DM editing, import round-trips, and feature-rich PDF gaps. These records are implementation evidence, not acceptance of the entire 48-point promise.
- The [sheet layout monitor](DADM_SHEET_LAYOUT_2026-10-28.md) proves the first roll control is visible on a 390×844 sheet and the sheet-to-table and Duckfolk browser journeys passed. Builder friction remains separate from that sheet fix.

## Benchmark and limits

D&D Beyond's [official first-character guide](https://www.dndbeyond.com/posts/1059-how-to-create-your-first-dungeons-dragons) describes Standard, Quick Build (species, class, name, then defaults), Randomize with parameters, and Premade. The [October 2026 changelog](https://www.dndbeyond.com/changelog/) confirms active Quickbuilder and Premade surfaces, including Premade filters. Its [2026 roadmap](https://www.dndbeyond.com/posts/2132-d-d-beyonds-2026-development-roadmap) describes Quickbuilder as a streamlined level-1 path, while future deeper-builder promises are plans rather than shipped parity criteria. This audit uses public product documentation and the repo's existing owner requirement; no signed-in competitor journey was inspected. Behavior is the benchmark, not copyrighted design, text, code, assets, or licensed content.

## Relevant inventory and 48-point trace

The statuses below mean **core**: a working path exists but parity acceptance was not independently completed; **partial**: a documented subfunction remains; **open**: no corresponding player-facing path was found. Matrix numbers refer to the [October 18 inventory](DADM_DISCOVER_CHARACTER_CREATOR_2026-10-18.md#4-paritäts-matrix-vollparität-owner-vorgabe-2026-10-18). No group is declared fully accepted by this audit.

| Matrix points | Observed state | Evidence / remaining work |
|---|---|---|
| 1, 9–12 | Partial | Guided drafts/resume and summary work; Quick is all-fields, random lacks entry parameters, mobile and finding recovery need work. |
| 2–3, 5, 7–8 | Core with partial choices | Class, origin, abilities, spells and description exist; origin feat detail, species spells and some spell changes are absent. |
| 4, 6, 13–14 | Open/partial | Custom background and source preferences absent; starting gear needs a later import; high-level starts lack full gear/resource accounting. |
| 15–20 | Core with partial mechanics | 1–20, feats, XP and multiclass exist; spell swaps, tool grants, hit dice, and complete respec/history remain. |
| 21–28 | Core with partial play loop | Derived sheet and table rolls work; conditions, rests, resources, spell slots and some attack/spell use are incomplete. |
| 29–36 | Partial | Inventory and mobile sheet exist; manual overrides, structured companions, all rule links, and broader homebrew effects remain. |
| 37–44 | Partial | List, party, sharing, PDF/JSON, avatar/token and DM awards exist; restore/undo, rich export, DM co-edit, condition sync and full token mapping remain. |
| 45–48 | Partial | SRD source pinning and global Species publication exist; general source enablement, campaign content gates, other playable Creation Engine types and safe structured effects remain. |

## Dependencies and constraints

- One canonical server evaluation/finalization path (`vtt/characters/srd_creator.py`, rules content and evaluator); incomplete drafts may save, but finalized characters require server validation. Existing draft/version/source pins, saved characters, Roll Drauf Light and portable imports must remain readable.
- Creation Engine publications have authors, scope and revisions. Global publication must be available to unrelated users only after its existing checks, and private/campaign content must stay within its scope.
- The bundled rule corpus is German SRD 5.2.1, CC BY 4.0, plus own or licensed content. Published source versions are immutable; attribution must remain accessible. No external proprietary content, implementation, visual copy, or account import is authorized.
- VTT character columns, live tokens, Play Hub, DM Hub, and two-tab sheet-to-table rolls consume creator output. Their contracts are regression boundaries, not isolated UI extras.
- Milestone work must run Discover → Apply → Deploy → Monitor, with reviewed outputs and phase gates. The plan belongs in `docs/decisions/` with a version and draft/approved status.

## Risks and assumptions

| Severity | Finding | Planning disposition |
|---|---|---|
| High, product | “Quick” currently means a long all-fields editor, while the requested benchmark means a few choices and defaults. | Treat as an explicit top-priority gap; do not label the current mode parity-complete. |
| Medium, rules | Missing feat/species choices, gear materialization, spell use and rest accounting can yield a legal finalized record that still needs manual repair to play. | Give rule-complete creation and creator→sheet continuity separate acceptance gates. |
| Medium, scope/access | General homebrew sources introduce version, license, owner, campaign and global visibility rules beyond current Species. | Split source discovery from per-type playable adapters; require server authorization and revision pinning. |
| Medium, data | Draft schema, evaluation, import and finalized records are shared across journeys; a UX shortcut could silently change character semantics. | Preserve canonical server evaluation and use compatibility/round-trip checks. |
| Medium, evidence | Prior P1–P12 documents describe delivered slices but no fresh exhaustive 48-point browser proof exists. | Record observed core/partial/open status; rebaseline with targeted journeys before claiming parity. |
| Low, competitor access | Public official documentation does not expose every signed-in state or recent experiment. | Freeze a dated behavioral benchmark and mark later competitor changes as a new planning input. |

## Open questions and next step

The unresolved items are design choices for Apply: what constitutes an auto-filled but still rules-valid quick build for every supported class/species; which public homebrew types need structured effects first; and how draft/source version drift should be shown to players. They do not block an explicit milestone plan. The next phase is Apply: define bounded milestones, contracts, acceptance journeys and deploy/monitor handoffs. No implementation is authorized by this audit-only request.

**Artifacts (retention):** this Discover record (keep); linked prior audit and screenshots (keep); code/docs cited above (source of truth). **Next step:** Apply program plan v1.
