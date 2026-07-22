# Monitor Output

```
artifact: monitor-output
milestone: TRACK-B-DISCORD-LOGIN-BOT-SSOT-2026-03-30
phase: MONITOR
status: complete
date: 2026-03-30
```

## Input Summary

This Monitor pass worked from:

- `docs/DADM_DEPLOY_TRACK_B_DISCORD_LOGIN_BOT_SSOT_2026-03-30.md`
- the current VTT repo state
- the local bot workspace at `../rolldrauf-bot-dev-work`

## Validation Result

Track B passes bounded repo-local integration validation, but it does not pass environment- or endpoint-readiness closure.

Confirmed in this Monitor pass:

- the VTT repo contains a Discord login flow, a local bot-verification client, and a bounded login-page CTA path
- the bot repo already contains a verifier server implementation in `rolldrauf_bot/http/vtt_verify.py`
- the bot main runtime only starts that verifier when `VTT_VERIFY_ENABLED=true`
- the current bot `.env` does not yet define the verifier settings required to start that server
- the verifier endpoint is not currently listening on the expected local port
- the VTT production example env still has unresolved Discord values

## Evidence Summary

Evidence gathered in this Monitor pass:

1. Bot verifier implementation exists:
   - `rolldrauf_bot/http/vtt_verify.py`
   - route: `POST /vtt/discord/verify`
2. Bot runtime start condition exists:
   - `rolldrauf_bot/main.py` starts `VTTVerifierServer` only when `self.settings.vtt_verify_enabled`
3. Bot config parsing exists:
   - `rolldrauf_bot/config/settings.py` expects:
     - `VTT_VERIFY_ENABLED`
     - `VTT_VERIFY_HOST`
     - `VTT_VERIFY_PORT`
     - `VTT_VERIFY_SHARED_SECRET`
     - `VTT_VERIFY_ALLOWED_GUILD_ID`
     - `VTT_VERIFY_MAX_SKEW_SECONDS`
4. Current bot `.env` state:
   - `ENVIRONMENT=dev`
   - `DEV_GUILD_ID` is set
   - no `VTT_VERIFY_*` values are currently present
5. Runtime probe:
   - `curl http://127.0.0.1:8787/vtt/discord/verify` failed to connect
   - socket check showed no verifier listener on `8787`
6. VTT env example still unresolved:
   - `DISCORD_GUILD_ID` empty
   - `DISCORD_BOT_VERIFICATION_URL` empty
   - `DISCORD_BOT_SHARED_SECRET` empty

## Residual Findings

| # | Description | Severity |
|---|---|---|
| F1 | The bot verifier endpoint is implemented but not enabled in the current bot dev environment. | `high` |
| F2 | The VTT env values needed for bot verification are not yet populated. | `high` |
| F3 | No shared secret has been provisioned across bot and VTT yet. | `high` |
| F4 | The exact runtime target for the verifier URL still needs to be chosen deliberately, even though the default local port shape is visible in code. | `medium` |
| F5 | Track B still lacks a full end-to-end live verification proof against the running bot instance. | `medium` |

## Recommendation

Recommendation: `rework`

Meaning:

- Track B should not be treated as closed
- the next bounded step is configuration and endpoint enablement, not another design-only loop
- that next step should configure the bot verifier and populate the VTT Discord env values coherently

## Next Action

Run a bounded Track B follow-up that:

- enables the bot verifier in the bot dev environment
- provisions a shared secret across bot and VTT
- fills the VTT Discord env values with the chosen guild ID and verifier URL
- captures a live request/response proof against the running verifier
