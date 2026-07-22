# Apply Output

```
artifact: apply-output
milestone: TRACK-B-DISCORD-LOGIN-BOT-SSOT-2026-03-30
phase: APPLY
status: complete
date: 2026-03-30
```

## Input Summary

This Apply pass worked from:

- `docs/DADM_SESSION_CONTROL_2026-03-30_VTT.md`
- `docs/DADM_APPLY_VTT_SESSION_BOUNDARY_2026-03-30.md`
- `M01_DISCOVER_Discord_Login_Bot_SSOT.md`
- `M02_APPLY_Discord_Login_Bot_SSOT.md`
- `M03_DEPLOY_Discord_Login_Bot_SSOT.md`
- the current Track B file state in:
  - `vtt_app/auth/routes.py`
  - `vtt_app/auth/discord_oauth.py`
  - `vtt_app/models/discord_identity_link.py`
  - `vtt_app/models/__init__.py`
  - `vtt_app/config.py`
  - `.env.example`
  - `.env.vtt.roll-drauf.de.example`
  - `vtt_app/templates/login.html`

## Observed Current State

Track B is not only planned; it already has partial repo-local implementation in progress.

Observed in the current codebase:

- Discord config flags and environment keys already exist
- Discord OAuth helper code already exists
- Discord start, status, and callback routes already exist
- a `discord_identity_links` model already exists
- the backend already assumes a signed bot-verification HTTP contract
- password and MFA login still exist and remain functional as the legacy fallback path
- Track A closure removed the Discord entry action from `login.html`, so Track B now needs a bounded UI re-entry point rather than a geometry rewrite

## Apply Decisions

### D1. Identity key

Approved identity key for Track B remains:

- `discord_user_id`

Rejected as authority keys:

- Discord username
- Discord global display name
- Discord nickname
- Discord email

### D2. Authority boundary

Approved authority split for Track B:

- bot decides whether the Discord identity is allowed as a player
- VTT owns local link persistence, cookie/session creation, and redirect UX
- VTT must fail closed if bot verification fails, times out, or returns denied

### D3. Fallback policy

For this session, password/MFA login remains the approved fallback path.

This is already aligned with the current repo state:

- `POST /api/auth/login` still exists
- MFA follow-up still exists
- Discord login is config-gated and not treated as the only entry path

### D4. Linking policy

The approved Track B linking policy for the next Deploy step is the narrower one already implied by the code:

- Discord login may reuse an existing `discord_identity_links` row
- otherwise it may link only to an already existing VTT account
- first-time Discord login does **not** auto-create a new VTT account
- email may be used as a lookup hint to find an existing VTT account, but never as the authorization key
- a valid consumed `RegistrationKey` remains required before first link completion

### D5. Bot contract shape

The approved integration shape for the next Deploy step is the repo-local contract already encoded in `vtt_app/auth/discord_oauth.py`:

- HTTP `POST` verification request
- JSON payload containing `discord_user_id`, `guild_id`, purpose, and state
- authenticated by shared-secret HMAC
- replay-mitigation headers via timestamp and nonce

This contract is accepted as the local integration target for the repo.

### D6. UI boundary

Track A remains closed.

That means Track B may reintroduce only the minimum Discord login entry surface needed for the identity flow:

- a bounded Discord CTA
- bounded Discord error presentation
- no reopening of Track A geometry decisions unless a concrete blocker is proven

## Deploy Boundary For Track B

Track B may now proceed only within this bounded Deploy scope:

- stabilize the existing backend Discord flow against the approved linking and fallback policy
- reintroduce the minimal login-page entry point required to start Discord OAuth
- preserve Track A layout closure
- keep `DISCORD_LOGIN_ENABLED` off by default in examples/config
- avoid any production-only assumption that the bot endpoint is already reachable

Track B may **not** in the next Deploy step:

- remove password login
- auto-create VTT accounts from Discord login
- authorize by username or display label
- treat the external bot contract as production-verified when it is only repo-local

## Deploy Readiness Decision

Decision: `conditional-approve`

Meaning:

- Track B may proceed to a bounded Deploy step for repo-local integration hardening
- Track B is **not** yet approved for production enablement or closure
- the next Deploy step should focus on internal consistency, bounded UI re-entry, and testability

## Acceptance Criteria

```text
AC-TRACK-B-01: Track B decisions are grounded in the current repo implementation, not only in the earlier plan documents.
AC-TRACK-B-02: Password/MFA fallback is explicitly retained for this session.
AC-TRACK-B-03: The approved linking policy is narrowed to existing-account linking only, with no Discord-driven account creation.
AC-TRACK-B-04: The bot verification contract shape is explicit enough for bounded local Deploy continuation.
AC-TRACK-B-05: Track B is allowed to continue only as a bounded Deploy step, not as silent production activation.
```

## Risks and Open Gates

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | No evidence exists yet that the real bot verification endpoint is reachable and contract-compatible. | `high` | yes |
| R2 | No dedicated positive/negative tests were validated for the Discord callback and denial paths in this session. | `high` | yes |
| R3 | `login.html` is still the shared join point between Track A closure and Track B re-entry. | `medium` | yes |
| R4 | The new `discord_identity_links` persistence path is present in code, but production rollout evidence for schema readiness is not yet established here. | `medium` | yes |
| R5 | The flow currently depends on Discord email for first-time linking to an existing account. That is acceptable for this session, but it is still a design constraint to document clearly. | `low` | no |

## Next Step

Proceed to a bounded `DEPLOY` step for Track B that hardens the repo-local Discord path and reintroduces the minimal login CTA without reopening Track A layout scope.
