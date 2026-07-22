# DAD-M Monitor: Live Rollout

Date: 2026-03-30
Phase: MONITOR
Scope: Live Discord verifier + registration-key rollout on VPS
Status: conditional-pass
Recommendation: human-e2e-proof

## Verified Live Facts

- `rolldrauf-bot-dev.service` is `active`.
- The bot verifier is bound on `0.0.0.0:8787`.
- `GET /api/auth/discord/status` returns `{"enabled":true}`.
- Signed verifier request for Discord user `194552061889740800` returned:
  - `allowed=true`
  - `player=true`
  - `role=owner`
- Internal key issue path is live and working.
- Internal key assigned-read path is live and working.

## Live Data State

- `users=0`
- `discord_identity_links=0`
- `registration_keys=1`
- Active assigned key exists for Discord user `194552061889740800`
  - batch: `discord-assign-194552061889740800`
  - tier: `player`
  - uses remaining: `1`
  - expires: `2026-04-13T13:29:57.768492`

## Findings

- No server-side blocker remains for the Discord verification decision.
- No server-side blocker remains for assigned registration-key retrieval.
- The live system is now ready for one real Discord user proof pass.
- Full closure is still gated by human interaction, because this monitor step cannot independently execute:
  - `/vtt claim_key` in Discord as the target user
  - browser OAuth login at `vtt.roll-drauf.de`
  - final confirmation that a VTT user row and `discord_identity_links` row are created as expected

## Decision

- Server-side rollout: pass
- End-to-end user proof: pending

## Next Allowed Step

Human proof pass:

1. Run `/vtt claim_key` as Discord user `194552061889740800`.
2. Open the VTT login and complete Discord login.
3. Re-run monitor for final closure against `users`, `discord_identity_links`, and consumed key state.
