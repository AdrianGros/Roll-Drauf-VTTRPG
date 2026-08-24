# Roll Drauf VTT — Build Report

**Date:** 2026-08-24
**Build:** `a26dedc` — `B2 Seitenmodell mobile-first`
**Branch:** `main` == `origin/main`
**Scope:** current build, book-UI progress, planned patches, research, and verification

## Executive summary

The repository is in a healthy, locally testable state. The functional VTT
baseline is substantially stronger than the older README and milestone files
suggest: the scene-stack model is canonical, browser automation exists, the
play table has map/token/chat support, Beyond20 integration is present, and the
full Python suite passes.

The active product direction is now the book UI. Two visual phases have landed:

- **B1 — Fundament:** Literata reading typography, Cinzel display typography,
  shared theme loading, canonical book tokens, real fonts, and a German UI
  pass.
- **B2 — Seitenmodell:** mobile-first single-page layout, dashboard as a table
  of contents, reading ribbon, running heads, folios, 66ch prose measure,
  German hyphenation, and removal of the accidental gray header slabs.

The next meaningful design patch is **B3: one page-transition and navigation
engine**. The current code still contains GSAP, legacy BookShell routes,
BookScene timelines, page-turn overlays, and keyboard arrow hijacking. Those
are explicitly identified as the next consolidation target in the design brief.

The browser acceptance layer is now stricter than the earlier smoke robots: it
executes the logged-out login → dashboard → logout journey for DM and player
roles, records screenshots/DOM/ARIA/metrics/traces, and runs geometry,
responsive, runtime, network, accessibility, keyboard, and text-resize gates.

## Current build inventory

| Area | Current state |
|---|---|
| Runtime | Flask application with Socket.IO, database-backed auth, campaigns, sessions, maps, tokens, chat, combat, assets, and ops endpoints |
| Session state | Scene-stack model is canonical; the three `active_map_id` write paths were unified in `551e947` |
| Browser realtime | Socket.IO client is vendored locally; the original missing-client failure was fixed in `6e67da1` |
| Play table | Scale/pan, map upload, token UI, chat, session controls, realtime sync, and Beyond20 roll/HP/condition integration are present |
| Book routes | Dashboard, campaigns, characters, character sheet, login, registration, and play use the book visual system to varying degrees |
| Typography | Real Literata, Cinzel, BadScript, and PirataOne assets are present; Literata is now the body-reading font |
| Browser acceptance | Ordered DM/player login-to-dashboard journey with Chromium/Firefox desktop and phone cells, screenshot/DOM/ARIA/trace evidence, and severity-aware reporting; WebKit is attempted and reported blocked when host libraries are unavailable |
| Mobile | Phone audit, touch-context robot gates, responsive book fixes, and separate DM/player phone-session coverage now pass in disposable-stack browser tests |
| Operations | Staging script, boto3 dependency, nightly backup script, pytest configuration, and scene-stack cleanup have landed; live deploy/restore proof is not established by this report |

## Recent delivered work

The current build is the result of the following recent cuts:

- `a0dea55` retired the obsolete session-map/session-token path in favor of
  scene stack.
- `8f13ee0` added disposable-stack browser robots with preflight and evidence
  bundles.
- `551e947` fixed the third, previously missed map-state write path.
- `ee84f6a` brought the Python suite to 415 passing tests at that point.
- `6a4d2b5`, `0a6b67e`, `f313953`, and `cc2682e` addressed the S3 dependency,
  staging deployment, pytest setup, and automated nightly backup respectively.
- `23cd8e3` and `a1fd70f` deepened the play table and added a complete DM/player
  session robot.
- `afd7898`, `73a84e1`, and `85c633a` added the external-roll bridge, HP sync,
  rich roll cards, condition sync, and turn tracking.
- `7c6de5f` fixed the app-wide click-default bug and made token-art upload
  visible.
- `7cdc675` delivered B1.
- `dbbe2dc` recorded the phone audit and two-mode mobile direction.
- `ab67094` added the mobile gates and immediate play-table fixes.
- `a26dedc` delivered B2.
- The current working-tree patch adds a dedicated DM/player phone-session gate,
  a strict login-to-dashboard journey, browser-matrix evidence, and registers
  both in the full robot runner.

