# DAD-M Apply: Desktop Pivot XFCE xrdp

Date: 2026-03-30
Phase: APPLY
Track: DESKTOP-PIVOT-XFCE-XRDP
Status: approved

## Objective

Replace the failing GNOME remote-login path with a lighter RDP stack that is better suited to this headless VPS.

## Input Findings

From `DADM_MONITOR_GNOME_REMOTE_LOGIN_REPAIR_2026-03-30.md`:

- the missing GDM session-file blocker was repaired
- `gnome-remote-desktop.service` is active
- `3389` is listening
- the effective login flow is still blocked
- `gdm-x-session` repeatedly reports `Unable to run X server`
- `/var/log/Xorg.0.log` reports:
  - `open /dev/dri/card0: No such file or directory`
  - `No devices detected.`
  - `no screens found`

Current host state:

- `xrdp` is not installed
- `xorgxrdp` is not installed
- `xfce4` is not installed
- no `xrdp` units are present yet

## Source-Backed Rationale

Primary-source support used for this apply decision:

- xrdp states that it provides graphical remote login over RDP and uses TLS by default:
  - https://www.xrdp.org/
- xorgxrdp states that it is used together with xrdp and X.Org, and that xrdp starts Xorg with a configuration that activates the xorgxrdp modules:
  - https://github.com/neutrinolabs/xorgxrdp
- Xfce documents `startxfce4` as the standard way to start an Xfce session and documents X session integration through `.desktop` session entries:
  - https://docs.xfce.org/xfce/4.10/getting-started
  - https://docs.xfce.org/xfce/display_managers

Inference:

- the GNOME path is failing because the host does not have a usable local display device for the GDM/Xorg login path
- the `xrdp + xorgxrdp + Xfce` path is the smallest practical pivot because it is purpose-built for remote RDP sessions and does not depend on the current GDM remote-login contract

## Decision Summary

This track is approved to pivot the remote desktop stack to:

- `xrdp`
- `xorgxrdp`
- `xfce4`

This track is approved to:

- hand ownership of port `3389` from GNOME Remote Desktop to `xrdp`
- keep GNOME packages installed for now, but stop using the GNOME remote-login path
- use a minimal Xfce session start path for the remote desktop

This track is not approved to:

- broaden into a general desktop redesign
- install unnecessary desktop extras before first proof
- expose additional ports beyond the existing RDP path

## Binding Decisions

### 1. The pivot is operational, not cosmetic

Approved:

- disable the active GNOME RDP service before starting `xrdp`
- treat `xrdp` as the new remote-login entrypoint on `3389`

Rejected:

- trying to keep GNOME RDP and `xrdp` live on the same port
- more GNOME-specific repair in this track

### 2. Use the smallest viable desktop

Approved minimum stack:

- `xrdp`
- `xorgxrdp`
- `xfce4`

Deferred unless first proof requires them:

- `xfce4-goodies`
- Cockpit
- any alternative display manager

### 3. Prefer a direct Xfce session start

Approved:

- configure the `xrdp` session start path to launch `startxfce4`
- use a system-level configuration that gets the first proof working for this server

Rejected:

- per-user desktop customization before the first successful login proof

### 4. Keep the rollback simple

Approved rollback:

- stop `xrdp` and `xrdp-sesman`
- re-enable `gnome-remote-desktop.service` if needed

Rejected:

- uninstalling GNOME packages in the same deploy step

## In-Scope Deploy Work

The next deploy step may:

- install `xrdp`
- install `xorgxrdp`
- install `xfce4`
- configure the `xrdp` session start path for `startxfce4`
- stop or disable `gnome-remote-desktop.service`
- stop or disable `gdm.service` if it is no longer needed
- enable and start `xrdp.service`
- enable and start `xrdp-sesman.service`
- verify port `3389`, service health, and a Windows `mstsc` login attempt

## Out-of-Scope Deploy Work

- uninstalling GNOME packages
- tuning themes or desktop appearance
- adding admin web panels
- changing VTT application services

## Acceptance Criteria

This apply decision is ready for deploy when the next step is constrained to the following proof targets:

- `xrdp.service` active
- `xrdp-sesman.service` active
- `3389` listening under `xrdp`
- `mstsc` reaches an `xrdp` login flow
- successful login lands in an Xfce desktop session

## Recommended Next Step

Proceed to:

- `DEPLOY Desktop Pivot XFCE xrdp`
