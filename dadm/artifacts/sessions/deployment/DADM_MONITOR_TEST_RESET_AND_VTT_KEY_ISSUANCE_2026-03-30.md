# Monitor Output

```
artifact: monitor-output
milestone: TEST-RESET-AND-VTT-KEY-ISSUANCE-2026-03-30
phase: MONITOR
status: complete
date: 2026-03-30
```

## Input Summary

This Monitor pass worked from:

- `docs/DADM_DEPLOY_TEST_RESET_AND_VTT_KEY_ISSUANCE_2026-03-30.md`
- the current live VTT runtime on this VPS
- the current live bot dev path under `/opt/rolldrauf-bot-dev`

## Validation Result

The reset portion passes.

The new key-flow portion passes at repo/test-harness level, but does not pass live runtime closure.

## Evidence Summary

Evidence gathered in this Monitor pass:

1. Reset state remains clean in the live VTT database:
   - `users = 0`
   - `sessions = 0`
   - `campaigns = 0`
   - `campaign_members = 0`
   - `discord_identity_links = 0`
   - `registration_keys = 0`
2. The running VTT container has the Discord runtime env loaded:
   - `DISCORD_LOGIN_ENABLED=true`
   - `DISCORD_GUILD_ID=1328724663257268264`
   - `DISCORD_BOT_VERIFICATION_URL=http://172.17.0.1:8787/vtt/discord/verify`
3. The live VTT runtime does **not** expose the new internal key endpoints yet:
   - `https://127.0.0.1/api/internal/registration-keys/assigned/...` returned `404`
   - direct app-container probe to `http://127.0.0.1:5000/api/internal/registration-keys/assigned/...` also returned `404`
4. The live bot dev path under `/opt/rolldrauf-bot-dev` still does not contain:
   - `rolldrauf_bot/cogs/vtt_access.py`
   - `rolldrauf_bot/http/vtt_verify.py`
5. Therefore the running bot dev instance is still behind the work-repo state and cannot yet provide:
   - the new `/vtt assign_key` and `/vtt claim_key` command surface
   - the verifier HTTP path needed by the VTT Discord login flow

## Residual Findings

| # | Description | Severity |
|---|---|---|
| F1 | The live VTT user reset is successful and stable. | `low` |
| F2 | The internal registration-key endpoints are not deployed into the running VTT app yet. | `high` |
| F3 | The live bot dev instance under `/opt/rolldrauf-bot-dev` does not yet contain the new `/vtt` command code. | `high` |
| F4 | The live bot dev instance also lacks the verifier HTTP implementation in its deployed path. | `high` |
| F5 | Because both live rollout gaps remain, a real end-to-end Discord onboarding test is still blocked. | `high` |

## Recommendation

Recommendation: `rework`

Meaning:

- the reset can be considered complete
- the key-flow work cannot be considered operationally complete yet
- the next bounded step is a live rollout step, not another design/document-only pass

## Next Action

Run a bounded live Deploy follow-up that:

- rolls the VTT app onto the new internal registration-key endpoint code
- rolls the bot dev instance onto the new `vtt_access` and verifier code
- enables the required bot env values
- captures a live proof using the real running services on this VPS
