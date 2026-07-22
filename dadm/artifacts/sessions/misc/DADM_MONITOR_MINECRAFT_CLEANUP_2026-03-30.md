# DAD-M Monitor: Minecraft Cleanup

Date: 2026-03-30
Phase: MONITOR
Track: MINECRAFT-CLEANUP
Decision: pass

## Scope Reviewed

Targeted cleanup for:

- `mc-atm10.service`
- `mc-friends.service`

Out of scope:

- `cottagewitch-recast.service`
- non-Minecraft services

## Evidence

Verification timestamp:

- `2026-03-30T16:21:53+02:00`

Service state:

- `mc-atm10.service`
  - current state: `inactive (dead)`
  - stop timestamp: `2026-03-30 16:17:02 CEST`
  - previous memory peak: `10.3G`

- `mc-friends.service`
  - current state: `failed`
  - stop timestamp: `2026-03-30 16:16:56 CEST`
  - main process exited with `status=130`
  - previous memory peak: `5.5G`

Process verification:

- no active process remains for:
  - `neoforge/21.1.219`
  - `forge/1.19.2-43.4.2`
  - `mc-atm10`
  - `mc-friends`

Memory verification:

- before cleanup:
  - `used`: `28Gi`
  - `free`: `274Mi`
  - `available`: `3.3Gi`
  - `swap used`: `511Mi`

- after cleanup:
  - `used`: `16Gi`
  - `free`: `12Gi`
  - `available`: `15Gi`
  - `swap used`: `95Mi`

## Result

Cleanup goal achieved.

Both requested Minecraft instances are no longer running, and the VPS recovered a large amount of RAM and swap headroom.

## Notes

`mc-friends.service` stopped successfully from an operations perspective, but systemd records the final state as `failed` because the process exited with code `130` during shutdown.

This is not a blocker for the cleanup objective, because the service is no longer active and the associated Forge process is gone.

If a cleaner idle state is desired later, a follow-up housekeeping step can run:

- `systemctl reset-failed mc-friends.service`

## Recommended Next Step

Proceed to either:

- `Discover Server Desktop Track`
- or `Apply Server Desktop Track`

with the new memory headroom now available.
