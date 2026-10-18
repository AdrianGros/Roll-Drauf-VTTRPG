# DAD-M Apply: Campaign departure recovery

- Status: complete
- Date: 2026-10-13
- Profile: standard
- Phase: Apply
- Discover input: `docs/DADM_DISCOVER_CAMPAIGN_DEPARTURE_RECOVERY_2026-10-13.md`

## Input summary

The existing system already authorizes campaign editors to manage any campaign, reassign its responsible owner/DM, and archive it. The missing contract is reliable selection and removal of active roster entries whose Discord member has left, plus non-exception handling of that expected state.

## Design summary

Use the database roster as the source of truth for removal choices. Discord guild membership is presentation metadata only. A departed user remains selectable by stored ID even when neither `guild.fetch_member()` nor `bot.fetch_user()` can resolve an account object.

The staff flow is:

1. Select any active campaign in the staff dashboard.
2. Open the existing player/DM removal action.
3. The bot loads active roster rows for that campaign and role.
4. Current guild members show their current display name; departed/global users show the best available global name; deleted or unresolvable accounts show an ID-only fallback marked as no longer on the server.
5. Submission re-checks campaign authorization and the active roster role by ID.
6. Removal uses the existing audited `CampaignMemberService` operation and runs access synchronization.
7. An owner is never directly removable. Staff either assigns a successor with the existing “Spielleitung festlegen” action and then removes the former owner as a DM, or archives the campaign.

## Solution boundary

In scope:

- Database-backed staff removal pickers for active players and DMs, including departed/unresolvable users.
- Reuse of those pickers from the staff campaign dashboard and the campaign management surface.
- Existing staff-wide authorization, owner reassignment, and archive-and-lock behavior.
- Expected-departure classification in Jail/access reconciliation.
- Reconciliation retry when a member rejoins.
- Targeted unit tests and live dev verification before production synchronization.

Out of scope:

- Hard deletion of campaign records or Discord channel history.
- Automatic owner reassignment or automatic campaign archival.
- Automatic removal of every departed roster member without staff confirmation.
- Production campaign 10's missing/moved extra channel.
- Cluster Staff mirror safety-guard remediation.
- Schema or dependency changes.

## Interfaces and contracts

### Roster choices

The campaign management service exposes role-scoped removal choices containing:

- `id`: stored Discord user ID;
- `display_name`: guild name, global name, or deterministic ID fallback;
- `name`: username or `nicht-auf-server` fallback;
- `departed`: whether the user is absent from the campaign guild.

The UI does not require a live `discord.Member` to render or submit a removal.

### Roster mutation

- Player removal delegates to the existing atomic player-roster mutation.
- DM removal delegates to `CampaignMemberService.remove_dm()` by stored user ID.
- Both operations re-check authorization and role at submission time.
- Owner rows are excluded from DM removal and continue to be protected by the service.
- Existing audit records and permission-sync results remain authoritative.

### Reconciliation outcome

- `member_missing` and `campaign_dm_missing` are expected lifecycle outcomes requiring staff action.
- They produce one deduplicated warning containing campaign/user context, not an exception traceback every five minutes.
- The current Jail signature is cached after an expected-departure outcome to avoid repeated Discord fetches and log noise.
- A guild member join invalidates that cache and retries reconciliation.
- Other failures, including missing/moved channels and Discord/API failures, retain operational error behavior and retry semantics.

### Campaign retirement

“Delete campaign” maps to the existing `archive_campaign()` contract: set archived status, lock campaign channels, preserve history, and write audit evidence.

## Acceptance criteria

- A campaign editor can open any active campaign and remove an active player who is no longer in the Discord guild.
- A campaign editor can remove a departed active DM by stored user ID.
- A departed owner cannot be removed directly; the UI preserves the explicit reassign-or-archive path.
- An unresolvable/deleted Discord account is still presented as an ID-only roster choice.
- A stale selection is rejected after a fresh authorization/roster-role check.
- Successful mutations remain audited and attempt permission/voice synchronization.
- `member_missing` and `campaign_dm_missing` do not create ERROR tracebacks in the periodic reconciliation loop.
- A real structural drift such as `extra_channel_missing_or_moved` still raises an operational error.
- Rejoining invalidates expected-departure reconciliation state.
- Targeted campaign tests pass in the live dev tree.
- Dev bot restarts healthy and the next reconciliation interval contains no departure-related ERROR tracebacks.

## Risks and tradeoffs

- Low: warnings are cached until an explicit roster action, owner change, archive, Jail-signature change, or member join. This intentionally avoids repeated fetch/rate-limit churn.
- Low: ID-only entries are less friendly than names but preserve recoverability for deleted accounts.
- Low: the staff dashboard and DM management surface share the same picker/service contract, reducing divergent behavior.
- Low: archive preserves data instead of satisfying a literal hard-delete interpretation. This is the existing safer lifecycle contract.

## Deploy handoff

Patch only the current campaign management/service/dashboard files in `/opt/rolldrauf-bot-dev`, add focused tests, and run those tests plus syntax checks. If dev is healthy through a reconciliation interval, synchronize only the verified changed files to `/opt/rolldrauf-bot-main`, restart main, and validate health/log behavior. Preserve all unrelated dirty-tree changes and record before/after hashes.

## Artifacts

- This document: retention class `review`.

## Next step

Deploy the bounded implementation and capture verification evidence.
