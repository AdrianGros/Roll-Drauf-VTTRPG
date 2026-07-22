# DAD-M Discover: GNOME Remote Login Failure

Date: 2026-03-30
Phase: DISCOVER
Track: GNOME-REMOTE-LOGIN-FAILURE
Status: complete

## Objective

Determine why GNOME Remote Login does not complete successfully even though:

- `gnome-remote-desktop.service` is active
- RDP is enabled
- port `3389` is listening
- TLS certificate and key are configured

## Observed Runtime State

Verified locally on `2026-03-30`:

- `gnome-remote-desktop.service` is active
- `gdm.service` is repeatedly restarting after crashes
- `3389` is listening from `gnome-remote-desktop-daemon`

Key server-side log findings:

- `RDP server started`
- `client authentication failure`
- `NTLM MIC verification failed`
- `server supports only NLA Security`
- `GdmSession: no session desktop files installed, aborting...`
- repeated `gdm` core dumps with restart loops

## Package / Filesystem Findings

Installed:

- `gdm`
- `gnome-remote-desktop`
- `gnome-session`
- `gnome-shell`
- `mutter`
- `xorg-server`

Not installed:

- `gnome-session-xsession`

Session files present:

- `/usr/share/wayland-sessions/gnome.desktop`
- `/usr/share/wayland-sessions/gnome-wayland.desktop`

Session files absent:

- `/usr/share/xsessions/gnome.desktop`
- `/usr/share/xsessions/gnome-xorg.desktop`

Local package evidence:

- `pacman -Ql gnome-session` shows only Wayland session desktop files on this host
- no local package currently provides GNOME session desktop files under `/usr/share/xsessions`

## Primary Source Findings

### GNOME Remote Login

GNOME’s own user documentation says Remote Login is the GNOME-supported path for logging into a user account over RDP, uses port `3389`, and recommends default settings with `mstsc` on Windows.

Source:

- https://help.gnome.org/gnome-help/remote-login.html

### GNOME session requirements

GNOME’s own system administration guide explicitly states:

- ensure `gnome-session-xsession` is installed
- available sessions are found in `/usr/share/xsessions`

Source:

- https://help.gnome.org/system-admin-guide/session-user.html

## Root Cause Assessment

### High-confidence root cause

The host has GNOME Remote Desktop and GDM enabled, but does not currently have a usable X session entry for GDM remote login.

Evidence chain:

1. GNOME documents that user sessions for GDM are tied to `gnome-session-xsession` and `/usr/share/xsessions`.
2. This host does not have `gnome-session-xsession` installed.
3. This host does not have `/usr/share/xsessions/gnome.desktop` or equivalent X session desktop files.
4. `gdm` logs repeatedly say:
   - `no session desktop files installed, aborting...`
5. `gdm` then crashes and restarts.

### Secondary effect

The Windows-side authentication error is likely a downstream symptom, not the first cause.

Inference from logs:

- the client reaches the server
- CredSSP/NLA negotiation begins
- the server-side login/session path is unstable because GDM cannot provide a valid session target
- the client therefore surfaces a generic authentication failure

## Decision-Relevant Conclusion

GNOME Remote Desktop itself is no longer the primary blocker.

The primary blocker is the incomplete GNOME login/session stack on this Arch host, specifically the missing X session path expected by GDM remote login.

## Resolution Paths

### Path A: Repair GNOME remote login

Likely next actions:

- install `gnome-session-xsession`
- verify `/usr/share/xsessions` entries appear
- restart `gdm.service`
- retest RDP login

Pros:

- preserves the current GNOME remote-login strategy
- likely the smallest change from the current deploy state

Risks:

- GDM has already shown crash loops on this host
- even after package repair, further GNOME-specific stabilization may still be needed

### Path B: Switch desktop track to XFCE + xrdp

Pros:

- often more predictable on headless VPS hosts
- avoids continuing down a currently unstable GDM path

Risks:

- broader install/configuration change
- discards some of the work already done on GNOME Remote Login

## Recommended Next Step

Proceed to:

- `APPLY GNOME Remote Login Repair`

Default recommendation:

- try the narrow repair first by adding the missing GNOME X session path
- only pivot to `XFCE + xrdp` if the repair does not stabilize GDM
