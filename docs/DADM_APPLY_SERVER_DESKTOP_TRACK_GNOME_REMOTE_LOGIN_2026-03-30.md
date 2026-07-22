# DAD-M Apply: Server Desktop Track GNOME Remote Login

Date: 2026-03-30
Phase: APPLY
Track: SERVER-DESKTOP-GNOME-REMOTE-LOGIN
Status: approved

## Objective

Bind a concrete implementation contract for enabling a real remote desktop on this VPS using the already-installed GNOME stack and GNOME Remote Desktop remote login.

## Input Facts

Host state confirmed on `2026-03-30`:

- OS: Arch Linux
- installed:
  - `gdm`
  - `gnome-shell`
  - `gnome-remote-desktop`
  - `xorg-server`
- available tool:
  - `grdctl`
- relevant units present but disabled:
  - `gdm.service`
  - `gnome-remote-desktop.service`
- currently listening:
  - `22`
  - `80`
  - `443`
- currently not listening:
  - `3389`
  - `9090`
- no active firewall service currently detected:
  - `nftables.service` disabled
  - `ufw.service` disabled
  - `iptables.service` disabled

## Decision Summary

The approved desktop path for this host is:

- `GNOME Remote Login`

This means:

- use `gdm` as the display manager
- use `gnome-remote-desktop` system remote login mode
- use RDP as the client protocol
- connect from Windows with built-in `mstsc`

## Why This Path Is Approved

Approved because:

- it uses components already installed on the host
- it provides a real desktop, not just an admin web UI
- it avoids a broader desktop-environment replacement during this session

Rejected as primary path for this track:

- `Cockpit`
  - useful as admin GUI, but not a true desktop
- `XFCE + xrdp`
  - still valid, but not the lowest-friction route on this exact VPS

## Binding Design Decisions

### 1. Use system remote login, not ad-hoc desktop sharing

Approved:

- configure GNOME Remote Desktop in system mode for remote login
- use `grdctl --system` semantics
- treat this as a login surface, not as opportunistic screen sharing on an already-logged-in session

Rejected:

- manual one-off desktop sharing as the primary access model
- per-user informal setup without a systemd-backed path

### 2. RDP is the client protocol

Approved:

- RDP on port `3389`
- Windows client: built-in `Remote Desktop Connection` (`mstsc`)

Rejected:

- introducing VNC as the first rollout path
- mixing multiple remote-desktop protocols in the first deploy step

### 3. Network exposure is a first-class gate

Approved:

- remote desktop must not be exposed casually because this host currently has no active firewall layer managing a new admin port
- first rollout must include an explicit access-control choice

Allowed access-control patterns:

- restricted source IPs
- VPN-only access
- SSH tunnel for initial validation
- equivalent narrow ingress control

Rejected:

- opening `3389` broadly to the internet as an unreviewed convenience step

### 4. TLS and credentials are part of the deploy contract

Approved:

- configure RDP credentials explicitly via `grdctl`
- set TLS certificate and key if the deploy step reaches externally reachable service exposure

Rejected:

- leaving remote login enabled without explicit credentials
- assuming the desktop path is safe enough without deliberate auth material

### 5. Root is required and expected

Approved:

- treat this track as a privileged operations change
- service enablement and remote-login activation require root-capable execution

Rejected:

- pretending this can be fully completed from the current unprivileged shell

## In-Scope Deploy Work

The next deploy step is allowed to:

- enable and/or start `gdm.service`
- configure GNOME Remote Desktop system remote login with `grdctl --system`
- enable and/or start `gnome-remote-desktop.service`
- bind RDP on `3389`
- apply narrow ingress control if needed
- verify local listener state and service health

## Out-of-Scope Work

- installing a new desktop environment
- replacing GNOME with XFCE
- adding Cockpit in the same step
- changing VTT application behavior
- public-broad exposure of `3389` without explicit ingress control

## Acceptance Criteria

The track is ready for monitor when all of the following are true:

- `gdm.service` is active
- `gnome-remote-desktop.service` is active
- `grdctl --system status` shows RDP enabled
- host listens on `3389`
- access path is intentionally restricted or tunneled
- Windows `mstsc` can reach the login surface
- no production VTT ports or services are disrupted

## Operational Risks

### High

1. Broadly exposing `3389` on a host without active firewall policy would create unnecessary remote-admin attack surface.

### Medium

1. Enabling `gdm` on a server host changes the login/display path and should be monitored for service side effects.

2. GNOME is heavier than a minimal desktop stack, so long-term it may still be worth revisiting `XFCE + xrdp` if footprint becomes a concern.

## Recommended Next Step

Proceed to:

- `DEPLOY Server Desktop Track GNOME Remote Login`
