# DAD-M Deploy — VPS Daily Report Refresh

- **status:** complete
- **date:** 2026-10-13
- **profile:** standard
- **input:** `docs/DADM_APPLY_VPS_REPORT_REFRESH_2026-10-13.md`

## Implementation summary

Updated the live VPS daily report for the post-migration Ubuntu host. The
report now has explicit journal-read permission, checks the current workload
groups, counts and aggregates real bot error records, detects kernel OOMs,
uses capacity-aware disk status, supports an isolated no-send run, and advances
its cursors only after successful delivery. The retired bot checkout/sudo check
was removed.

No campaign, Discord resource, migration archive, Docker image, backup, or
application data was changed.

## Files changed

- `/opt/vps-daily-report/scripts/vps_daily_report.sh`
- `/opt/vps-daily-report/scripts/build_and_send_embed.py`
- `/etc/systemd/system/vps-daily-report.service`
- `docs/DADM_DISCOVER_VPS_REPORT_REFRESH_2026-10-13.md`
- `docs/DADM_APPLY_VPS_REPORT_REFRESH_2026-10-13.md`
- This deployment record

## Rollback artifacts

- `/opt/vps-daily-report/scripts/vps_daily_report.sh.bak_20261013`
- `/opt/vps-daily-report/scripts/build_and_send_embed.py.bak_20261013`
- `/etc/systemd/system/vps-daily-report.service.bak_20261013`

Retention class: `deployment_rollback`.

## Verification run

- `bash -n` passed for the report shell script.
- `python3 -m py_compile` passed for the embed sender.
- `systemd-analyze verify` passed for the service and timer.
- `systemctl daemon-reload` loaded
  `SupplementaryGroups=systemd-journal` for the report service.
- An isolated transient-systemd dry-run executed as `admin` with the same
  supplemental group and `VPS_REPORT_DRY_RUN=1`.
- The dry-run generated a 19-field, 2,704-character embed, stayed within all
  checked Discord limits, detected 2,596 bot error records / 13 signatures in
  its rolling 24-hour window, and did not change production cursors.
- A single normal service run at 11:34 CEST exited 0 and Discord returned
  `HTTP 204`.
- The live interval from the prior 08:00 report contained 387 bot error records
  / 10 signatures: 300 dev and 87 main.
- The live report showed VTT 4/4, Goblin Delve 3/3, games 3/3, platform 5/5,
  journal access available, no failed units, and no kernel OOM.
- The production marker changed only after the successful post.
- No report-service error or sudo/PAM error was recorded during the final run.
- The timer remains enabled/active; next scheduled run is 2026-10-14 08:00
  CEST.

## Proofs

- Live state: `/home/admin/.local/state/vps-daily-report/last_report.txt`
- Live embed: `/home/admin/.local/state/vps-daily-report/last_embed.json`
- Dry-run state: `/tmp/vps-report-dry-run.5if06V/`
- Script SHA-256:
  `944a358c19700ef261885f2406a1d1e5977a674abb482ce58e85fd7c35042bb7`
- Sender SHA-256:
  `49dbf03334ed581a12c2d47702b075d2722c6bcc368e5a36db1a306f286a5a69`
- Unit SHA-256:
  `8c118398dce1b5187cd3f93ebcfd4bf0ca8845f4506047b3bbc06bd1b2c8ae71`

Retention class: `deployment_proof` (the `/tmp` dry-run directory is ephemeral;
this record retains its asserted results).

## Acceptance checklist

- [x] No sudo or retired `rolldrauf-bot-prod` reference remains.
- [x] Service-context journal access succeeds.
- [x] Bot events are counted before presentation truncation.
- [x] Error signatures and affected services are included.
- [x] Current workload groups are represented.
- [x] ATM10 and Cottage Witch appear in the RAM matrix.
- [x] Load uses consistent `1m / 5m / 15m` separators.
- [x] Disk shows 70% with 238 GiB free as good under combined thresholds.
- [x] Failed-unit and kernel-OOM results are accurate.
- [x] Dry-run leaves production state unchanged.
- [x] Successful live post advances state.
- [x] Timer remains scheduled.
- [x] No out-of-scope production data was mutated.

## Risks and assumptions

- **medium, residual:** Campaign/member reconciliation errors continue every
  five minutes until an operator confirms the desired Discord/data state.
- **medium, residual:** Retained migration data and reclaimable Docker images
  consume substantial disk space; cleanup remains separately gated.
- **low:** A later service rename requires updating the explicit inventory.

## Next step

Proceed to Monitor to confirm the emitted report and next-run readiness. Handle
campaign reconciliation and storage cleanup as separate bounded decisions.
