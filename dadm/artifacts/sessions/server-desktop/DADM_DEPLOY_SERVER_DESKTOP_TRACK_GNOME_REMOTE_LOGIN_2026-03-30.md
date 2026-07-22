# DAD-M Deploy: Server Desktop Track GNOME Remote Login

Date: 2026-03-30
Phase: DEPLOY
Track: SERVER-DESKTOP-GNOME-REMOTE-LOGIN
Status: blocked-prepared

## Objective

Execute the approved GNOME Remote Login rollout for this VPS.

## Actions Performed

Validated live host state before activation:

- `gdm.service` is currently `inactive (dead)`
- `gnome-remote-desktop.service` is currently `inactive (dead)`
- port `3389` is not listening
- `grdctl --system status` does not complete from the current shell because the host requires privileged authentication and no controlling TTY auth agent is available in this execution context

Prepared deploy artifacts:

- `ops/scripts/enable_gnome_remote_login.sh`
- `ops/runbooks/gnome_remote_login.md`

## Blockers

### High

1. Root-only activation

The required activation path depends on:

- `systemctl enable --now gdm.service`
- `grdctl --system ...`
- `systemctl enable --now gnome-remote-desktop.service`

Those operations cannot be completed from the current unprivileged execution context.

### High

2. Ingress control must be explicit before RDP is started

This host currently has no active local firewall service managing a new admin port, so enabling `3389` without confirming external restriction would be unsafe.

### Medium

3. Final credential values are an operator decision

The rollout needs explicit `GRD_USER` / `GRD_PASS` values at execution time.

## Prepared Execution Path

When root access and ingress restriction are available, the intended deploy path is:

```bash
cd /home/admin/projects/roll-drauf-vtt
sudo chmod +x ops/scripts/enable_gnome_remote_login.sh
sudo env \
  GRD_USER='admin' \
  GRD_PASS='CHOOSE_A_STRONG_PASSWORD' \
  ASSUME_INGRESS_RESTRICTED=yes \
  ./ops/scripts/enable_gnome_remote_login.sh
```

## Result

Deploy was advanced to a ready-to-execute state, but not activated yet.

## Recommended Next Step

Next step is a `human_decision` / privileged execution checkpoint:

- confirm ingress restriction strategy for `3389`
- execute the prepared root script
- then proceed to `MONITOR Server Desktop Track GNOME Remote Login`
