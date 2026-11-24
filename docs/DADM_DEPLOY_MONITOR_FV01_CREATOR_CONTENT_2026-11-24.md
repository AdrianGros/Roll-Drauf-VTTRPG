# Deploy and Monitor FV01 creator names and English details

Status: bounded slice committed, pushed, deployed and live verified. FV01 remains partial; the retained full version through FV18 is unfinished. Permanent. [Apply](DADM_APPLY_FV01_CREATOR_CONTENT_2026-11-24.md).

## Implementation and acceptance

The creator now presents 663 reviewed core/spell entity names and 52 source-backed ability, skill, language and alignment terms in the rules language, independently of site navigation. Canonical German data/IDs, comparisons and mechanics stay unchanged. Equipment, subchoices, remaining rule-derived labels, structured validation and the editor are still open; the partial-language notice stays visible.

The deterministic builder checks source hashes, bounded identity/term coverage, bijection, model/subclass reference graphs, source words and the three reading-only core feature anchors. The authenticated display endpoint validates both compendia and canonical data, returns private/no-cache data with an ETag and fails safely on stale sources. The canonical response gains a hash header; a versioned request avoids reusing its older headerless cache entry. No permission, dependency or schema change.

Explicit presentation helpers drive labels/search/sort without changing state values. Caster/list/spell keys keep checks and focus attached to the correct controls after sorting. Old locale/dialog responses are discarded. Missing English data leaves editing usable with an honest German fallback. Rule dialogs and subclass previews use genuine English source entries; Hypnotic Pattern's actual component difference is disclosed without changing the engine.

Files: creator API and new `creator_locale.py`; source-pinned builder/data; new creator locale client plus creator/steps/preview/template; catalog task and generated translations; focused tests and reproducible release/live helpers.

## Checks and review

[Verification history](proofs/fv01-creator-content-2026-11-24/verification.json) records 20 distinct targeted cases across overlapping runs. An initial cookie/header fixture error and a quoting collection error were corrected. Ten new browser journeys and five prior creator regressions passed. The combined run passed 19 cases and exposed a real English subclass preview defect: EN subclass records omit `features`. Codex generated a source-ordered feature index from the actual EN subclass context, validated it against reviewed DE counterparts, and the final six-case API/EN/fallback run passed. Final builder checks passed two cases again. No full-suite green claim; inherited FV18 findings remain.

All six UI/rules/automatic combinations, source names/details, canonical checked spell IDs after reordering, state/data/evaluation invariance, hash failure, delayed-response ordering, component differences, subclass normal/fallback behavior, pending input, campaign/in-flight result and actual guided/random finalization are covered. Tests use throwaway SQLite, not a lane or production database. Source/data freshness, 3777-message catalog generation, changed JS/Python syntax and whitespace checks pass.

Claude's [identity audit](proofs/fv01-creator-content-2026-11-24/identity-review.json) checked every pair's semantic name/context with limited full-text checks. The [initial code review](proofs/fv01-creator-content-2026-11-24/source-review-initial.json) led to stricter mandatory source pins, context keys and cache/term hardening. The [reworked review](proofs/fv01-creator-content-2026-11-24/source-review-reworked.json) found no supported medium/high issue; bounded term kinds were then tightened. The actual EN feature-index correction came afterwards and has explicit source/compiler/browser checks. Existing Pro authentication was used; no API-key/provider fallback or delegated test/deploy action.

## Live delivery

Normal dashboard → Play & Characters → Characters → create hero → Wizard/Magier journeys pass as Chromium DM 1440/DE site/EN rules/night and Firefox Player 390/EN site/DE rules/paper. Each reads class details, selects two cantrips, changes rules language through settings, reads the selected spell, and reloads the draft. ID/version/state/data/evaluation, selected canonical spell IDs, authored name and unit preference are retained. Both report zero browser errors. [Results](proofs/fv01-creator-content-2026-11-24/live.json).

- Source `842f57e58965c182e46ee6c4f81ad404373bd6d9`, pushed on `fix/feedback-harness-20261123`.
- Image `roll-drauf-vtt-app:fv01-creator-content-20261124-842f57e58`, identity `sha256:d04f4ee8fce80226544116f51a73cc3791d7cedb69f351bb9b9906e729761a18`.
- Base `a28afce53`, image `sha256:4221b9772405bbc0be4d25ffdacea07047148277d2ed89bc2f95cf849e901dd0`. Baseline 388 and built 391 source/data files match; runtime verifies all 11 overlay files plus 54 reviewed rule files. Existing artwork and omitted superseded G1 remain inherited.
- DB archive 539343 bytes, readable with `pg_restore --list`; full restore not exercised. No migration. Only the app was recreated; DB/Redis/mail identities and start times are unchanged; live health is OK.
- Rollback `/srv/migration/2026-11-24/fv01-creator-content/842f57e58/rollback.sh`, syntax checked, not executed.
- QA users 152/153, campaigns 90/91/92, two drafts and all their prepared dependent rows were removed; host/container credentials removed. No real user project/quota changed. [Cleanup](proofs/fv01-creator-content-2026-11-24/qa-cleanup.json), [source/health](proofs/fv01-creator-content-2026-11-24/live-source-health.json), [release](proofs/fv01-creator-content-2026-11-24/delivery.json).

## Remaining scope

Continue FV01 equipment/subchoices/remaining labels, structured findings/API errors, sheet/inventory/progression/shared views and retained low view/status issues. The preview's own expansion reset and rare stale-data failure rehash cost remain low notes. FV04 stays complete; FV05/FV06 stay partial. FV17 closes only by the owner's explicit scope decision, with no claimed technical fix.

The owner requires no new image generation or generative use of Ducky artwork. [Ducky discovery](DADM_DISCOVER_DUCKY_ASSETS_2026-11-24.md) found 77 attachments and preserves 51 graphics-candidate records as 50 immutable originals; source-specific credit, including Anne's QR code, is retained. This source inventory does not publish those files or supply missing rules text. Other retained packets and content inputs remain in the [register](plans/VTT_NEXT_FULL_VERSION_2026-11-23.md).