## Book-UI status

### Landed: B1 foundation

The live design system now establishes paper, ink, rubrication, gold, status
colors, Literata body text, Cinzel headings, and a system sans for tool surfaces.
All primary book templates load the shared font/theme/component stack. The
runtime also uses real font files rather than the earlier invalid `.woff2`
placeholders.

The foundation is not yet fully clean: `theme.css` retains legacy aliases and
the older CSS files still contain hard-coded colors. This is intentional debt
for B2–B5, not evidence that the token migration is complete.

### Landed: B2 page model

The dashboard is now a genuine table of contents rather than a long
self-description. It exposes the reading ribbon and live counts for campaigns,
characters, and sessions. Book pages now have running heads, folios, opaque
paper surfaces, a classical margin hierarchy, and a single-page mobile base
state below 1200px.

The accidental gray slabs were traced to an unscoped `header` rule in three
templates and narrowed to `body > header`.

### Not landed: B3–B7

The next phases remain planned, not complete:

1. **Mobile closeout / revalidation:** the emulated-phone role gate is green;
   follow up with real-device coverage for ≥44px touch targets, no `100vh` in
   Play styles, full-width phone sheets, visible dice/chat/token actions, and
   no horizontal overflow at 390×844 and 844×390.
2. **B3 — one transition engine:** adopt View Transitions API as the sole
   navigation engine, centralize route direction, remove duplicate bindings,
   remove arrow-key hijacking from book navigation, and preserve reduced-motion
   behavior.
3. **B4 — table material:** bring the play surface onto the shared token set;
   retain a dark map/table area as a deliberate derived surface; replace the
   current curtain choreography with one book-to-table handoff.
4. **B5 — night reading and gates:** add an intentional dark mode and wire the
   contrast, language, reduced-motion, token, layout-monotony, and
   single-engine gates into the robot evidence flow.
5. **B6 — Spielerbuch:** portrait companion mode for character sheet, dice,
   chat, and a mini-map; player actions remain usable without desktop DM tools.
6. **B7 — Voller Tisch:** landscape full-bleed map, `100svh`, bottom thumb-zone
   controls, and bottom-sheet panels.

## Research completed

The current direction is based on several named research tracks rather than a
generic visual refresh:

| Research | Decision carried into the build |
|---|---|
| `DESIGNBRIEF_BUCH_UI_2026-08-24.md` | Book as material and information order; page turns only at view boundaries; one token set; German-first chrome; the table is a separate workspace |
| `MOBILE_AUDIT_BUCH_UI_2026-08-24.md` | Portrait is the purest single-page form; phone play needs deliberate Spielerbuch and Voller-Tisch modes; mobile must be measured with touch contexts |
| `MASTERPLAN_1_100_2026-08-22.md` | Stabilization-first sequence; competitor/user research across Roll20, Foundry, Owlbear Rodeo, TaleSpire, Astral, and Alchemy; operations and documentation are explicit arcs |
| `ITEM_SYSTEM_SET_BONI_RESEARCH_2026-08-18.md` | Server-authoritative item definitions/instances, controlled effect DSL, 2/3/4-piece thresholds, alternatives to mandatory sets, and bad-luck protection |
| `UI_ANALYSE_WORLD_ATLAS_HOME_2026-08-18.md` | Atlas Command Surface as a possible future home; social feed remains secondary; Play remains a separate tactical workspace |
| April DAD-M Book UI documents | Earlier IST/SOLL, access-gate, spread, character-sheet, and play-workspace decisions; useful provenance, but not the current status source |

## Verification evidence

### Local checks run for this report

- `venv/bin/python -m pytest -q tests` → **427 passed**, 2065 warnings, 253.89s.
- Targeted book checks → **17 passed**.
- `git diff --check` → passed.
- At report start, `main` was synchronized with `origin/main`; this run adds
  the mobile-session robot and updates this report in the working tree.

