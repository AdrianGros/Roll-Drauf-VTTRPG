# DAD-M Monitor: GNOME Remote Login Repair

Date: 2026-03-30
Phase: MONITOR
Track: GNOME-REMOTE-LOGIN-REPAIR
Status: fail

## Decision

The repair produced a real intermediate improvement, but it did not achieve a usable GNOME remote login on this VPS.

Result:

- the original missing-session blocker is resolved
- the effective login path is still blocked
- the correct next step is now a desktop pivot away from GNOME

## What Passed

- `/usr/share/xsessions` now exists
- `/usr/share/xsessions/gnome.desktop` exists
- `/usr/share/xsessions/gnome-xorg.desktop` exists
- `gnome-remote-desktop.service` is active
- `3389` is listening
- the earlier `GdmSession: no session desktop files installed, aborting...` blocker is no longer the active failure

## What Failed

- `gdm` is still not providing a stable remote-login surface
- `mstsc` still cannot complete the login flow
- `gdm` now fails deeper in the stack with X-session startup failure

## Evidence

- `systemctl status gdm.service gnome-remote-desktop.service` shows:
  - `gdm.service` active, but with repeated:
    - `GdmDisplay: Session never registered, failing`
    - `maximum number of X display failures reached`
  - `gnome-remote-desktop.service` active with `RDP server started`
- `ss -tulpn | grep ':3389\\b'` shows:
  - `*:3389` is listening
- `journalctl -b _COMM=gdm-x-session -n 80 --no-pager` shows repeated:
  - `Unable to run X server`
- `/var/log/Xorg.0.log` shows the concrete host blocker:
  - `open /dev/dri/card0: No such file or directory`
  - `No devices detected.`
  - `Fatal server error: no screens found`

## Interpretation

The GNOME repair fixed the session contract problem, but the host remains headless from the Xorg point of view.

Inference:

- on this VPS, the GNOME remote-login path is now blocked by the lack of a usable display device for the X session
- this is materially different from the earlier missing-session-files problem
- continuing to patch GNOME inside the same track would broaden scope beyond the approved narrow repair

## Monitoring Verdict

The approved GNOME repair track is not sufficient for this host.

The methodically correct next step is:

- `APPLY Desktop Pivot XFCE xrdp`

## Recommended Next Step

Proceed to:

- `APPLY Desktop Pivot XFCE xrdp`
