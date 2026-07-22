# DAD-M Apply: GNOME Remote Login Repair

Date: 2026-03-30
Phase: APPLY
Track: GNOME-REMOTE-LOGIN-REPAIR
Status: approved

## Objective

Repair the existing GNOME Remote Login path by satisfying the missing GDM session requirement, without yet pivoting to a different desktop stack.

## Input Finding

From `DADM_DISCOVER_GNOME_REMOTE_LOGIN_FAILURE_2026-03-30.md`:

- `gnome-remote-desktop` is functioning as an RDP endpoint
- TLS is configured and `3389` is listening
- the active failure is in `gdm`
- `gdm` repeatedly aborts with:
  - `GdmSession: no session desktop files installed, aborting...`
- the host has only Wayland session desktop files
- the host lacks `/usr/share/xsessions/*`

## Decision Summary

The repair track will focus only on restoring a valid GNOME session target for GDM remote login.

This track is approved to:

- add the missing X session layer expected by GDM
- restart the affected services
- retest the same RDP flow

This track is not approved to:

- replace GNOME with XFCE
- install xrdp
- broaden the desktop architecture

## Binding Decisions

### 1. The repair target is the missing GDM session contract

Approved:

- the next deploy step must restore a usable session entry under `/usr/share/xsessions`
- the next deploy step must keep `gnome-remote-desktop` as-is unless service restarts are required

Rejected:

- treating TLS, networking, or Windows client settings as the primary blocker

### 2. Prefer the smallest GNOME-compatible repair

Approved repair order:

1. If an official package providing the GNOME X session path is available in the enabled package sources, use that.
2. If no such package is available on this host, create a minimal local X session desktop entry that points GDM at the already-installed `gnome-session` binary.

Inference:

- this second step is an operational compatibility shim inferred from:
  - GNOME’s requirement for `/usr/share/xsessions`
  - the local presence of `/usr/bin/gnome-session`
  - the local absence of any X session desktop files

Rejected:

- broad package churn unrelated to the missing session files
- switching to another desktop environment before this narrow repair is tested

### 3. The repair remains privileged operations work

Approved:

- root-level package install and/or root-level file creation under `/usr/share/xsessions`
- root-level restart of `gdm.service`
- root-level restart of `gnome-remote-desktop.service`

Rejected:

- attempting to complete the repair from the current unprivileged shell context

### 4. Validation must reuse the existing proof path

Approved:

- verify `gdm.service` becomes stable instead of crash-looping
- verify `gnome-remote-desktop.service` remains active
- verify `3389` remains listening
- retest Windows `mstsc`

Rejected:

- changing multiple variables at once before re-running the same proof

## In-Scope Deploy Work

The next deploy step may:

- install the missing GNOME X-session support if available
- create `/usr/share/xsessions/gnome.desktop` if needed
- create `/usr/share/xsessions/gnome-xorg.desktop` if needed
- restart `gdm.service`
- restart `gnome-remote-desktop.service`
- verify service stability and listener state

## Out-of-Scope Deploy Work

- installing `xfce4`
- installing `xrdp`
- removing the current GNOME RDP setup
- changing VTT services or network topology

## Acceptance Criteria

The repair is ready for monitor when all of the following are true:

- `/usr/share/xsessions` contains at least one valid GNOME session entry
- `gdm.service` stops crash-looping
- `gnome-remote-desktop.service` is still active
- `3389` still listens
- a Windows `mstsc` attempt reaches a GNOME login surface or credential prompt instead of the previous generic authentication failure

## Failure Gate

If the repair deploy completes and:

- `gdm.service` still crash-loops
- or the RDP proof still fails with the same effective behavior

then the next methodically correct step is:

- `APPLY Desktop Pivot XFCE xrdp`

## Recommended Next Step

Proceed to:

- `DEPLOY GNOME Remote Login Repair`
