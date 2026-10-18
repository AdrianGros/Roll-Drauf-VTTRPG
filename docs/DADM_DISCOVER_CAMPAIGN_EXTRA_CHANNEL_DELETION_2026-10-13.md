# DAD-M Discover: Campaign extra-channel deletion

- Status: complete
- Date: 2026-10-13
- Profile: standard
- Phase: Discover

## Input summary

Campaign DMs intentionally delete optional campaign channels as part of normal campaign management. Those deletions must not create recurring operational errors.

## Current-state summary

Campaign 10 (`Ein letzter Funke Hoffnung`) contains four stored extra-channel records. Three still resolve inside the campaign category. The stored channel `poisons-pompöse-papawitze` (`1525904276440744189`) no longer exists; Discord returns `404 / 10003 Unknown Channel`.

Permission reconciliation currently combines a missing optional channel and a moved optional channel into `extra_channel_missing_or_moved`. That result is treated as an operational failure and retried every five minutes. The missing database record also reserves the old channel name, so recreating a channel with the same name can be blocked.

## Relevant inventory

- `/opt/rolldrauf-bot-dev/rolldrauf_bot/services/campaign_member_service.py`: reconciles extra-channel permissions and currently fails on missing or moved channels.
- `/opt/rolldrauf-bot-dev/rolldrauf_bot/repositories/campaign_management_repo.py`: stores, reserves, binds, and renames `campaign_extra_channel` rows; it has no operation for forgetting a previously bound channel.
- `/opt/rolldrauf-bot-dev/rolldrauf_bot/cogs/campaign_management.py`: owns campaign lifecycle listeners and periodic reconciliation.
- `/opt/rolldrauf-bot-dev/rolldrauf_bot/services/campaign_management_service.py`: creates optional channels and currently treats a stale bound reservation as an unresolved creation attempt.
- `/opt/rolldrauf-bot-dev/tests/test_campaign_management.py`: targeted campaign management and permission-sync coverage.

## Dependencies and constraints

- Discord emits `on_guild_channel_delete` while the bot is online, but deletion can occur while it is offline; a reconciliation fallback is required.
- An existing channel moved outside its campaign category is different from a deleted optional channel because its permissions may no longer match the destination category.
- No schema or dependency change is required.
- The live dev and main trees contain unrelated work that must be preserved.

## Risks and assumptions

- Low: deleting a stale database row is safe only after Discord has reported the channel deletion or the guild cache/fresh channel list confirms the channel is absent.
- Medium, retained as an error: an existing extra channel outside the campaign category may expose content or permissions incorrectly and must not be silently forgotten.
- Low: a missed delete event may temporarily leave the old name reserved; periodic permission reconciliation and creation-time recovery can close that gap.

## Open questions

None blocking. The user explicitly confirmed that DM deletion of optional campaign channels is normal behavior.

## Artifacts

- This document: retention class `review`.

## Next step

Apply should define event-driven and fallback cleanup of deleted optional-channel records while preserving moved-channel detection as a real operational failure.
