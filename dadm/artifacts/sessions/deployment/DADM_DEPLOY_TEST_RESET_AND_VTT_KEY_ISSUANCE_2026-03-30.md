# Deploy Output

```
artifact: deploy-output
milestone: TEST-RESET-AND-VTT-KEY-ISSUANCE-2026-03-30
phase: DEPLOY
status: complete
date: 2026-03-30
```

## Input Summary

This Deploy pass worked from:

- the user request to clear the VTT user state for a fresh end-to-end onboarding run
- the user request for a bot command that can assign a single-use registration key and let the target user retrieve it later

## Implementation Summary

This pass delivered a bounded MVP across the VTT repo and the bot work repo.

Implemented outcome:

- the VTT user-space test data was backed up and then reset
- the VTT repo now exposes internal bot-authenticated registration-key endpoints
- the bot work repo now contains `/vtt assign_key` and `/vtt claim_key`
- the VTT production env example was aligned with the current VPS Discord wiring for non-secret values

## Files Changed

In the VTT repo:

- `vtt_app/endpoints/registration_keys.py`
- `.env.vtt.roll-drauf.de.example`
- `docs/proofs/vtt_pre_reset_backup_2026-03-30.sql`

In the bot work repo:

- `rolldrauf_bot/config/settings.py`
- `rolldrauf_bot/main.py`
- `rolldrauf_bot/cogs/vtt_access.py`

## Proofs

Targeted verification completed in this Deploy pass:

1. VTT endpoint syntax validation
   - `venv/bin/python -m py_compile vtt_app/endpoints/registration_keys.py`
2. Bot work-repo syntax validation
   - `.venv/bin/python -m py_compile rolldrauf_bot/config/settings.py rolldrauf_bot/cogs/vtt_access.py rolldrauf_bot/main.py`
3. Internal endpoint behavior proof via Flask testing app
   - `GET /api/internal/registration-keys/assigned/<discord_user_id>` returned an empty assignment list before issuance
   - `POST /api/internal/registration-keys/issue` returned `201` with a generated single-use key
   - the follow-up assigned-key lookup returned the new key
4. Destructive reset safety proof
   - pre-reset backup created at `docs/proofs/vtt_pre_reset_backup_2026-03-30.sql`
   - post-reset production DB counts confirmed zero for:
     - `users`
     - `sessions`
     - `campaigns`
     - `campaign_members`
     - `discord_identity_links`
     - `registration_keys`

## Acceptance Checklist

- [x] VTT onboarding state was reset for a fresh test run
- [x] Backup was captured before the reset
- [x] The new key-issuance path supports assignment by Discord user id
- [x] The retrieval path can return the active assigned key for a Discord user
- [x] The bot-side command surface exists in the bot work repo

## Residual Risks And Next Step

- `high`: The running bot dev instance under `/opt/rolldrauf-bot-dev` does not yet contain the new `/vtt` command code.
- `high`: The running bot dev instance still does not have the verifier HTTP server enabled.
- `medium`: The live VTT container has not been restarted to serve the new internal registration-key endpoints.
- `medium`: The new bot command currently depends on VTT API configuration in the bot environment (`VTT_API_BASE_URL`, `VTT_API_SHARED_SECRET` or the verifier secret fallback).

Next step:

- move to `MONITOR` if you want a strict assessment of what is still missing for a real live end-to-end run, or continue with a bounded live rollout of the VTT and bot dev instances
