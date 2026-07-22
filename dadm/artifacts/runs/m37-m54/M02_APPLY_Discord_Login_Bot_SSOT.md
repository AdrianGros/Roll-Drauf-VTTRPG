# DAD-M Milestone Plan — M02 Apply: Discord Identity Contract & Bot SSOT
date: 2026-03-29
status: draft
basis: M01 Discover findings for Discord login and bot-backed authorization
source_of_truth: Discord bot is the single source of truth for Discord user identity and player eligibility

## Objective
Define the target data model, bot integration contract, and Discord login UX so the VTT can authenticate users via Discord while the bot remains authoritative for player eligibility.

## Target State

- Discord OAuth2 is the primary identity entry point for players.
- The VTT stores only local session state plus a stable Discord link.
- The bot owns the canonical Discord user identity and the player decision.
- The VTT never authorizes by Discord username, nickname, or display name.
- If the bot denies access, the VTT fails closed.

## Scope

- VTT login UI
- OAuth2 start and callback handling
- Discord identity linking
- Bot verification contract
- Local session creation after positive bot verification
- Audit/logging for identity and authorization events

## Non-Goals

- Rewriting the entire VTT auth system
- Trusting Discord usernames as identifiers
- Building a self-bot or unofficial Discord automation
- Moving player-authority logic into the VTT
- Replacing all existing password/MFA flows immediately without a migration decision

## Recommended UX

1. User clicks `Mit Discord anmelden`.
2. VTT redirects to Discord OAuth2 using Authorization Code Grant.
3. Discord returns `code` to the VTT callback with `state`.
4. VTT exchanges the code server-side for a Discord token.
5. VTT fetches the Discord identity via `identify`.
6. VTT receives the stable `discord_user_id`.
7. VTT asks the bot whether that ID is allowed and whether it is a `player`.
8. If allowed, the VTT creates the local session and links the account.
9. If denied, the VTT shows a clear rejection and stores no session.

## Design Decisions

### Identity
- Stable identity key: `discord_user_id`
- Display-only snapshot: `discord_username_snapshot`
- Forbidden as identity: Discord username, global display name, server nickname

### Authority
- Source of truth for access: bot
- Source of truth for local login session: VTT
- Source of truth for account link metadata: VTT database

### Linking Strategy
- Recommended: one canonical Discord link per VTT account
- Relinking should require an explicit unlink/relink path
- Duplicate links should be rejected unless intentionally migrated by an admin flow

## Proposed Data Model

### New table: `discord_identity_links`

Recommended columns:
- `id`
- `user_id` foreign key to VTT `users.id`
- `discord_user_id` unique and indexed
- `discord_guild_id` indexed
- `discord_username_snapshot` nullable
- `bot_verified_role` nullable, e.g. `player`
- `link_status` enum-like string: `pending`, `linked`, `denied`, `revoked`
- `linked_at`
- `last_verified_at`
- `revoked_at`
- `created_at`
- `updated_at`

Recommended rules:
- `discord_user_id` must be unique
- one `user_id` may have at most one active link
- the link row can store snapshots for UI only, not authorization

### Optional additions to `users`
- `discord_linked_at`
- `discord_verified_at`
- `discord_profile_label`

These are optional and should only exist if we need quick profile rendering. They are not the authoritative link.

## Proposed Bot API Contract

The VTT should not read the bot database directly. It should call a bot-owned verification endpoint.

### Verification request

```http
POST /internal/discord/verify-user
Content-Type: application/json
X-Request-Timestamp: 1711740000
X-Request-Nonce: <unique-nonce>
X-Signature: <hmac-or-signed-token>
```

```json
{
  "discord_user_id": "123456789012345678",
  "guild_id": "987654321098765432",
  "vtt_user_id": 42,
  "purpose": "login",
  "state": "<oauth-state>"
}
```

### Verification response

```json
{
  "allowed": true,
  "player": true,
  "reason": null,
  "discord_user_id": "123456789012345678",
  "guild_id": "987654321098765432",
  "role": "player",
  "display_name": "SomeUser",
  "verified_at": "2026-03-29T18:00:00Z",
  "bot_version": "1.0.0"
}
```

### Denied response

```json
{
  "allowed": false,
  "player": false,
  "reason": "not_in_player_list",
  "discord_user_id": "123456789012345678",
  "guild_id": "987654321098765432",
  "verified_at": "2026-03-29T18:00:00Z"
}
```

### Bot contract requirements
- Requests must be authenticated with a shared secret, HMAC, or signed token
- Requests must include replay protection via timestamp and nonce
- Responses should be fail-closed if invalid, stale, or unsigned
- The bot should answer from its own DB or canonical membership store

## OAuth2 Requirements

- Use Authorization Code Grant
- Keep the client secret on the backend only
- Use `state` to bind the callback to the initiating browser/session
- Request only the scopes that are needed
- Recommended scopes:
  - `identify`
  - `guilds.members.read` if the VTT needs member info from Discord directly

## Security Requirements

- Never trust a Discord display name for authorization
- Never create a VTT session before bot approval
- Fail closed on bot timeout, Discord timeout, or callback mismatch
- Store only the minimum necessary identity data
- Log link, verify, deny, and revoke events for auditability

## UX Requirements

- Login page needs a primary `Mit Discord anmelden` action
- The user should understand that Discord is the login identity
- If the bot denies access, show a non-technical message
- If the user is already linked, the flow should be idempotent
- If the user is not yet linked, the flow should either auto-link on first approved login or present a guided link confirmation step

## Implementation Boundaries

- VTT UI is responsible for the redirect and callback presentation
- VTT backend is responsible for OAuth exchange and local session creation
- Bot is responsible for player truth
- Shared DB access is not preferred; API-based verification is preferred

## Acceptance Criteria

- The login flow is defined from click to session creation
- `discord_user_id` is the only identity key used for authorization
- The bot contract is explicit and versionable
- The VTT can store and reuse the local Discord link
- Unauthorized Discord identities cannot enter the VTT
- The design is compatible with the current cookie/JWT session model

## Risks and Assumptions

- `high`: Bot availability becomes part of the login critical path
- `high`: Discord OAuth errors must be handled gracefully or users get blocked
- `medium`: Relinking and account migration can get messy without clear admin rules
- `medium`: If the bot DB schema changes independently, the contract must be versioned
- `low`: Display names may change often, but they are only used as snapshots

## Dependencies

- M01 Discover complete
- Discord application created in the Developer Portal
- Bot-side verification endpoint or signed query contract available
- Chosen linking policy approved

## Priority

P1

## Source References

- Discord OAuth2 Authorization Code Grant, `state`, `identify`, `guilds.members.read`: [Discord OAuth2](https://docs.discord.com/developers/topics/oauth2?sa=D&source=editors&usg=AOvVaw1nL7mE4dLNI_zvQHDnUgCm&ust=1648698859771000)
- Discord bot authorization flow and bot/user separation: [Discord OAuth2](https://docs.discord.com/developers/topics/oauth2?sa=D&source=editors&usg=AOvVaw1nL7mE4dLNI_zvQHDnUgCm&ust=1648698859771000)
- Current VTT auth handler: [vtt_app/auth/routes.py](/home/admin/projects/roll-drauf-vtt/vtt_app/auth/routes.py)
- Current user model: [vtt_app/models/user.py](/home/admin/projects/roll-drauf-vtt/vtt_app/models/user.py)
- Current login UI: [vtt_app/templates/login.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/login.html)

