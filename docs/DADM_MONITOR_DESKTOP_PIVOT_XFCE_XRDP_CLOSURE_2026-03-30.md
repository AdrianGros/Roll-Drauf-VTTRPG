# DAD-M Monitor: Desktop Pivot XFCE xrdp Closure

Date: 2026-03-30
Phase: MONITOR
Track: DESKTOP-PIVOT-XFCE-XRDP
Status: ready-for-human-proof

## Decision

The desktop pivot is operationally prepared but not yet fully closed.

Result:

- infrastructure closure: pass
- end-user desktop proof: pending
- hardening closure: pending

The track may proceed to a human proof pass, but it should not yet be marked fully closed.

## What Is Now Proven

- `xrdp.service` is active
- `xrdp-sesman.service` is active
- `gdm.service` is disabled and inactive
- `gnome-remote-desktop.service` is disabled and inactive
- `3389` is listening under the new xrdp stack
- `startxfce4` is installed
- `/etc/xrdp/startwm.sh` is pinned to Xfce
- `/etc/pam.d/xrdp-sesman` exists
- `/etc/X11/Xwrapper.config` exists
- xorgxrdp modules are installed

## What Is Not Yet Proven

### 1. No observed Windows client proof yet

Severity: medium

Current evidence shows no completed xrdp login attempt after the pivot:

- no xrdp session process beyond the service daemons
- no observed Xfce session process
- no observed `.xorgxrdp.*.log` session file

Inference:

- the infrastructure is ready
- but we have not yet seen a real client reach and complete the login flow

### 2. xrdp runtime hardening is still open

Severity: medium

The service log still reports:

- `You are running xrdp as root. This is not safe.`

This does not block a functional proof pass, but it blocks full production-hardening closure.

### 3. Residual GDM loginctl session history remains visible

Severity: low

`loginctl list-sessions` still shows many historical `gdm-greeter` sessions even though:

- `gdm.service` is inactive
- `gnome-remote-desktop.service` is inactive

This is not the active remote-desktop path anymore, but it is residual host state worth cleaning later.

## Closure Verdict

The track is not closed yet.

It is ready for a human proof pass against the new xrdp endpoint.

## Required Human Proof

From Windows:

- open `mstsc`
- connect to `82.25.101.159:3389`
- log in as `admin`
- verify that the flow reaches the xrdp login surface and lands in an Xfce session

## Recommended Next Step

Proceed to:

- `human_proof_pass`

After that, the next DAD-M step should be:

- `MONITOR Desktop Pivot XFCE xrdp Final Closure`
