# DAD-M Deploy: Live Rollout

Date: 2026-03-30
Phase: DEPLOY
Scope: Discord login bot verifier + VTT internal registration-key live rollout on VPS
Status: complete

## Changes Applied

- Rebuilt the live VTT app container from `/home/admin/projects/roll-drauf-vtt` with `docker compose -f docker-compose.vtt.roll-drauf.de.yml up -d --build app`.
- Rolled the prepared bot changes into `/opt/rolldrauf-bot-dev`:
  - `rolldrauf_bot/main.py`
  - `rolldrauf_bot/config/settings.py`
  - `rolldrauf_bot/cogs/vtt_access.py`
  - `rolldrauf_bot/http/__init__.py`
  - `rolldrauf_bot/http/vtt_verify.py`
  - `requirements.txt`
- Updated `/opt/rolldrauf-bot-dev/.env` with live verifier and VTT API settings:
  - `VTT_VERIFY_ENABLED=true`
  - `VTT_VERIFY_HOST=0.0.0.0`
  - `VTT_VERIFY_PORT=8787`
  - `VTT_VERIFY_ALLOWED_GUILD_ID=1328724663257268264`
  - `VTT_VERIFY_SHARED_SECRET=<live secret>`
  - `VTT_API_BASE_URL=https://vtt.roll-drauf.de`
  - `VTT_API_SHARED_SECRET=<live secret>`
- Patched the bot package loader collision in the bot worktree and live path:
  - `rolldrauf_bot/cogs/setup/__init__.py` now exports an async `setup(bot)` entry point.
- Started the dev bot as a persistent host service via the existing `rolldrauf-bot-dev.service`.

## Runtime Proof

- Live VTT key assignment read endpoint no longer returns `404`:
  - `GET https://127.0.0.1/api/internal/registration-keys/assigned/194552061889740800`
  - result: `200 {"assignments":[],"discord_user_id":"194552061889740800"}`
- Live Discord status endpoint is enabled:
  - `GET https://127.0.0.1/api/auth/discord/status`
  - result: `200 {"enabled":true}`
- Live bot verifier is bound and answering:
  - `POST http://127.0.0.1:8787/vtt/discord/verify`
  - result without signature headers: `401 {"reason":"missing_signature_headers", ...}`
- Live dev bot service is active:
  - `rolldrauf-bot-dev.service`
  - `Main PID: 2019483`
  - current boot policy: `disabled`
- Live dev bot startup log confirms:
  - `/vtt assign_key`
  - `/vtt claim_key`
  - `VTT verifier started on 0.0.0.0:8787`

## Notes

- The live bot was not left running via an ad-hoc shell process. It was attached to the existing host systemd unit `rolldrauf-bot-dev.service` to avoid helper-container lifetime issues.
- The service is currently `active` but not `enabled` for boot. This deploy does not change reboot policy.
- No live registration key was pre-issued in this deploy step. The path is ready, but user-facing issuance remains an intentional action through the bot command path.
- Push remains deferred behind the current session, as agreed.

## Next Allowed Step

MONITOR live rollout with one real end-to-end Discord user flow:

1. Run `/vtt assign_key` for the intended Discord user.
2. Run `/vtt claim_key` as that user.
3. Complete Discord login against `vtt.roll-drauf.de`.
4. Verify `discord_identity_links` and final VTT session state.
