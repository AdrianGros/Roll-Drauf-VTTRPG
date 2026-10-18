# DAD-M Monitor: Campaign departure recovery

- Status: complete
- Date: 2026-10-13
- Profile: standard
- Phase: Monitor
- Deploy input: `docs/DADM_DEPLOY_CAMPAIGN_DEPARTURE_RECOVERY_2026-10-13.md`

## Input summary

Validate the deployed campaign departure recovery on dev and main, confirm that expected departures no longer pollute the operational error domain, and identify any remaining independent errors.

## Observed results

- Dev and main bot services are active.
- Dev emitted one structured warning with all five campaigns currently requiring roster review.
- After that warning, the next periodic reconciliation did not repeat the warning and did not emit a `member_missing` traceback or aggregate campaign Jail failure.
- Main loaded the new staff management controls and remains connected after the repaired production-specific authorization implementation.
- Production campaign 10 still emits `extra_channel_missing_or_moved`. This confirms the patch did not suppress real structural drift.
- The daily VPS report counts `ERROR` entries; the new departure warning is therefore outside its operational-error count while remaining visible to staff in logs and actionable through the campaign UI.

## Validation evidence

- Dev targeted tests: 9 passed.
- Dev broader campaign tests: 35 passed, 1 known stale test deselected.
- Main targeted tests against production runtime files: 6 passed.
- Runtime compile checks: passed on dev and main.
- Dev log counts since deployment:
  - roster staff-action warnings: 1;
  - `member_missing` text: 1, contained only in that warning;
  - campaign Jail failure entries: 0;
  - aggregate campaign Jail failure entries: 0.
- Main post-start reconciliation at 12:14:26 CEST retained the campaign-10 structural error path.
- `systemctl --failed` returned no failed units.

## Acceptance validation

- Passed: staff-wide campaign management authorization.
- Passed: database-backed departed-player removal/replacement.
- Passed: database-backed departed-DM removal.
- Passed: explicit owner-transfer-or-archive rule.
- Passed: archive remains history-preserving rather than destructive.
- Passed: expected departures are deduplicated warnings, not recurring operational errors.
- Passed: real non-departure drift remains an error.
- Passed: both services recovered and remain active.

## Residual risks

- Medium: production campaign 10 references a missing or moved extra channel. This should be investigated as a separate campaign-structure repair, not normalized as a departure.
- Medium: dev Staff mirror would remove seven members and correctly trips its safety guard. The main-server Staff source/bindings need a separate review before any role removals are allowed.
- Low: five dev campaigns still contain departed active roster rows. The new controls make them recoverable, but staff must decide whether to remove/replace members, transfer ownership, or archive.
- Low: one pre-existing Jail cog shutdown error (`remove_view` missing) remains outside this milestone.
- Low: the live runtime trees contain extensive unrelated work and are not a clean release branch; future consolidation should preserve this deployment evidence.

## Recommendation

Close this milestone. Staff can now resolve the five dev campaign warnings through the dashboard. Open two separate bounded follow-ups for production campaign 10 channel drift and the dev Staff mirror safety guard.

## Artifacts

- This document: retention class `review`.
- Deploy evidence and rollback backups: retention classes `review` and `rollback`.

## Next step

Use `/dashboard` → `Kampagnen`, select a campaign, then `Kampagne verwalten` to remove/replace players or remove additional DMs. Use `Spielleitung festlegen` before removing a departed owner, or archive the campaign when it should end.
