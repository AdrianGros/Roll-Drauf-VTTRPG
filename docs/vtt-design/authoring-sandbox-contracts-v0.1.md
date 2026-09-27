# Authoring-to-sandbox design contracts v0.1

**Status:** specified design target, 27 September 2026. **Scope/source:** [design v0.1](authoring-sandbox-design-v0.1.md), bounded by the [active engine contract](../creation-engine/active-contract.json). **Execution status:** [test backlog](test-backlog-2026-09-29.md). These IDs do not replace engine T01–T56. All new design acceptance remains unverified; named existing tests are inherited evidence for their narrower assertions.

Each contract applies to authenticated, currently authorized authors unless a denied state is specified. The implementation owner role is VTT integration; acceptance owner and study lead roles follow the G1 program. `VD-T` identifies technical backlog cases and `VD-H` human cases, deferred until 29 September.

## VD-C01 — Entry, orientation and return

**Source:** overview IA, shared navigation, design §3. **Test:** VD-T02; VD-H01, VD-H05.

Given an eligible account in an enabled test environment, the dashboard offers one real content-authoring entry while retaining session/preparation priority. Opening it reaches the existing editor route, shows local item-authoring orientation and provides real overview/campaign/character navigation. No unrelated chapter is marked current. An empty workspace offers explicit creation; a mere visit creates nothing. Leaving with dirty input or a pending outcome obeys VD-C07. An account without authoring availability sees no misleading active entry and cannot bypass server checks by visiting the URL.

## VD-C02 — Shared visual identity

**Source:** book brief and `theme.css`; design §4. **Test:** VD-T03.

The editor loads shared theme assets before scoped feature styles and uses the selected paper/ink/rubrication/field/status tokens. Prose and tool controls use their shared font roles. No new feature-specific literal palette or global control selectors create a competing theme. Verify computed styling as well as source use; token reuse alone is insufficient. Review normal, invalid, focused, disabled, stale and unknown-outcome states. Preserve the existing browser icon contract.

## VD-C03 — Responsive reading and control order

**Source:** book page model; design §4. **Test:** VD-T04; VD-H06.

Below 1200 CSS px, questions and preview follow a single reading column. At wider widths two tool columns may be used without narrowing controls below usability. At 320, 390, 1199, 1200, 1201 and 1280 CSS px, and at 200% browser zoom on the desktop case, actions, labels and error recovery remain reachable without main-page horizontal scrolling or overlay obstruction. Advanced JSON may scroll within a labelled region. Wider windows must not unexpectedly reduce the usable authoring area. DOM and keyboard order remain meaningful when columns collapse.

## VD-C04 — One draft across modes and locales

**Source:** engine §15, T32; design §§3/6. **Test:** VD-T06; VD-H05, VD-H07.

Given saved answers, switch Guided → Advanced → Structured → Guided and de → en → fr → de. Draft identity, version, canonical answers and question identities remain unchanged by these reads. Prompts, controls, validation/status copy and document language match the selected editor locale; authored prose is not translated automatically. Switching while an input is dirty cannot discard it silently. A compiler/registry upgrade requires reviewed migration rather than locale-driven reinterpretation.

## VD-C05 — Explicit intent and preset review

**Source:** engine §15, T31; design §3. **Test:** VD-T06; VD-H01, VD-H02, VD-H04.

For a new flame item, behavior is an explicit choice. Harmless flames never acquire damage; damage, timing, duration, cost and recovery are not guessed from prose. Unanswered creative values remain unresolved. Optional questions may be skipped; required questions may not be silently skipped. Preset preview is read-only and displays its supplied values before explicit application. Apply uses that exact preset version/preview digest and the displayed locale. No preset is selected for a study participant by the moderator.

## VD-C06 — Invalidation and retained history

**Source:** engine §15, T31–T32; design §5. **Test:** VD-T07; VD-H05.

After changing an earlier answer, invalid descendants no longer affect the active draft; the UI identifies permitted affected questions and the required next step. Prior answers/history remain inspectable. Re-answering an unchanged value does not invalidate valid descendants. Revert creates a new version and preserves prior history/revisions. A Guided dead end offers authorized diagnostics and Structured recovery, not an endless question cycle.

## VD-C07 — Save, conflict and uncertain response

**Source:** engine command/version/retry semantics; design §5. **Test:** VD-T08; VD-H05.

Dirty input survives blocked view changes and failed saves. In-app navigation offers explicit save/discard handling; while an outcome is unknown it cannot silently abandon the command or generate a replacement. One in-flight save has one key. If its response is lost, show “result not confirmed”, retain the envelope and retry with the identical key/payload. A version conflict preserves local input for inspection and requires refresh/reconciliation before a new save. On success show the confirmed saved version. Browser unload warns about dirty/pending work. Hard tab loss does not trigger silent new-key replay; offline durability is not claimed.

## VD-C08 — Honest quality and immutable revisions

**Source:** engine §§4/15; design §§3/6. **Test:** VD-T09; VD-H01, VD-H04.

