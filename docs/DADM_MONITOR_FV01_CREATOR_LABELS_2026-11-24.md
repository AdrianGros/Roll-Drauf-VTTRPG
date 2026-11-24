# Monitor FV01 creator interface labels

Status: this bounded slice is delivered and live verified. **FV01 remains partial; the FV01–FV18 full-version goal remains active.** Retention permanent. Input: [Apply](DADM_APPLY_FV01_CREATOR_LABELS_2026-11-24.md), [implementation](DADM_DEPLOY_FV01_CREATOR_LABELS_2026-11-24.md) and the existing live FV04 release.

## Observed behavior

The creator's explicitly cataloged authored labels follow the selected rules language. Site navigation/settings keep the UI language. Marked creator roots include the page title, titlebar, main, dialog and attribution; the global DOM observer cannot overwrite their locale. Canonical data, quoted source text and user/homebrew text are unchanged. English interface mode visibly explains that some rule names/text remain German.

Rules-language switching preserves the home/import file, draft identity/version/dirty flag, canonical state/data and evaluation. Focus and selection survive a locale-only rebuild. A pending onchange value stays uncommitted during the rebuild and commits normally on actual user blur. The final confirmation subtree retains its campaign choice, pending button/result and server failure message. Authored confirmation labels update in place.

## Verification and evidence

[Eleven unique browser cases pass](proofs/fv01-creator-labels-2026-11-24/verification.json) on the final functional code: three focused state-preservation cases and eight matrix/guided/random cases. All six UI/rules/automatic combinations, scoped vs global markers, unchanged user text matching catalog words, independent unit preference, draft dirty state, focus/selection, actual pending-input commit, campaign/in-flight result, guided creation and random finalization are covered. Tests use throwaway SQLite, not production. The 3773-source catalog freshness check, four changed-JS syntax checks, proof-Python compile checks and diff whitespace check pass. Inherited repository-suite findings remain FV18; no global green result is claimed.

Claude's [initial](proofs/fv01-creator-labels-2026-11-24/review-initial.json) and [reworked](proofs/fv01-creator-labels-2026-11-24/review-reworked.json) read-only source reviews used the existing Pro subscription, no tools or API/provider fallback. The medium finalize concern was corrected. Codex confirmed existing view capture, extended locale-only preservation and tested the replacement-induced browser change plus subsequent real commit. The run history records both test-harness corrections and the genuine implementation correction. Final weak-set/event handling has Codex browser verification; it was added after Claude's reworked review.

Two **authenticated live journeys pass on the deployed image**, using dashboard → Play & Characters → Characters → create hero → guided creation:

- Chromium DM, 1440, night: German website / English creator, then switch to German through the real settings dialog and reload the existing draft.
- Firefox Player, 390, paper: English website / German creator, then switch to English through the real settings dialog and reload the existing draft.

Both retain the exact draft ID/version/state/data/evaluation, the user name `Charaktere`, the independent `ft` preference and site-localized settings button. Neither reports a browser error. The screenshot is after each settings switch/reload; initial mixed-language states are verified by assertions. [Live results](proofs/fv01-creator-labels-2026-11-24/live.json), [desktop](proofs/fv01-creator-labels-2026-11-24/creator-chromium-1440-de-de.png), [narrow](proofs/fv01-creator-labels-2026-11-24/creator-firefox-390-en-en.png). Real OAuth and physical keyboard checks were not exercised.

## Source and operations

- Source `a28afce53838d73abfc2d5602f02f7fb50996e45`, pushed to `origin/fix/feedback-harness-20261123`.
- Image `roll-drauf-vtt-app:fv01-creator-labels-20261124-a28afce53`, identity `sha256:4221b9772405bbc0be4d25ffdacea07047148277d2ed89bc2f95cf849e901dd0`.
- Base source `207c8e9fc`, image `sha256:384ab8657919735f893eaa2dad1e249c5ead23ad03108494778103ec1851146c`. All 334 shipped source/changed-JSON baseline and built-image checks pass; all eight overlay files match committed hashes in the running app. Unchanged artwork and omitted superseded G1 remain inherited from the checked immutable base.
- PostgreSQL backup 539343 bytes; `pg_restore --list` successful, full restore not exercised. No schema/model migration, dependency or permission change. Only the app was recreated; database, Redis and mailservice identity/start times are unchanged. `/health/live` is `ok`.
- Rollback `/srv/migration/2026-11-24/fv01-creator-labels/a28afce53/rollback.sh`, syntax checked, not executed. It restores the previous app image/configuration.
- QA cleanup passed: users 150/151, campaigns 87/88/89, two creator drafts and all their prepared sessions/maps/dependencies were removed. Host/container credentials are removed. No real user project or quota was changed. [Cleanup](proofs/fv01-creator-labels-2026-11-24/qa-cleanup.json), [source/health](proofs/fv01-creator-labels-2026-11-24/live-source-health.json), [release record](proofs/fv01-creator-labels-2026-11-24/delivery.json).

## Residual work and recommendation

Keep FV01 open for reviewed ID mappings and complete English rules presentation, structured validation/API errors, character sheet/inventory/progression/shared views, and old import/conflict/dialog status text after a live switch. The 339-spell candidate inventory still approves no identities. Asynchronous subclass-feature disclosure expansion retains its pre-existing reset on rebuild (low view issue). The narrow screenshot also retains cramped creator mode/help layout; FV02/FV03 already cover that work.

FV04 stays delivered. FV05/FV06 retain their previously documented partial statuses. All other retained packets, including terrain, curved text and the radial palette, remain in the [full-version register](plans/VTT_NEXT_FULL_VERSION_2026-11-23.md). Public AI policy, additional approved content sources and identification of the older 0% control/clipped asset remain explicit inputs; no approval is inferred from silence.

Recommendation: retain this delivered slice and proceed with the reviewed canonical-ID presentation crosswalk and remaining FV01 module coverage. The full-version goal is not complete.
