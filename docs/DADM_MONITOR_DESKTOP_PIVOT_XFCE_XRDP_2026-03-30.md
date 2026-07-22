# DAD-M Monitor: Desktop Pivot XFCE xrdp

Date: 2026-03-30
Phase: MONITOR
Track: DESKTOP-PIVOT-XFCE-XRDP
Status: conditional-pass

## Decision

The infrastructure pivot from GNOME Remote Login to `xrdp + xorgxrdp + xfce4` is live on the VPS.

Result:

- deploy intent is materially achieved
- the old GNOME path is no longer the active entrypoint
- final closure still requires a real Windows client proof

## What Passed

- `xrdp.service` is active
- `xrdp-sesman.service` is active
- `gdm.service` is disabled and inactive
- `gnome-remote-desktop.service` is disabled and inactive
- `3389` is listening after the pivot
- `/usr/bin/xrdp`, `/usr/bin/xrdp-sesman`, and `/usr/bin/startxfce4` exist
- `/etc/xrdp/startwm.sh` launches `startxfce4`
- `/etc/pam.d/xrdp-sesman` is present with the upstream Arch profile
- `/etc/X11/Xwrapper.config` exists with headless compatibility settings
- xorgxrdp modules are installed under `/usr/lib/xorg/modules`

## Evidence

- `systemctl status xrdp.service xrdp-sesman.service gdm.service gnome-remote-desktop.service`
- `ss -tulpn | grep ':3389\\b'`
- `/etc/xrdp/startwm.sh`
- `/etc/pam.d/xrdp-sesman`
- `/etc/X11/Xwrapper.config`
- `/usr/lib/xorg/modules/libxorgxrdp.so`
- `/usr/lib/xorg/modules/drivers/xrdpdev_drv.so`
- `/usr/lib/xorg/modules/input/xrdpkeyb_drv.so`
- `/usr/lib/xorg/modules/input/xrdpmouse_drv.so`

## Open Findings

### 1. Human client proof is still missing

Severity: medium

Not yet proven in this monitor step:

- that Windows `mstsc` reaches the xrdp login flow
- that a successful login lands in a usable Xfce desktop session

### 2. xrdp is currently running as root

Severity: medium

`journalctl -u xrdp.service -u xrdp-sesman.service` reports:

- `[CORE ] You are running xrdp as root. This is not safe.`

Inference:

- the pivot is usable for functional proof
- but it should not be treated as fully hardened until the xrdp runtime user model is tightened

## Monitoring Verdict

This track has passed the infrastructure pivot gate, but it has not yet passed full operational closure.

The next correct step is:

- run a Windows client proof against the new xrdp endpoint
- then decide whether to do a narrow hardening pass for the root-run warning

## Recommended Next Step

Proceed to:

- `MONITOR Desktop Pivot XFCE xrdp Closure`
