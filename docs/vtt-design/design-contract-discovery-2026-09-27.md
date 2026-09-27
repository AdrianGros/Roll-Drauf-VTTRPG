# VTT design contracts — initial discovery

**Date:** 27 September 2026. **Status:** source and document discovery; a basis for a design document, not an approved design contract. **Retention:** repository artifact. **Input:** assess Creation Engine progress and whether the VTT needs a consolidated design document with testable contracts.

## 1. Engine progress and authority

The [active authority record](../creation-engine/active-contract.json) selects specification v1.1.4, core wire 1.1.3 and registry A1. The [G1 program](../../dadm/artifacts/programs/milestone_program_creation_engine_g1.md), especially §16, records implementation evidence. The v1.2 reading edition does not replace that selection.

| Scope | Recorded position |
| --- | --- |
| G0: specification audit | Passed; G1 implementation authorized on 24 September. |
| G1, WP1–WP4 | Implemented and committed at or before HEAD `66b6fc4`. |
| G1, WP5–WP8 | Implemented and verified in the working tree; uncommitted. |
| G1, WP9 | Acceptance evidence consolidation, the required human study and milestone exit assessment remain open. |
| G2 | Time, choices, grants, reactions and a contrasting ruleset remain a later gate. |
| G3 | Complete lock/update/import/export/rollback coverage remains a later gate; G1 supplies some foundations. |
| G4 | Complete advertised first-ruleset mechanics, progression and NPCs remain a later gate. |
| G5–G8 | World/spatial behavior, publishing/adapters, deployment-scale operations and optional intelligence/extensions remain later gates. |

Eight of G1's nine work packages have recorded implementation evidence. This is a package count, not an effort estimate or a percentage of the full specification. Later gates have different sizes and reuse foundations already implemented.

WP8's initial full suite recorded 1,325 passes and one browser-icon failure. The icon was fixed; the final follow-up recorded 113 passes. No second full-suite run was performed. Engine flags remain off by default and no production cutover is claimed.

The specification's §22 requires at least eight target users, four T45 tasks, reporting of completion/time/confusion/abandonment, an 80% completion target and zero unnoticed creative defaults. The implemented magic-item workflow does not itself establish evidence for all four study tasks. WP9 must map each task to the available surface and record gaps explicitly.

## 2. Existing design material

| Source | What it contributes | Limitation |
| --- | --- | --- |
| [Book UI design brief](../DESIGNBRIEF_BUCH_UI_2026-08-24.md) | Book identity, shared tokens, typography, page model, navigation/motion, table boundary and proposed visual gates. | Dated brief with historical diagnoses and proposed phases; those diagnoses are not automatically current defects. |
| [Overview information architecture](../OVERVIEW_INFORMATION_ARCHITECTURE_2026-08-25.md) | User journeys through campaigns, character creation, preparation and live sessions; optional Discord identity. | Does not place the new Creation Engine editor in those journeys. |
| [B2 design review](../DESIGN_JURY_B2_BASELINES_2026-08-25.md) | Historical examples of functional tests missing visible usability failures, and screenshot-evidence limitations. | Advisory review of older screenshots; this discovery does not reassert its defects as current. |
| [Application architecture](../architecture.md) | Earlier navigation and character-system ideas. | Includes proposed page names and a different presentation vocabulary; not a verified current route inventory or selected design authority. |
| [Engine specification §19](../creation-engine/v1.1.4/creation-engine-v1.1.4.md) | Authorized rendering, semantic presentation, diagnostics, keyboard authoring, labels, focus and non-color status requirements. | Does not specify the full VTT shell, component catalogue or every user journey. |
| [Shared theme](../../vtt/static/css/theme.css) | Existing paper/ink tokens and Literata body-font definition. | Source inspection does not establish rendering quality across all routes/viewports. |
| [Navigation tests](../../tests/test_journey_nav_cta_cleanup.py) | Shared book navigation and campaign-to-play behavior. | Route list covers dashboard, campaigns, characters and character sheet; the new editor is not included. |
| [Book layout tests](../../tests/test_book_scene_layout_contract.py) and [playtable contracts](../../tests/test_public_surface_and_playtable_contract.py) | Existing regression assertions for layout and table interactions. | Several assertions inspect source/markup; their presence is not complete browser, accessibility or usability evidence. |
| [Editor browser tests](../../tests/creation_engine/test_ce_authoring_transports.py) | Real authenticated authoring, mode/locale changes, retry and sandbox execution. | The fixture uses Chromium at 1280×960; these cases do not establish a mobile/cross-browser/keyboard-only conformance matrix. |

The repository therefore already has design intent and some executable contracts. The missing work is to reconcile their authority and coverage, connect the new engine surface, and make remaining requirements traceable.

## 3. Concrete current observations

