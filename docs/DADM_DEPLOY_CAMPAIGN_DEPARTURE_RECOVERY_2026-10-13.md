# DAD-M Deploy: Campaign departure recovery

- Status: complete
- Date: 2026-10-13
- Profile: standard
- Phase: Deploy
- Apply input: `docs/DADM_APPLY_CAMPAIGN_DEPARTURE_RECOVERY_2026-10-13.md`

## Input summary

Implement database-backed staff recovery for departed campaign players/DMs, preserve explicit owner-transfer/archive semantics, and stop expected departures from producing recurring reconciliation exceptions.

## Implementation summary

- Added a normalized roster-choice model whose identity is the stored Discord user ID.
- Active roster members who have left the guild remain selectable through a global-name or deterministic ID-only fallback.
- Bot rows remain filtered even when a bot is absent from the guild cache.
- Added a database-backed departed-DM picker and confirmed removal flow.
- Player removal/replacement and DM removal re-check authorization and current roster role before mutation.
- Exposed the full campaign management surface from the staff campaign action menu as `Kampagne verwalten`.
- Routed the direct staff remove-player and remove-DM actions to the database-backed pickers instead of Discord `UserSelect`.
- Expanded main-server campaign management authorization to `MOD`, `PROJEKTTEAM`, `ADMIN`, and `OWNER` through its native permission-tier repository.
- Classified `member_missing` and `campaign_dm_missing` as deduplicated staff-action warnings in periodic Jail/access reconciliation.
- Added member-join invalidation so a returning member causes access reconciliation to retry.
- Kept every other reconciliation failure, including missing/moved campaign channels, on the operational error path.

## Files changed

Dev runtime:

- `/opt/rolldrauf-bot-dev/rolldrauf_bot/services/campaign_management_service.py`
- `/opt/rolldrauf-bot-dev/rolldrauf_bot/cogs/campaign_management.py`
- `/opt/rolldrauf-bot-dev/rolldrauf_bot/cogs/campaign.py`
- `/opt/rolldrauf-bot-dev/tests/test_campaign_access_feedback.py`
- `/opt/rolldrauf-bot-dev/tests/test_campaign_management.py`
- `/opt/rolldrauf-bot-dev/tests/test_campaign_cog_permissions.py`

Main runtime:

- `/opt/rolldrauf-bot-main/rolldrauf_bot/services/campaign_management_service.py`
- `/opt/rolldrauf-bot-main/rolldrauf_bot/cogs/campaign_management.py`
- `/opt/rolldrauf-bot-main/rolldrauf_bot/cogs/campaign.py`

Review artifacts:

- `docs/DADM_DISCOVER_CAMPAIGN_DEPARTURE_RECOVERY_2026-10-13.md`
- `docs/DADM_APPLY_CAMPAIGN_DEPARTURE_RECOVERY_2026-10-13.md`
- This document.

## Rollback points

Main pre-change backups:

- `/opt/rolldrauf-bot-main/rolldrauf_bot/services/campaign_management_service.py.bak_20261013_departure_recovery`
- `/opt/rolldrauf-bot-main/rolldrauf_bot/cogs/campaign_management.py.bak_20261013_departure_recovery`
- `/opt/rolldrauf-bot-main/rolldrauf_bot/cogs/campaign.py.bak_20261013_departure_recovery`

Their recorded SHA-256 hashes are respectively:

- `23b1b3cb5479416f1579ed59012c13d3ddf27125c375450783c7024246113f5c`
- `2f5febafa221df4c6abc3e553ac4d1b5a70f839330d3fdc456ca1ab6ea498a06`
- `7935b377b83fa1e6a3d20759b3759e05a25cf96e8f58ea05973d074877575003`

## Verification run

Dev:

- Python compile check for all three runtime files: passed.
- `git diff --check` for runtime and test files: passed.
- Focused behavior suite: `9 passed`.
- Broader campaign suite excluding one known stale panel-recovery test: `35 passed, 1 deselected`.
- `rolldrauf-bot-dev.service` restarted at 12:04:01 CEST, active, zero restarts.
- First reconciliation at 12:04:54 produced one warning listing campaigns 24, 25, 26, 27, and 29 with the missing user IDs.
- The next five-minute cycle produced no repeated roster warning, no `member_missing` traceback, and no aggregate campaign Jail traceback.

Main:

- Python compile check for all three runtime files: passed.
- Six targeted tests executed against the main runtime files using the dev test environment: passed.
- Main initially failed once because a dev-only authorization helper was absent. The patch was reworked to use main's existing permission-tier repository, without adding a dependency.
- `rolldrauf-bot-main.service` then started at 12:13:12 CEST, loaded all cogs, synchronized 18 global commands, started the VTT verifier, connected to Discord, and remains active.
- No `member_missing`, roster-warning, module-import, or runtime-failure entries occurred after the successful start.

## Proofs

- Dev service: active, PID `1206191`, `NRestarts=0` after deployment.
- Main service: active, PID `1208071`; `NRestarts=1` records the caught and repaired promotion mismatch.
- Dev departure output is now a single `WARNING rolldrauf_bot.services.campaign_management_service: Campaign roster needs staff action ...` rather than repeated ERROR tracebacks.
- Current runtime SHA-256 values are recorded in the command transcript; dev/main differ only where their pre-existing deployments differ.

## Acceptance checklist

- [x] Staff can manage campaigns they do not own.
- [x] Departed players remain selectable and removable by stored ID.
- [x] Departed DMs remain selectable and removable by stored ID.
- [x] Deleted/unresolvable accounts have an ID-only fallback.
- [x] Player replacement remains available from the exposed campaign management view.
- [x] Owner removal remains blocked pending explicit successor assignment or archive.
- [x] Existing owner assignment remains available.
- [x] Existing audited archive-and-lock operation remains available.
- [x] Expected departures no longer produce recurring reconciliation exceptions.
- [x] Member joins invalidate the expected-departure cache.
- [x] Structural drift still follows the error path.
- [x] Dev and main services are active after deployment.

## Risks and assumptions

- Low: the live bot trees remain broadly dirty from earlier campaign work; only the named files/hunks were changed and unrelated work was preserved.
- Low: the one pre-existing stale test expects `ensure_panel()` to restore a panel although that deployed method intentionally returns immediately. It was excluded rather than changing unrelated behavior.
- Low: staff still make the business decision to remove, replace, reassign, or archive. No automatic destructive cleanup was introduced.
- Medium residual, outside this deployment: production campaign 10 still references an extra channel that is missing or moved.
- Medium residual, outside this deployment: the dev cluster Staff mirror safety guard still detects seven potential removals and refuses to apply them.
- Low residual, outside this deployment: Jail cog shutdown calls a missing `remove_view` method and logs during service shutdown; normal startup is unaffected.

## Artifacts

- Runtime code and tests: retention class `source`.
- Main backups: retention class `rollback`.
- DAD-M documents: retention class `review`.

## Next step

Monitor both bots, confirm no departure-related ERROR regression, and leave the five dev roster warnings for staff to resolve through the new UI. Investigate campaign 10 channel drift and the Staff mirror safety guard as separate bounded tasks.
