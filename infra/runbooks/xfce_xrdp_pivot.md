# XFCE xrdp Pivot

## Goal

Replace the failing GNOME remote-login path with `xrdp + xorgxrdp + xfce4`.

## Execute

```bash
cd /home/admin/projects/roll-drauf-vtt
sudo chmod +x ops/scripts/deploy_xfce_xrdp_pivot.sh
sudo ./ops/scripts/deploy_xfce_xrdp_pivot.sh
```

## Expected Result

- `xrdp.service` is active
- `xrdp-sesman.service` is active
- `3389` is listening under `xrdp`
- `gnome-remote-desktop.service` is stopped
- `gdm.service` is stopped

## Windows Client

Use:

- `Computer:` `<server-ip>:3389`
- `Username:` `admin`

After connect, select the default `Xorg` path if an xrdp chooser is shown.

## Quick Verify

```bash
systemctl --no-pager --full status xrdp.service xrdp-sesman.service
ss -tulpn | grep ':3389\\b'
journalctl -u xrdp.service -u xrdp-sesman.service -n 80 --no-pager
```

## Rollback

```bash
sudo systemctl disable --now xrdp.service xrdp-sesman.service
sudo systemctl enable --now gdm.service gnome-remote-desktop.service
```
