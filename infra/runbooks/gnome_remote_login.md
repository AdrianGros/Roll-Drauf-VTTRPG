# GNOME Remote Login Runbook

## Purpose

Enable a real remote desktop on this Arch Linux VPS using the already installed GNOME stack.

## Preconditions

- `gdm`, `gnome-shell`, `gnome-remote-desktop`, and `xorg-server` are installed
- root shell available
- ingress to port `3389` is restricted outside the host
- chosen RDP credentials are ready

## Safe Default

Do not expose `3389` broadly on the internet.

Preferred first rollout:

- keep `3389` blocked except from trusted source IPs
- or keep it reachable only behind VPN
- or equivalent external firewall restriction

## Execute

```bash
cd /home/admin/projects/roll-drauf-vtt
sudo chmod +x ops/scripts/enable_gnome_remote_login.sh
sudo env \
  GRD_USER='admin' \
  GRD_PASS='CHOOSE_A_STRONG_PASSWORD' \
  ASSUME_INGRESS_RESTRICTED=yes \
  ./ops/scripts/enable_gnome_remote_login.sh
```

Optional TLS paths:

```bash
sudo env \
  GRD_USER='admin' \
  GRD_PASS='CHOOSE_A_STRONG_PASSWORD' \
  ASSUME_INGRESS_RESTRICTED=yes \
  TLS_CERT='/path/to/cert.pem' \
  TLS_KEY='/path/to/key.pem' \
  ./ops/scripts/enable_gnome_remote_login.sh
```

## Verify

```bash
sudo systemctl status --no-pager gdm.service gnome-remote-desktop.service
sudo grdctl --system status
ss -tulpn | grep ':3389\\b'
```

## Windows Client

Use the built-in Windows client:

- open `mstsc`
- connect to `<server-ip>:3389`
- sign in with the configured `GRD_USER` / `GRD_PASS`

## Rollback

```bash
sudo systemctl disable --now gnome-remote-desktop.service
sudo systemctl disable --now gdm.service
```
