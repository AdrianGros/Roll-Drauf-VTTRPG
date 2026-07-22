# DAD-M Deploy: xrdp Hardening

Date: 2026-03-30
Phase: DEPLOY
Track: XRDP-HARDENING
Status: blocked-prepared

## Objective

Deploy the approved xrdp privilege-drop hardening on the live VPS.

## Deploy Artifacts Prepared

- `ops/scripts/deploy_xrdp_hardening.sh`
- `ops/runbooks/xrdp_hardening.md`

The deploy script is intentionally narrow. It:

- creates the `xrdp` system user and group if missing
- activates `runtime_user=xrdp`
- activates `runtime_group=xrdp`
- activates `SessionSockdirGroup=xrdp`
- sets `AllowRootLogin=false`
- repairs ownership and mode for:
  - `/etc/xrdp/rsakeys.ini`
  - `/etc/xrdp/cert.pem`
  - `/etc/xrdp/key.pem`
- creates a tmpfiles rule for `/run/xrdp`
- restarts `xrdp.service` and `xrdp-sesman.service`
- runs `/usr/share/xrdp/xrdp-chkpriv`

## Why This Deploy Is Still Marked Blocked

The actual host mutation requires root because it:

- creates a system user and group
- edits files under `/etc/xrdp`
- changes ownership and permissions on cryptographic files
- writes under `/etc/tmpfiles.d`
- restarts system services

## Prepared Execution Path

```bash
cd /home/admin/projects/roll-drauf-vtt
sudo chmod +x ops/scripts/deploy_xrdp_hardening.sh
sudo ./ops/scripts/deploy_xrdp_hardening.sh
```

## Expected Success Signal

- `xrdp.service` active
- `xrdp-sesman.service` active
- `3389` still listening
- `xrdp-chkpriv` passes
- fresh xrdp logs no longer report running as root

## Recommended Next Step

Execute the prepared root deploy and then proceed to:

- `MONITOR xrdp Hardening`
