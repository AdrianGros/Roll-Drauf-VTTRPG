# GNOME Remote Login Repair Runbook

## Purpose

Repair the current GNOME Remote Login setup by restoring the X session entries GDM expects for remote login.

## Why

Observed server-side failure:

- `GdmSession: no session desktop files installed, aborting...`

Current host state:

- only `/usr/share/wayland-sessions/*` exists
- `/usr/share/xsessions/*` is missing
- `gdm` crash-loops during remote login attempts

## Execute

```bash
cd /home/admin/projects/roll-drauf-vtt
sudo chmod +x ops/scripts/repair_gnome_remote_login.sh
sudo ./ops/scripts/repair_gnome_remote_login.sh
```

## Verify On Host

```bash
ls -la /usr/share/xsessions
sudo systemctl status --no-pager gdm.service gnome-remote-desktop.service
ss -tulpn | grep ':3389\b'
sudo journalctl -u gdm.service -n 40 --no-pager
```

## Verify On Windows

Use `mstsc` with:

- Computer: `<server-ip>:3389`
- Username: `admin`

Expected improvement:

- login surface or credential prompt
- not the previous generic authentication failure

## Rollback

```bash
sudo rm -f /usr/share/xsessions/gnome.desktop /usr/share/xsessions/gnome-xorg.desktop
sudo systemctl restart gdm.service
sudo systemctl restart gnome-remote-desktop.service
```
