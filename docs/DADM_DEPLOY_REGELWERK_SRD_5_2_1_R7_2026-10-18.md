# DAD-M Deploy: Regelwerk R7 preview activation on the live test environment

date: 2026-10-18
status: deployed as `preview`; not `published`
basis: `docs/decisions/REGELWERK_SRD_5_2_1_PROGRAM_V1.md`, commit `7bfe069`

## Environment fact

The live VTT (`https://vtt.roll-drauf.de`) is the test environment; there is no separate
production. The VTT itself is pre-alpha. Deploys here are reversible tests, not releases.

## What was deployed

- Image `roll-drauf-vtt-app:regelwerk-7bfe069` = previous image `bugfix-20261007` plus the
  Regelwerk files from commit `7bfe069` (reader, package, CSS/JS, nav hooks). The two files that
  already carried unrelated live changes (`book-scene.js`, `campaigns.html`) received only the
  Regelwerk lines; all other unrelated working-tree changes stay uncommitted and undeployed.
- Compose config `/srv/migration/2026-10-07/setup/production.compose.json`: `app` image switched,
  `REGELWERK_PREVIEW=true` added. Only the `app` service was recreated.
- Package: `srd-5.2.1-de`, 101 documents, pages 5-412 covered, status `preview`.

## Verification (2026-10-18)

- Offline image check: package validates (preview, 101 documents, coverage complete).
- Local and public: `/regelwerk`, `/regelwerk/lizenz`, `/regelwerk/5.2.1/de/zauber-f-g`,
  `/api/rulesets/main` (`available: true`), manifest, search ("Feuerball", "Goblin") all return 200;
  `/login` contains the `data-regelwerk-nav` link.

## Rollback

1. Restore `production.compose.json.bak-pre-regelwerk-20261018` over `production.compose.json`.
2. `docker compose -p migration-production -f <file> up -d --no-deps app` (old image
   `roll-drauf-vtt-app:bugfix-20261007` is still present).

## Open before `published` (R7 remainder)

- Named human acceptance owner (not yet named).
- Browser-level acceptance checks: keyboard, reduced motion, narrow screen, print, stat-block layout.
- Final legal/fidelity audit and rollback rehearsal.
- Preview label removal and `published` status only after the owner signs off.
- Commit `7bfe069` is local; not pushed.

## Update: publication (2026-10-18, owner sign-off)

The human owner named themself acceptance owner, accepted the preview ("fast perfekt"), requested
Roll Drauf violet headings, and authorized publishing the whole Regelwerk without slices.

- Headings and accent now `#4b235a` (Roll Drauf violet) in `regelwerk.css`.
- Package `srd-5.2.1-de` is `published`, version `1.0.0`, `publishedAt` 2026-10-18T12:00:00Z; immutable from now on
  (changes need a new version).
- `vtt/rules.py`: a published package is always served; `REGELWERK_PREVIEW` only gates unpublished packages.
  Preview badge/note and the "Vorschau" nav suffix show only while status is `preview`.
- Image `roll-drauf-vtt-app:regelwerk-72e3177` (commit `72e3177`); compose no longer sets `REGELWERK_PREVIEW`.
- Verified locally and at https://vtt.roll-drauf.de: reader, license, document, search, main API (`published`), CSS accent.
- Tests: 40 pass (package + routes). Rollback: previous image `regelwerk-7bfe069` / `bugfix-20261007`
  and `production.compose.json.bak-pre-regelwerk-20261018`.
- Still open: browser-level checks by the owner on device; rollback rehearsal not run; commits not pushed.
