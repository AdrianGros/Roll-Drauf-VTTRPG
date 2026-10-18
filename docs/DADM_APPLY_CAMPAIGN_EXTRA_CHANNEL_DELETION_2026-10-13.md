# DAD-M Apply: Campaign extra-channel deletion

- Status: complete
- Date: 2026-10-13
- Profile: standard
- Phase: Apply
- Discover input: `docs/DADM_DISCOVER_CAMPAIGN_EXTRA_CHANNEL_DELETION_2026-10-13.md`

## Input summary

Optional campaign channels may be deleted by a DM at their discretion. The bot must remove the corresponding optional-channel metadata and continue normally rather than escalating the deletion as an error.

## Design summary

Make optional-channel deletion an idempotent campaign lifecycle operation:

1. When Discord emits a guild-channel deletion event, delete any matching `campaign_extra_channel` row and record only an informational log.
2. When permission reconciliation finds an optional channel absent from the guild cache, delete the stale row and continue reconciling the campaign. This covers deletions missed while the bot was offline.
3. When channel creation encounters an old bound reservation whose channel is absent from a fresh guild-channel list, discard the stale reservation and reserve/create normally.
4. If a stored optional channel still exists but is outside its campaign category, return a distinct `extra_channel_moved` failure. Moving a channel can change its effective access boundary and therefore remains operationally significant.

## Solution boundary

In scope:

- Optional rows in `campaign_extra_channel` only.
- Event-driven, reconciliation, and creation-time stale-record cleanup.
- Informational lifecycle logging.
- Targeted tests, dev rollout, production synchronization, and live cleanup of campaign 10 through normal reconciliation.

Out of scope:

- Required campaign categories/channels, private player-history channels, session channels, or guild configuration channels.
- Automatic deletion of any Discord channel.
- Silently accepting an existing optional channel moved outside its campaign category.
- Schema or dependency changes.

## Interfaces and data contracts

- `CampaignManagementRepository.forget_deleted_extra_channel(guild_id, channel_id)` deletes and returns matching optional-channel records. Repeated calls return no records and remain safe.
- `CampaignMemberService.sync_permissions()` treats a missing extra channel as successful cleanup and continues; an existing channel with the wrong `category_id` returns `reason=extra_channel_moved` with the affected channel ID.
- `CampaignManagementCog.on_guild_channel_delete()` invokes the repository cleanup for every guild-channel deletion; non-extra channels produce no mutation.
- `CampaignManagementService.create_channel()` clears only a stale bound extra-channel reservation proven absent from a fresh guild channel listing.

## Acceptance criteria

- Deleting an optional campaign channel while the bot is online removes its database record without an ERROR log.
- A missed/offline deletion is cleaned during permission reconciliation without making reconciliation fail.
- The same optional channel name can be created again after its old Discord channel was deleted.
- A moved-but-existing channel still fails reconciliation as `extra_channel_moved`.
- Required campaign channel deletion behavior is unchanged.
- Targeted tests and syntax checks pass in dev before production rollout.
- Both services restart healthy.
- Campaign 10 no longer produces recurring extra-channel errors, and its stale `poisons-pompöse-papawitze` row is absent after reconciliation.

## Risks and tradeoffs

- Low: event delivery is not guaranteed while offline; reconciliation and creation-time recovery provide independent fallback paths.
- Low: cleanup removes only optional metadata for an already absent Discord object and is idempotent.
- Medium, explicitly retained: moved channels continue to alert because their access context may be unsafe.

## Artifacts

- This document: retention class `review`.

## Deploy handoff

Patch the repository, campaign permission synchronization, campaign management service, listener, and focused tests in the current dev tree. Verify there, then copy only the verified changes to main with backups and restart both services. Preserve unrelated changes.

## Next step

Deploy the bounded lifecycle cleanup and capture evidence.