Given an incomplete draft, show unresolved values and the selected quality's permitted blockers; do not substitute zero or conceal mandatory costs. The server validates `CommitDraftRevision`; a disabled button is not enforcement. Saving a revision is visibly distinct from saving an answer or publishing. Later draft edits/reverts do not change the revision. Manual hit/recovery adjudication prevents an automation-complete claim in this native profile. No UI implies that a private revision is deployed to a campaign.

## VD-C09 — Exact sandbox and copy identity

**Source:** engine lock/occurrence identity, T49; native host. **Test:** VD-T10; VD-H01, VD-H05.

Sandbox creation requires explicit revision selection and resolves an exact lock. Instantiation only accepts its locked revisions. Two copies of the same revision display distinct identities/resources; selecting one changes only that copy. A held copy starts unequipped and cannot bypass equip requirements. Holder/target statistics come from supplied imported fixtures. Changing the draft never silently updates an existing sandbox; new content needs a new explicit sandbox selection.

## VD-C10 — Explicit mechanical decisions and manual boundaries

**Source:** T09–T12, T49–T50, T54; native profile. **Test:** VD-T10, VD-T11; VD-H01, VD-H05.

Harmless activation spends only the authored charge cost and never rolls damage. A confirmed hit is labelled a human attestation on the chosen target. Optional flame acceptance commits the authored cost, recorded roll and HP change atomically on that same target; decline or timely timeout preserves the hit without those changes. Recovery confirms the specified event and affects only the selected copy. A clock anomaly/suspended child is not rendered as an ordinary timeout/success. Only eligible responders can answer; only authorized operators can manually finish a suspended action, with explicit outcome/reason and a visible manual label. The UI never calls the server-only damage child directly.

## VD-C11 — Authorized rendering and denied states

**Source:** engine §14, T22–T25/T47; design §§1/6. **Test:** VD-T12; VD-H05.

Each list, preview, diagnostic, receipt/result and sandbox display uses the currently authorized projection. A viewer cannot discover hidden names, identifiers, counts or source hashes through disabled controls, errors or cached content. Unknown and inaccessible object references have the same public unavailable representation. Revocation removes inaccessible content and disables further mutation; stale responses cannot restore it. View As cannot mutate authoring state. Hiding/disabling a control never substitutes for server authorization. Keep untrusted prose as safe content, not executable markup.

## VD-C12 — Keyboard, labels and focus

**Source:** engine §19; design §4. **Test:** VD-T05, VD-T13; VD-H06.

Complete the in-scope journey with Tab/Shift+Tab, Enter/Space and standard controls without a mouse. Every control has an accessible name, visible focus and meaningful grouping. After saving, focus moves to the next applicable question or stable completion heading; switching modes/locales does not drop focus into the document body. After validation errors, the first relevant invalid field/error link is reachable and the input is retained. Global arrow keys do not override text/select editing. Disclosure/modal behavior, if used, has a predictable open/close focus return and no trap.

## VD-C13 — Understandable state and error feedback

**Source:** engine §19; design §5. **Test:** VD-T08, VD-T13; VD-H05, VD-H07.

Loading, empty, dirty, saving, saved, conflict, unknown outcome, quality-blocked and suspended states are distinguishable in text. A changed server result is announced without repeated announcement on every redraw. Errors identify the permitted cause, affected control and useful next action; color alone never conveys the distinction. Verify the feedback at the tested narrow widths and zoom, not only via text presence. Public copy avoids raw internal exceptions and does not confuse saving a draft with publishing/automation.

## VD-C14 — Motion is optional

**Source:** book brief; design §4. **Test:** VD-T14; VD-H06.

Navigation works with reduced motion and without a transition API. Decorative page turns are absent with reduced motion. An answer save, locale change, error or sandbox outcome does not trigger a chapter turn or delay access to controls/data. No additional animation/navigation engine or global arrow-key binding is introduced by the editor integration.

## VD-C15 — Capability and rollout boundary

**Source:** G1 authorization and runtime integration; design §8. **Test:** VD-T02, VD-T12, VD-T15.

With engine flags off, the ordinary VTT remains usable and offers no active authoring entry. With authoring enabled but runtime disabled, permitted draft work can proceed and sandbox execution is clearly unavailable. A missing native registration prevents an executable quality claim. Direct endpoints still enforce current account/permission/feature state. No fixture-only command becomes a production campaign deployment button. Reverting UI assets leaves server content, receipts and execution locks intact.

## VD-C16 — Evidence and human-study integrity

**Source:** engine §22; user scheduling instruction. **Test:** VD-T01, VD-T16; VD-H01, VD-H02, VD-H03, VD-H04, VD-H05, VD-H06, VD-H07.

Every run identifies source/build, flags, fixtures, browser/device/viewport/locale, scenario, expected/actual result and evidence location. Keep inherited automated results separate from new executions and human observations. Before 29 September no user session is conducted or invented. Tuesday's scheduled WP8 test feeds WP9; attendance, a meeting date or passing automation does not close the milestone. The four T45 tasks, required participant count and success/default/confusion criteria remain visible; unavailable tasks are blocked/incomplete, never silently dropped from the denominator or replaced by a scripted demo.
