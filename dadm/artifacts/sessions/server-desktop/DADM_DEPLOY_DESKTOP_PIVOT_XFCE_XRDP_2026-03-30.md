# DAD-M Deploy: Desktop Pivot XFCE xrdp

Date: 2026-03-30
Phase: DEPLOY
Track: DESKTOP-PIVOT-XFCE-XRDP
Status: blocked-prepared

## Objective

Deploy the approved remote-desktop pivot from the failing GNOME path to `xrdp + xorgxrdp + xfce4`.

## Host Facts Used

- `gnome-remote-desktop.service` currently owns `3389`
- `gdm` remains functionally broken on this headless VPS
- `xfce4` is available from the official Arch repos on this host
- `xrdp` is not available as a plain official repo package on this host
- upstream source builds are therefore prepared from the official `neutrinolabs` repositories

## Deploy Artifacts Prepared

- `ops/scripts/deploy_xfce_xrdp_pivot.sh`
- `ops/runbooks/xfce_xrdp_pivot.md`

The deploy script is intentionally narrow. It:

- installs the required Arch packages for build and Xfce session startup
- builds `xrdp` from the official `v0.10.3` tag
- builds `xorgxrdp` from the official `v0.10.4` tag
- installs the upstream Arch PAM profile for `xrdp-sesman`
- sets `/etc/xrdp/startwm.sh` to `startxfce4`
- adds `/etc/X11/Xwrapper.config` for headless Xorg compatibility
- disables `gnome-remote-desktop.service` and `gdm.service`
- enables `xrdp.service` and `xrdp-sesman.service`
- prints immediate verification output

## Why This Deploy Is Still Marked Blocked

The actual host mutation requires root because it:

- installs packages with `pacman`
- writes under `/etc`
- writes under `/usr`
- enables and disables system services

## Prepared Execution Path

```bash
cd /home/admin/projects/roll-drauf-vtt
sudo chmod +x ops/scripts/deploy_xfce_xrdp_pivot.sh
sudo ./ops/scripts/deploy_xfce_xrdp_pivot.sh
```

## Expected Success Signal

- `xrdp.service` active
- `xrdp-sesman.service` active
- `3389` listening under `xrdp`
- Windows `mstsc` reaches the `xrdp` login flow
- successful login lands in an Xfce desktop session

## Recommended Next Step

Execute the prepared root deploy and then proceed to:

- `MONITOR Desktop Pivot XFCE xrdp`
