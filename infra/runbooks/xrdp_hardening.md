# xrdp Hardening

## Goal

Drop the `xrdp` daemon out of root runtime mode and align the host with xrdp's own privilege model.

## Execute

```bash
cd /home/admin/projects/roll-drauf-vtt
sudo chmod +x ops/scripts/deploy_xrdp_hardening.sh
sudo ./ops/scripts/deploy_xrdp_hardening.sh
```

## What This Changes

- creates system user/group `xrdp`
- enables `runtime_user=xrdp`
- enables `runtime_group=xrdp`
- enables `SessionSockdirGroup=xrdp`
- sets `AllowRootLogin=false`
- repairs xrdp secret permissions
- creates a tmpfiles rule for `/run/xrdp`

## Verify

```bash
systemctl --no-pager --full status xrdp.service xrdp-sesman.service
ss -tulpn | grep ':3389\\b'
sudo /usr/share/xrdp/xrdp-chkpriv
journalctl -u xrdp.service -u xrdp-sesman.service -n 80 --no-pager
```

## Expected Result

- `xrdp.service` active
- `xrdp-sesman.service` active
- `3389` still listening
- `xrdp-chkpriv` passes
- no new `You are running xrdp as root` warning in fresh logs
