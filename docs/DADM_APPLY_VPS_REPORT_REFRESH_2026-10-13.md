# DAD-M Apply — VPS Daily Report Refresh

- **status:** complete
- **date:** 2026-10-13
- **profile:** standard
- **input:** `docs/DADM_DISCOVER_VPS_REPORT_REFRESH_2026-10-13.md`

## Design summary

Repair the existing host-native report in place. Preserve its timer, webhook,
state directory, German presentation, commit cursors, and explicit Palworld
omission. Replace the obsolete migration-era checks with checks that describe
the current Ubuntu target and fail visibly when evidence cannot be read.

## Solution boundary

### In scope

- Give only `vps-daily-report.service` supplemental `systemd-journal` access.
- Remove the retired `/opt/rolldrauf-bot-prod`/sudo drift check and its tile.
- Count explicit bot `ERROR`, `CRITICAL`, and `FATAL` records across the full
  interval before applying any display limit.
- Aggregate the records into signatures and show both event and signature
  counts plus bounded details.
- Refresh availability/resource coverage for the current VTT, Goblin Delve,
  game, Codex, DADM KB, PostgreSQL, Docker, and nginx workloads.
- Add kernel OOM detection for the interval.
- Use disk percentage plus absolute free bytes for alert status.
- Make report-state advancement conditional on successful delivery.
- Add a no-send/state-directory override for integration verification.

### Out of scope

- Campaign/member reconciliation or Discord resource mutation.
- Migration archive, Docker image, backup, or other storage deletion.
- Bot application fixes for isolated Discord errors.
- Palworld reporting; its existing explicit omission remains authoritative.
- Redesigning bot deployment provenance or creating a new release registry.

## Interfaces and contracts

### Runtime inputs

- `VPS_REPORT_DRY_RUN=1`: build artifacts but do not read/post the webhook and
  do not advance marker/commit state.
- `VPS_REPORT_STATE_DIR=<path>`: direct generated artifacts and cursors to an
  isolated verification directory.
- Existing webhook path and default state directory remain unchanged in normal
  operation.

### Evidence contract

- `Log-Zugriff` is critical unless the process has root, `adm`, or
  `systemd-journal` membership.
- A missing journal permission must never produce a green zero-error tile.
- Bot event count is the number of explicit level-bearing journal records, not
  matching traceback lines.
- Signature count is computed after stripping the per-record timestamp; IDs
  remain in the signature so different affected campaigns stay distinct.
- Details are sorted by frequency and bounded only at presentation time.

### Availability groups

- VTT: app, database, Redis, and mailserver containers.
- Goblin Delve: bot, web client, and next/staging web client.
- Games: ATM10, Cottage Witch, and healthy 7 Days to Die. Palworld is omitted.
- Platform: Codex Remote, DADM KB, PostgreSQL 18, Docker, and nginx.
- A group is healthy only when all required members are active/running; the
  local text artifact records missing members.

### Capacity status

- Disk critical: at least 90% used or less than 40 GiB available.
- Disk warning: at least 80% used or less than 100 GiB available.
- Otherwise disk is good; the tile always shows used percentage and free space.
- Memory keeps the existing 70% warning / 90% critical thresholds.

### Delivery transaction

The sender must exit non-zero on webhook failure. The shell must then exit
non-zero without touching `last_run_marker`, `last_commit`, or
`vtt_last_commit`. Dry-run never advances them.

## Rollout notes

1. Preserve timestamped copies of both scripts and the systemd unit.
2. Patch scripts and unit, then run shell/Python syntax checks.
3. Reload systemd without restarting unrelated workloads.
4. Execute an isolated dry-run as `admin` with the supplemental journal group.
5. Assert current-service coverage, journal visibility, non-zero bot errors,
   corrected load formatting, no retired-check field, and valid embed limits.
6. Start the oneshot once normally to send the corrected current report.
7. Confirm HTTP 204, success status, cursor advancement, and absence of new
   sudo/PAM errors from the report unit.

## Acceptance criteria

- The report no longer invokes sudo or references `rolldrauf-bot-prod`.
- A service-context dry-run can read main/dev bot errors.
- The refreshed report shows the three recurring error families and isolated
  errors as aggregated evidence rather than `0` or a ten-line truncation.
- Current VTT, Goblin Delve, game, and platform groups are represented.
- ATM10 and Cottage Witch appear in the RAM matrix.
- Load renders as `1m / 5m / 15m` with consistent separators.
- At 70% with roughly 238 GiB free, disk is informational/good, not warning.
- No failed units and no post-cutover OOM events are reported accurately.
- A simulated no-send run does not change production cursors.
- The live refresh posts once and completes successfully.
- No campaign, Discord, archive, Docker image, or backup data is changed.

## Risks and tradeoffs

- **medium, accepted residual:** Real reconciliation errors remain after the
  report repair; they are made visible and need an operator data decision.
- **medium, accepted residual:** 70% disk usage remains real. Combined
  percentage/headroom thresholds reduce noise without removing low-space
  protection; cleanup remains separately gated.
- **low:** Explicit service names require maintenance when workloads change.
- **low:** Signature aggregation is log-format dependent, but it is more honest
  than the current truncation and preserves a critical journal-access guard.

## Artifacts

- This design — retention class: `operations_design`
- Planned timestamped live-file backups — retention class:
  `deployment_rollback`
- Planned dry-run/live evidence — retention class: `deployment_proof`

## Deploy handoff

Implement only this design, verify with an isolated dry-run, then issue one
live report refresh. Stop without changing application or campaign data if the
dry-run does not satisfy the acceptance criteria.

## Next step

Proceed to DAD-M Deploy.
