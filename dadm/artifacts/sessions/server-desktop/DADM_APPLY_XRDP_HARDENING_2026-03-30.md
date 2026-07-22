# DAD-M Apply: xrdp Hardening

Date: 2026-03-30
Phase: APPLY
Track: XRDP-HARDENING
Status: approved

## Objective

Harden the live `xrdp` deployment without reopening the desktop pivot itself.

## Input Findings

From `DADM_MONITOR_DESKTOP_PIVOT_XFCE_XRDP_FINAL_CLOSURE_2026-03-30.md`:

- `xrdp.service` is active
- `xrdp-sesman.service` is active
- `3389` is on the xrdp path
- the remaining hardening finding is that xrdp is running as root

Current host facts:

- `/etc/xrdp/xrdp.ini` still has:
  - `#runtime_user=xrdp`
  - `#runtime_group=xrdp`
- `/etc/xrdp/sesman.ini` still has:
  - `#SessionSockdirGroup=xrdp`
- no `xrdp` user exists yet
- no `xrdp` group exists yet
- `/run/xrdp` is currently `root:root`
- `/etc/xrdp/rsakeys.ini`, `/etc/xrdp/cert.pem`, and `/etc/xrdp/key.pem` are currently `root:root`
- `/etc/xrdp/sesman.ini` currently has:
  - `AllowRootLogin=true`

## Primary-Source Basis

From the installed xrdp primary docs and shipped tooling:

- [xrdp.ini.5](/usr/share/man/man5/xrdp.ini.5) says:
  - `runtime_user` / `runtime_group` are the user and group to run the daemon under
  - after startup xrdp drops UID/GID to those values
  - `runtime_group` must match `SessionSockdirGroup` in `sesman.ini`
- [sesman.ini.5](/usr/share/man/man5/sesman.ini.5) says:
  - `SessionSockdirGroup` must match `runtime_group`
  - `AllowRootLogin` explicitly enables root login on the terminal server
- the shipped checker [xrdp-chkpriv](/usr/share/xrdp/xrdp-chkpriv) and upstream source checker in `/tmp/xrdp-inspect/tools/chkpriv/xrdp-chkpriv.in` expect:
  - both `runtime_user` and `runtime_group` to be set
  - the runtime user and group to exist
  - `rsakeys.ini` to be owned by `root:<runtime_group>` with `640`
  - certificate and key to be readable but not writable by the runtime user/group

## Decision Summary

This hardening track is approved to do the minimum necessary privilege drop and file-permission repair for xrdp.

## Binding Decisions

### 1. Introduce a dedicated xrdp runtime identity

Approved:

- create user `xrdp`
- create group `xrdp`
- make the daemon run under that identity

Rejected:

- reusing `admin`
- keeping the daemon as `root`

### 2. Align xrdp and sesman on the same runtime group

Approved:

- set `runtime_user=xrdp`
- set `runtime_group=xrdp`
- set `SessionSockdirGroup=xrdp`

Rejected:

- setting only one side of the contract

### 3. Repair permissions to match xrdp's own checker model

Approved:

- set `/etc/xrdp/rsakeys.ini` to `root:xrdp` with mode `640`
- set `/etc/xrdp/cert.pem` to `root:xrdp` with mode `640`
- set `/etc/xrdp/key.pem` to `root:xrdp` with mode `640`
- ensure `/run/xrdp` is compatible with the runtime group
- validate with `/usr/share/xrdp/xrdp-chkpriv`

Rejected:

- broad ownership changes across unrelated files

### 4. Disable terminal-server root login

Approved:

- set `AllowRootLogin=false`

Inference:

- this does not affect the intended `admin` login path
- it removes a needless elevated login path from the RDP surface

## In-Scope Deploy Work

The next deploy step may:

- create the `xrdp` user and group
- patch `/etc/xrdp/xrdp.ini`
- patch `/etc/xrdp/sesman.ini`
- adjust file ownership and modes for xrdp secrets and runtime paths
- restart `xrdp.service`
- restart `xrdp-sesman.service`
- run `/usr/share/xrdp/xrdp-chkpriv`
- verify that the root-warning disappears from the logs

## Out-of-Scope Deploy Work

- changing the Xfce session shape
- changing the listening port
- opening additional network services
- broader login-policy redesign beyond `AllowRootLogin`

## Acceptance Criteria

The hardening deploy is ready for monitor when all of the following are true:

- `xrdp` user exists
- `xrdp` group exists
- `runtime_user=xrdp` is active in `xrdp.ini`
- `runtime_group=xrdp` is active in `xrdp.ini`
- `SessionSockdirGroup=xrdp` is active in `sesman.ini`
- `AllowRootLogin=false` is active in `sesman.ini`
- `/usr/share/xrdp/xrdp-chkpriv` passes
- xrdp logs no longer report running as root
- `3389` still listens and the xrdp stack stays active

## Recommended Next Step

Proceed to:

- `DEPLOY xrdp Hardening`
