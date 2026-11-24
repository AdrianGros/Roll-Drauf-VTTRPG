# Apply FV01 creator interface labels

Status: implementation handoff, permanent. Parent: [full FV01 design](DADM_APPLY_FV01_CHARACTER_LANGUAGE_2026-11-23.md). Input: live source `207c8e9fc`, clean worktree `93e918b85`, existing UI catalog and creator source inspection. This is a bounded delivery within FV01, not completion of that packet.

## Contract

Implement the parent's module-scoped translator first. Explicit creator roots (page title, titlebar, main, dialog and attribution) use the resolved rules language; the surrounding ribbon and settings remain in the UI language. Only existing, explicitly cataloged repository-authored labels are translated. Do not inspect or translate arbitrary DOM text, canonical creator-data, quoted rules, draft names, descriptions or homebrew.

The shared translator exposes a rules module using the existing catalog. Global translation skips marked rules roots; its existing DOM observer routes newly inserted marked labels to the proper translator. Every rules root has the resolved `lang`. Creator render calls use the module translator, including constant label dictionaries resolved lazily. Shared subclass previews receive an optional translator from the creator; other callers keep their existing behavior.

Changing only the rules preference re-renders the current creator view from its existing state, without saving, changing draft identity/version/dirty status, navigating, or changing mechanics. Preserve stable IDs, input focus/selection and view where available. Asynchronous subclass feature disclosures retain their pre-existing reset behavior on a rebuild; that low-severity view issue remains in FV01 follow-up, outside the synchronous-details acceptance of this slice. Do not rebuild the draft home during a live preference change: retain explicit source/parameter references for its authored text nodes and translate them in place, preserving a selected import file. Translate static review labels through explicit catalog keys. Preserve current controls’ uncommitted values and synchronously rendered details expansion by position during this locale-only rebuild (the canonical data/state and field structure do not change). Suppress only the artificial change event caused by replacing the focused control during that rebuild; subsequent real user commits keep their normal handler. Track a pending input in a view-only WeakSet, restore that flag on the replacement input, and dispatch its ordinary change on actual blur if the browser has no native pending event after replacement. The capture listener clears the flag so a native change is never duplicated. Retain the exact finalization subtree and its explicitly authored text-node references, so campaign selection, an in-flight request and its eventual result remain connected. This addresses the medium review finding before Deploy; the existing view-capture code already preserves stable-ID focus/selection. Track save/status authored source separately so lifecycle text can be refreshed without treating server or user strings as catalog messages.

## Boundary and residual work

The full English rules presentation, canonical ID crosswalk, structured validation localization and character editor remain outstanding. The creator shows an English notice while English interface labels are selected, explaining that some rule names/text remain German. This makes the partial language support visible. Existing German attribution remains factually correct in both interface languages. No API, permission, schema, dependency or stored-preference format change.

## Acceptance and handoff

- Browser matrix DE/DE, DE/EN, EN/DE, EN/EN and both automatic settings verifies site navigation vs creator static/dynamic labels and live switching.
- Existing names matching catalog text, free text, canonical data and state are unchanged; switching preserves draft ID/version/dirty state, focused input and selected file.
- Mutation handling cannot overwrite a marked module label with the global locale. A non-creator page continues to follow its UI locale.
- Existing guided creation and random finalization still work; focused browser/catalog/JS checks pass.
- Commit/push; deploy a guarded committed overlay on the current image, back up the database, record rollback and unchanged services; verify normal dashboard → Characters → creator journeys as DM and Player, then remove isolated QA data.

Risks: low shared-translator regression, addressed by mixed-locale and unscoped-node assertions. Full rules coverage is a retained FV01 limitation, not accepted as packet completion. Next phase: Deploy this contract, then Monitor; no pending owner policy decision affects this slice.
