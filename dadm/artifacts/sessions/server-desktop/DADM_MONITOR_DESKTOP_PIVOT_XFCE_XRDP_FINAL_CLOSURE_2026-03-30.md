# DAD-M Monitor: Desktop Pivot XFCE xrdp Final Closure

Date: 2026-03-30
Phase: MONITOR
Track: DESKTOP-PIVOT-XFCE-XRDP
Status: hold

## Decision

Final closure is not yet allowed.

The desktop pivot remains technically live, but there is still no observed end-user proof that completes the xrdp login flow.

## What Remains Valid

- `xrdp.service` is active
- `xrdp-sesman.service` is active
- `3389` remains on the xrdp stack
- `gdm.service` remains disabled and inactive
- `gnome-remote-desktop.service` remains disabled and inactive
- no regression is visible in the infrastructure state

## Final Closure Blockers

### 1. No observed human proof

Severity: medium

Since the prior closure checkpoint:

- `journalctl -u xrdp.service -u xrdp-sesman.service --since '2026-03-30 18:05:00'`
  shows no new entries
- no xrdp user session process is visible
- no Xfce session process is visible
- no `.xorgxrdp.*.log` session file is visible

Inference:

- the server has not yet produced evidence of a real client login flow
- therefore the track cannot be marked fully closed

### 2. Runtime hardening is still open

Severity: medium

Earlier evidence remains unchanged:

- xrdp logs that it is running as root

This is not a blocker for the human proof itself, but it is still a blocker for hardened closure.

### 3. Residual historical GDM sessions remain listed

Severity: low

`loginctl list-sessions` still contains many historical `gdm-greeter` entries.

This does not reactivate the old path, but it remains residual host state to clean later.

## Final Verdict

This track is still in `hold`.

It is waiting for:

1. a real Windows `mstsc` proof against `82.25.101.159:3389`
2. a follow-up hardening pass for the xrdp runtime user

## Recommended Next Step

Proceed to:

- `human_proof_pass`

After that, the next DAD-M step should be:

- `APPLY xrdp Hardening`
