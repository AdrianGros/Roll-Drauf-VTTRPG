# DAD-M Discover: Server Desktop Track

Date: 2026-03-30
Phase: DISCOVER
Track: SERVER-DESKTOP
Status: complete

## Objective

Identify the safest and most practical way to give this VPS a graphical administration surface, ideally a real remote desktop, without degrading the VTT stack.

## Current Host State

Observed locally on `2026-03-30`:

- OS: Arch Linux
- default target: `graphical.target`
- installed desktop-related packages:
  - `gdm`
  - `gnome-shell`
  - `gnome-remote-desktop`
  - `xorg-server`
- not installed:
  - `cockpit`
  - `xrdp`
  - `xfce4`
  - `tigervnc`
- current open ports:
  - `22`
  - `80`
  - `443`
- currently not listening:
  - `3389`
  - `9090`
  - `5900`
- current memory headroom after Minecraft cleanup:
  - `16Gi` used
  - `12Gi` free
  - `15Gi` available
  - `95Mi` swap used

## Primary Source Findings

### GNOME Remote Desktop

GNOME documents a built-in remote desktop path:

- desktop sharing and remote control are managed in `Settings -> System -> Remote Desktop`
- enabling `Remote Login` sets port `3389`
- GNOME explicitly lists `mstsc` as the built-in Windows client and recommends default settings
- `grdctl` is available for command-line configuration

Source:

- https://help.gnome.org/gnome-help/sharing-desktop.html

### xrdp

xrdp describes itself as:

- an open-source RDP server
- providing graphical logins over RDP
- accepting Microsoft Remote Desktop Client and other RDP clients
- using TLS by default

Source:

- https://www.xrdp.org/

### Cockpit

Cockpit documents itself as:

- a web-based graphical interface for servers
- suitable for new and experienced admins
- using normal system logins and privileges
- not intended as a full Linux desktop, but as a server admin UI
- accessed on port `9090`
- available on Arch Linux

Source:

- https://cockpit-project.org/

### Microsoft client guidance

Microsoft’s current guidance says:

- for remote PC access on Windows, use the built-in `Remote Desktop Connection` app (`mstsc`) for a generally available path
- Windows App covers other Microsoft remote scenarios, but the built-in RDP client remains the safe baseline for standard remote-PC use

Source:

- https://learn.microsoft.com/en-us/windows-app/get-started-connect-devices-desktops-apps

## Option Matrix

### Option A: GNOME Remote Login on this host

What it gives:

- a real remote desktop
- RDP-compatible access
- least additional installation work on this VPS

Why it fits this host:

- `gdm`, `gnome-shell`, `gnome-remote-desktop`, and `xorg-server` are already installed
- no extra desktop environment is needed to get to a first working remote desktop

Risks:

- heavier than a minimal desktop
- should not be exposed broadly on the public internet without deliberate network controls
- still needs root-level activation and probably firewall work

Assessment:

- best-fit path if the goal is “I want an actual desktop quickly”

### Option B: Cockpit

What it gives:

- strong graphical server administration
- browser-based access
- low ongoing overhead compared with a full desktop

What it does not give:

- not a real Linux desktop session
- no normal desktop windowing workflow

Assessment:

- best-fit path if the goal is “I want to administer the server visually”
- not enough if the requirement is specifically a true desktop

### Option C: Xfce plus xrdp

What it gives:

- a lighter real desktop than GNOME
- standard RDP workflow

Why it is not the first recommendation here:

- not currently installed
- requires a broader install/configuration step than the GNOME path already present on the server

Inference:

- this is likely the better long-term low-overhead desktop shape
- but on this exact host it is not the lowest-friction path today

## Recommendation

For this VPS on `2026-03-30`, the strongest recommendation is a two-tier model:

1. If you want a real desktop now:
   - use the already-present GNOME stack
   - activate `gdm` plus `gnome-remote-desktop`
   - connect from Windows with built-in `mstsc`

2. If you mainly want visual server administration:
   - install Cockpit as a separate admin surface

This recommendation is specific to the current host state. It is based on the fact that GNOME remote desktop components are already installed, while Xfce/xrdp are not.

## Guardrails

- do not expose a new remote-admin port publicly without an explicit access decision
- prefer SSH tunnel, VPN, or restricted source IPs for first rollout
- keep the desktop track separate from the VTT production web entrypoints on `80/443`
- root privileges are required for service enablement and network-opening steps

## Recommended Next Step

Proceed to:

- `APPLY Server Desktop Track`

Recommended default target for Apply:

- `GNOME Remote Login + optional Cockpit sidecar`