1. [The editor template](../../vtt/templates/creation-engine.html) loads its own stylesheet and provides a dashboard backlink. It does not load the shared book theme or use the shared book navigation markup inspected in the route contract.
2. [Its stylesheet](../../vtt/static/css/creation-engine.css) defines a standalone dark palette with literal colors and a system font. This differs from the shared paper/ink theme. No selected exception to the older brief's shared-theme rule was identified in the inspected G1 material.
3. The editor already includes labels, status announcements, visible focus styling and a narrow-screen layout. [Its JavaScript](../../vtt/static/js/creation-engine.js) includes focus handling and an unsaved-input guard. Those features require behavioral assessment before claiming full accessibility conformance.
4. The older brief calls for German throughout the interface; the active G1 contract explicitly requires German, English and French authoring prompts. Their respective scope must be recorded when consolidating language rules.
5. The older brief favors visible disabled actions. Engine §14 requires unauthorized information to remain concealed. A design contract must distinguish a visible but unavailable authorized action from information the viewer may not know exists.

These findings come from repository source and document inspection. No fresh production session, rendered cross-device audit, external-source verification or human study was performed in this discovery.

## 4. Questions the design document needs to settle

The following is a discovery checklist, not a newly approved architecture or acceptance catalogue.

| Contract area | Question to resolve | Evidence needed |
| --- | --- | --- |
| Journeys and navigation | Where do players and GMs enter authoring, resume a draft, test content and return to their campaign? | Current route inventory and complete browser journeys by role. |
| Visual system | Which shared tokens, typography, components and table-specific exceptions are authoritative? | Existing design decisions, component inventory and reviewed screenshots. |
| Interaction states | What appears during loading, empty results, validation, stale versions, saving, disconnects and uncertain command outcomes? | State-by-state examples linked to actual transport and domain behavior. |
| Engine integration | Which command, receipt and authorized projection supports each action? | Traceability to the existing engine registry and tests; any actual protocol gap recorded separately. |
| Privacy and roles | Which data/actions are hidden, disabled, view-only or actionable for each viewer? | Role/projection matrix and browser observations without unauthorized data. |
| Authoring and language | How do modes, locales, presets, invalidation and undo remain understandable without choosing mechanics for the user? | Stable question identity plus interaction tests and human-study observations. |
| Accessibility and responsive behavior | Can users finish each journey with keyboard, assistive technology and supported small screens? | Explicit focus/status/error expectations and a declared device/input test matrix. |
| Evidence and change control | Which requirements are approved, implemented, tested or still proposals? | Stable IDs, linked proofs, ownership and recorded exceptions. |

A useful contract entry would record its source, ID/version/status, applicable surfaces and roles, preconditions, observable behavior, denied/failure states, engine references where relevant, verification method and evidence status. Visual decisions need documented values and visual evidence; interactions need state/behavior tests; machine interfaces need schemas where appropriate. Not every design rule belongs in a JSON schema.

## 5. Risks, assumptions and dependencies

| ID | Severity | Finding or assumption | Follow-up |
| --- | --- | --- | --- |
| VD-D01 | Medium | Several dated design documents exist without an authority selection equivalent to the engine's active-contract record in the inspected set. | Reconcile sources, decisions and exceptions before treating a consolidated document as normative. |
| VD-D02 | Medium | The editor has diverged from the shared theme/navigation without design-conformance evidence. | Decide its intended product placement and assess that placement in the design pass. |
| VD-D03 | Medium | Functional editor tests do not establish mobile, keyboard-only, cross-browser or human usability acceptance. | Record these as unverified; define and execute the required checks for the selected scope. |
| VD-D04 | Medium | Broad design work could obscure the still-open G1 exit and repeat the earlier specification/implementation confusion. | Keep engine status and design-document status explicit; scope new implementation through recorded work packages. |
| VD-D05 | Medium | Disabled-control language and locale rules need reconciliation with current privacy and authoring requirements. | Resolve the concrete cases against the active engine contract before finalizing design rules. |
| VD-A01 | Assumption | “VTT design” includes visual design, navigation, interaction states and frontend integration with the engine. | Revisit if a different product boundary is requested. |

Dependencies are the current VTT routes/components, existing design evidence, active engine commands/projections and G1's user-study obligation. No new library or framework is selected here. The current functional editor and legacy VTT behavior are inputs to the design analysis, not automatic target-state choices.

## 6. Next step and verification

Complete a bounded current-state audit of the dashboard → campaign → character/table journeys and the editor, including rendered states. Reconcile the source authority and findings above, then use Apply to produce the consolidated VTT design document and its traceable contract catalogue. Start with the authoring-to-sandbox journey and shared navigation/theme boundary so that the next contract is concrete and reviewable.

Continue G1 WP9 evidence preparation against its existing contract. Any finding that affects its acceptance must be recorded there; a larger design initiative does not silently change the engine gate or replace its human study.

This task adds only this discovery document. Relative file links and whitespace are checked; no application code, active contract, database or deployment is changed, and no new runtime tests are claimed.
