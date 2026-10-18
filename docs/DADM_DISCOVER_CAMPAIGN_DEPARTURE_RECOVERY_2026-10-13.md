# DAD-M Discover: Campaign departure recovery

- Status: complete
- Date: 2026-10-13
- Profile: standard
- Phase: Discover

## Input summary

Players and DMs leaving a Discord server is an expected campaign lifecycle event. It must not create recurring operational errors. Staff need a recovery path for campaigns they do not own: edit the roster, replace or remove players, assign a new responsible DM, and archive the campaign when it should not continue.

## Current-state summary

The deployed campaign system already contains most of the required authority and data operations:

- Campaign editors (`MOD`, `PROJEKTTEAM`, `ADMIN`, `OWNER`, including the cluster-main bridge) may manage campaigns they do not own.
- Staff can add/remove players and DMs, assign a new responsible owner/DM, synchronize permissions, and archive an active campaign.
- Owner reassignment is transactional: the previous owner becomes a DM, the new owner becomes the active `owner`, Discord access is repaired, and an audit event is written.
- Campaign deletion is represented operationally as archive-and-lock, preserving campaign history rather than hard-deleting database and Discord data.
- The newer campaign management roster can remove a departed player by stored Discord ID, but the staff dashboard's direct player/DM removal controls still use Discord `UserSelect`. Discord cannot select a user who is no longer a member of the server.
- There is no equivalent database-backed picker for departed DMs. After an owner is reassigned, the departed former owner remains an active DM and cannot be selected by the current direct removal control.
- The five-minute Jail/access reconciliation loop treats the service result `member_missing` as an exception. Each affected campaign produces a traceback every run, followed by a second aggregate traceback.

## Relevant inventory

- `/opt/rolldrauf-bot-dev/rolldrauf_bot/cogs/campaign.py`
  - Staff campaign selector and actions.
  - Direct remove-player and remove-DM controls currently use `discord.ui.UserSelect`.
  - Staff owner reassignment and archive actions are already exposed.
- `/opt/rolldrauf-bot-dev/rolldrauf_bot/cogs/campaign_management.py`
  - Database-backed player roster UI.
  - Five-minute access/Jail reconciliation loop.
- `/opt/rolldrauf-bot-dev/rolldrauf_bot/services/campaign_management_service.py`
  - Cross-campaign staff authorization.
  - Player roster changes by stored user ID.
  - `sync_jail()` currently raises and logs for every non-OK permission-sync result.
- `/opt/rolldrauf-bot-dev/rolldrauf_bot/services/campaign_owner_service.py`
  - Staff owner/DM reassignment with audit and permission repair.
- `/opt/rolldrauf-bot-dev/rolldrauf_bot/services/campaign_member_service.py`
  - Role-aware member removal by user ID.
  - Returns `member_missing` when an active roster entry no longer resolves to a guild member.
- `/opt/rolldrauf-bot-dev/rolldrauf_bot/services/campaign_service.py`
  - Archive-and-lock lifecycle operation.
- `/opt/rolldrauf-bot-dev/rolldrauf_bot/repositories/campaign_management_repo.py`
  - Atomic roster mutations and role protection.
- `/opt/rolldrauf-bot-dev/tests/test_campaign_access_feedback.py`
- `/opt/rolldrauf-bot-dev/tests/test_campaign_management.py`
- `/opt/rolldrauf-bot-dev/tests/test_campaign_cog_permissions.py`

## Evidence

- Live dev logs repeatedly report `RuntimeError: Permission sync: member_missing` for campaigns 24, 25, 26, 27, and 29 every five minutes.
- The dev sandbox roster confirms active stored members on all five campaigns. Campaigns 25 and 29 share an owner who is also an active player in campaign 24, demonstrating that the same departure can block several campaign reconciliations.
- `CampaignManagementService.player_choices()` already attempts a global-user fallback for departed players, while the staff dashboard direct actions do not.
- Production campaign 10 has a different problem (`extra_channel_missing_or_moved`). That remains a real configuration-drift error and is outside this departure-specific change.
- The Staff mirror safety-guard error is also independent and remains outside this campaign departure boundary.

## Dependencies and constraints

- The deployed campaign implementation is newer than `/home/admin/projects/rolldrauf-bot-dev-work` and currently exists as a large, dirty live tree in `/opt/rolldrauf-bot-dev`; unrelated changes must be preserved exactly.
- `/opt/rolldrauf-bot-main` is a non-Git deployed copy. Dev verification must precede any production synchronization.
- Discord component limits require reusing the existing compact management/action surfaces.
- No schema change is required: campaign membership status, role, owner, and audit storage already exist.

## Risks and assumptions

- Medium, resolved by boundary: editing the wrong older workspace would discard deployed campaign behavior. Work must patch only the current deployed campaign files and preserve their surrounding changes.
- Medium, resolved by lifecycle choice: hard deletion would destroy history and related records. “Delete campaign” is interpreted as the existing audited archive-and-lock operation.
- Low: a deleted Discord account may not resolve through the global user API. The roster UI therefore needs an ID-only fallback, not just `fetch_user()`.
- Low: an owner cannot be removed directly. Staff must either assign a successor first, then remove the former owner as a DM, or archive the campaign.
- Low: a member can rejoin. Expected-departure reconciliation should be invalidated on join so access can be retried without waiting for an unrelated Jail-role change.

## Open questions

None blocking. The requested behavior maps to existing authorization, archive, owner-transfer, and roster contracts.

## Next step

Apply should define one database-backed staff roster picker for departed players and DMs, wire the staff dashboard to it, preserve owner-transfer/archive semantics, and classify `member_missing` as a deduplicated staff-action warning rather than an operational exception. Deploy should verify in dev before production synchronization.

## Artifacts

- This document: retention class `review`.
