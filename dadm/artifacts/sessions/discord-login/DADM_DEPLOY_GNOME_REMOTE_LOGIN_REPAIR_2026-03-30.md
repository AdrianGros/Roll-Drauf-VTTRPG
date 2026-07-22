# DAD-M Deploy: GNOME Remote Login Repair

Date: 2026-03-30
Phase: DEPLOY
Track: GNOME-REMOTE-LOGIN-REPAIR
Status: blocked-prepared

## Objective

Deploy the smallest repair needed to stop `gdm` from aborting due to missing session desktop files.

## Host Findings Used

- `/usr/bin/gnome-session` exists
- `/usr/share/wayland-sessions/gnome.desktop` exists
- `/usr/share/xsessions` is missing
- `gdm` crash logs show:
  - `GdmSession: no session desktop files installed, aborting...`

## Actions Completed In This Deploy Step

Prepared repair artifacts:

- `ops/scripts/repair_gnome_remote_login.sh`
- `ops/runbooks/gnome_remote_login_repair.md`

The repair script:

- creates `/usr/share/xsessions`
- writes:
  - `gnome.desktop`
  - `gnome-xorg.desktop`
- restarts:
  - `gdm.service`
  - `gnome-remote-desktop.service`
- prints verification output for immediate proof

## Why The Deploy Is Still Marked Blocked

The actual host mutation requires root because it writes under `/usr/share/xsessions` and restarts system services.

## Prepared Execution Path

```bash
cd /home/admin/projects/roll-drauf-vtt
sudo chmod +x ops/scripts/repair_gnome_remote_login.sh
sudo ./ops/scripts/repair_gnome_remote_login.sh
```

## Expected Success Signal

- `gdm.service` remains active without crash-looping
- `gnome-remote-desktop.service` remains active
- `3389` keeps listening
- Windows `mstsc` reaches a GNOME login surface or prompt

## Failure Gate

If this deploy is executed and:

- `gdm` still crash-loops
- or the Windows client still fails with the same effective behavior

then the next correct step is a desktop pivot away from GNOME.

## Recommended Next Step

Execute the prepared root repair and then proceed to:

- `MONITOR GNOME Remote Login Repair`
