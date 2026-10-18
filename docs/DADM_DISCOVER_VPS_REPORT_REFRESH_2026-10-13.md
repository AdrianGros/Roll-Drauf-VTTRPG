# DAD-M Discover — VPS Daily Report Refresh

- **status:** complete
- **date:** 2026-10-13
- **profile:** standard

## Input summary

Refresh the stale VPS daily report and investigate the conditions it flags.
Discovery was read-only: no service, database, Discord, report-state, or storage
content was changed.

## Current-state summary

The timer ran successfully at 08:00 CEST and Discord accepted the embed with
HTTP 204. The report is nevertheless unreliable on the migrated Ubuntu host:

- `vps-daily-report.service` runs as `admin`, which is not a member of `adm` or
  `systemd-journal`; its journal queries therefore return no bot records.
- The report consequently claimed zero bot errors although the same 24-hour
  window contained 2,595 explicit `ERROR` records across the main and dev bot.
- The critical reference-copy tile still checks the retired
  `/opt/rolldrauf-bot-prod` checkout via `sudo -u botadmin`. The report user
  cannot run that sudo command non-interactively, so every affected run emits a
  PAM/sudo error and marks an obsolete check critical.
- The hard-coded service/resource inventory predates the VPS migration. It
  omits both systemd Minecraft servers, `codex-remote`, `goblin-delve2-web`, and
  the renamed PostgreSQL 18 unit.
- Error counting truncates each service to ten matching lines before counting
  and mixes traceback lines with events. Delivery failure would still advance
  the report marker and commit cursors.

## Relevant inventory

- Report script: `/opt/vps-daily-report/scripts/vps_daily_report.sh`
- Embed sender: `/opt/vps-daily-report/scripts/build_and_send_embed.py`
- Unit/timer: `/etc/systemd/system/vps-daily-report.{service,timer}`
- State: `/home/admin/.local/state/vps-daily-report/`
- Current host: `vmd208406`; no failed systemd units were present.
- Core bot, VTT, Goblin Delve, DADM KB, Codex, Minecraft, Docker, PostgreSQL,
  and nginx services were active with zero recorded restarts after cutover.
- Both inspected backup jobs completed successfully on 2026-10-13.
- No kernel OOM kill was found after target activation.

## Flagged-condition investigation

### Disk usage — medium, capacity follow-up

The root filesystem is 70% used with about 238 GiB available. Approximately
342 GiB is retained migration material: an extracted source tree, a 109.5 GB
archive, and a second extracted package. Docker images use about 90 GB, of
which Docker reports about 64 GB reclaimable. `/opt/backups` uses about 56 GB.
There is no immediate space incident, but retention/cleanup requires a separate
destructive-action decision and is outside this report repair.

### Recurring bot errors — medium, production-data decision required

- Main campaign `Ein letzter Funke Hoffnung` (ID 10) is active and retries
  every five minutes because at least one recorded extra channel is missing or
  has moved outside the expected campaign category.
- Dev campaigns 24, 25, 26, 27, and 29 retry every five minutes because one or
  more recorded active members are absent from the Discord guild.
- The dev staff mirror refuses a change that would remove seven members. This
  is a working safety guard, but it is logged as an error every five minutes.
- These recurring conditions were documented before the VPS cutover and are
  not migration regressions. Repair requires confirming the intended Discord
  campaign/member state; this task will not mutate it implicitly.

### Isolated errors — low

- One main verify-schedule interaction expired before the bot replied
  (`Unknown interaction`); the fallback reply necessarily failed for the same
  expired interaction.
- One dev dashboard recovery call received a transient Discord-side HTTP 503.
- Codex logged two model-list refresh timeouts; the service stayed active.
- Minecraft authentication outages/vanilla-client rejections, SSH pre-auth
  resets, and one Docker DNS timeout were external/client noise, not service
  failures in the inspected window.

## Dependencies and constraints

- Preserve the explicit policy that Palworld is omitted from the report.
- Do not expose the webhook or deployment secrets.
- Do not clean migration archives, Docker images, or backups in this task.
- Do not alter campaign/member records without an operator decision.
- A manual final report run will send a new Discord message; dry-run validation
  must precede it.

## Risks and assumptions

- **high:** A green error tile is currently false because journal access is
  missing.
- **medium:** Repeated campaign reconciliation errors represent unresolved live
  data/Discord drift, but service availability is not affected.
- **medium:** Disk usage is real; changing alert thresholds must retain an
  absolute-free-space guard.
- **low:** Adding report-only service checks increases embed size but remains
  within Discord's field limit.

## Open questions

- Whether to archive/repair campaign 10 and the five dev campaigns is an
  operator decision outside the report refresh.
- Migration/archive retention and Docker image cleanup need an explicit,
  separately reviewed deletion scope.

## Artifacts

- This document — retention class: `operations_discovery`
- Existing local `last_report.txt` and `last_embed.json` — retention class:
  `report_runtime_state`

## Next step

Proceed to Apply with a bounded design: grant only the report service journal
read access, remove the retired checkout check, aggregate explicit bot error
events without truncating before counting, refresh service coverage, make
delivery state transactional, use percentage plus absolute disk headroom, and
prove the result with a no-send run before one live refresh.