The warnings are not release blockers for this report, but they are real
maintenance debt: deprecated Eventlet/Flask/SQLAlchemy APIs, naive UTC datetime
construction, legacy `Query.get()`, relationship-overlap warnings, and a
pytest rewrite warning.

### Browser verification

The final disposable-stack aggregate run passed all six functional/touch
suites with zero findings:

- `preflight` — Chromium 151.0.7922.34, PostgreSQL disposable-stack checks,
  live-database guard, and real registration/login forms.
- `views` — authenticated desktop route and selector checks.
- `flows` — dice, map/token, and Beyond20 bridge checks.
- `fullsession` — separate desktop DM/player campaign, map, visibility,
  placement, chat, dice, initiative, and session lifecycle checks.
- `mobile` — portrait/landscape touch-context layout checks.
- `mobile_session` — separate DM/player phone contexts covering visibility,
  touch token placement, chat, dice synchronization, landscape layout, and DM
  session end.

The strict journey suite also ran 140 ordered DM/player checkpoints across
Chromium and Firefox at desktop and phone sizes. It is **blocked**, correctly,
until reviewed screenshot baselines exist for the seven named checkpoints and
because this Arch host cannot launch the Playwright WebKit build
(`libicudata.so.74` is unavailable). It still produced screenshots, DOM,
ARIA snapshots, navigation metrics, telemetry, and traces. The remaining
product-level findings were three responsive target-size cases and one Firefox
phone contrast case; no Chromium/Firefox login, route, request, or page-error
journey failures occurred.

Evidence bundle: `/tmp/roll-drauf-vtt-robots-2026-08-24-final/`.
The runner was invoked through the repository's existing sudo boundary because
its disposable PostgreSQL setup requires the `postgres` OS user; the live
database guard still passed. Phone coverage is Playwright emulation at 390×844
and 844×390 with touch/DPR settings, not physical devices or a separate mobile
browser user-agent matrix.

## Risks and unresolved status

| Severity | Risk / gap | Evidence or implication |
|---|---|---|
| High | Production access-control fix is not proven deployed | The masterplan still identifies the privileged-role deployment gap; local tests do not establish live deployment state |
| High | Physical-device and user-agent coverage is not established | The browser robots use Playwright Chromium desktop and touch emulation; Safari/Firefox/real iOS/Android remain outside this run |
| Medium | Bare `pytest` still descends into private certificate directories | `pytest tests` passes; the repository-level command remains environment-sensitive despite `pytest.ini` |
| Medium | Book navigation still has multiple runtime engines | B3 is required before claiming a single-transition invariant |
| Medium | Token migration is incomplete | Legacy aliases and hard-coded colors remain in `theme.css`, `book-shell.css`, `components.css`, `spellbook-theme.css`, and `book-scene.css` |
| Medium | Operational changes lack live proof in this report | Staging and backup code landed, but deployment, restore, and production health were not probed |
| Medium | Strict visual baselines are not yet reviewed | The strict suite intentionally blocks instead of auto-blessing current screenshots; baseline generation requires a human design review after the current patches settle |
| Medium | WebKit is unavailable on this Arch host | Playwright WebKit downloaded, but its Ubuntu fallback binary requires `libicudata.so.74`; Firefox and Chromium ran fully |
| Low | Documentation sources disagree | `README.md` still describes M1–M4, and the April M01–M20 tracker remains active even though the August masterplan and B-series are now the operative direction |

## Recommended handoff

1. Add physical-device or BrowserStack-style coverage for iOS/Android and
   Safari/Firefox before calling mobile release-ready.
2. Treat the green browser result as the acceptance gate for the current
   mobile fixes.
3. Move to an Apply pass for B3 with an explicit inventory of every navigation
   owner and transition trigger before deleting legacy engines.
4. After B3, perform B4 table-material work, then wire the B5 gates.
5. In a separate documentation/operations pass, reconcile the README and old
   tracker with the August masterplan and record live access-control, staging,
   backup-restore, and deployment evidence.

This report is a Discover artifact. It does not claim that the VTT is publicly
release-ready; it establishes the current repository build and the safest next
bounded patch.
