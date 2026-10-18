# DAD-M Monitor — VPS Daily Report Refresh

- **status:** complete
- **date:** 2026-10-13
- **profile:** standard
- **input:** `docs/DADM_DEPLOY_VPS_REPORT_REFRESH_2026-10-13.md`

## Observed results

The refreshed Discord report was accepted and its content matches live host
state:

- VTT: 4/4 components healthy
- Goblin Delve: 3/3 components healthy
- Game servers: 3/3 healthy (Palworld remains intentionally omitted)
- Platform services: 5/5 active
- Failed systemd units: 0
- Disk: 70% used, 238 GiB free, good under the approved combined threshold
- Memory: 25/47 GiB used, about 21 GiB available
- Kernel OOM kills after cutover: 0
- Journal access: available
- Bot errors in the 08:00–11:34 interval: 387 records / 10 signatures

The timer remains enabled and active for 2026-10-14 08:00 CEST. The final
oneshot result is `success` / exit status 0. No sudo, PAM, report-delivery, or
other report-unit error appeared after the refresh.

## Validation evidence

- Discord webhook response: HTTP 204
- Production marker advanced after the successful response
- Post-send `systemctl --failed`: zero units
- Post-send kernel journal: zero OOM-kill records since target activation
- Post-send report-unit error scan: no matches
- Live embed values were read back from
  `/home/admin/.local/state/vps-daily-report/last_embed.json` and compared with
  live `systemctl`, `df`, `free`, and kernel-journal results
- Recurring dev reconciliation errors continued after the refreshed marker,
  confirming that the report now observes the real unresolved condition rather
  than hiding it

## Acceptance result

All report-refresh acceptance criteria passed. No regression was found in the
timer, service execution, workload availability, delivery state, or report
payload limits.

## Residual risks

- **medium:** Main campaign 10 has a missing/moved recorded extra channel and
  continues its reconciliation retries.
- **medium:** Dev campaigns 24, 25, 26, 27, and 29 contain active member records
  for users absent from the dev guild; the staff mirror safety guard also
  continues to block removal of seven members.
- **medium:** About 342 GiB of migration material is retained, and Docker reports
  about 64 GiB of reclaimable images. There is no immediate space incident,
  but retention cleanup needs explicit deletion scope.
- **low:** Isolated Discord HTTP 503/expired-interaction events were transient
  in the inspected window.

## Artifacts

- Discover, Apply, Deploy, and this Monitor record — retention class:
  `operations_audit`
- Live report state — retention class: `report_runtime_state`
- Timestamped live-file backups — retention class: `deployment_rollback`

## Recommendation

Close the report-refresh milestone. Open two separate bounded follow-ups only
when authorized:

1. reconcile or retire the affected main/dev campaign records after confirming
   intended Discord state;
2. approve a concrete retention/deletion list for migration copies and unused
   Docker images before reclaiming storage.

## Next step

No further report changes are required. The next automatic run is the primary
ongoing monitor at 08:00 CEST.
