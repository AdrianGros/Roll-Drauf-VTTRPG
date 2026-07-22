# DAD-M Milestone Plan — M03 Deploy: Discord Login & Bot SSOT
date: 2026-03-29
status: draft
basis: M01 Discover and M02 Apply for Discord identity linking and bot-backed player authorization
source_of_truth: Discord bot is the single source of truth for Discord user identity and player eligibility

## Objective
Implement the Discord login flow in the VTT, verify Discord identity through OAuth2, and gate access through the production bot before creating or reusing a local VTT session.

## Target Outcome

- The login screen exposes `Mit Discord anmelden`.
- Discord OAuth2 is used as the entry point for players.
- The VTT receives a stable `discord_user_id` from Discord.
- The VTT verifies that identity against the bot before granting access.
- The bot decides whether the Discord user is a valid player.
- The VTT creates or reuses the local session only after a positive bot response.

## Scope

- Login UI changes in the VTT
- OAuth2 start route
- OAuth2 callback route
- Bot verification call from the VTT backend
- Local Discord link persistence
- Session creation after bot approval
- Logging, audit, and denial handling
- Tests for positive and negative auth paths

## Non-Goals

- Replacing all password/MFA login paths in one step
- Trusting Discord usernames as identity
- Moving player truth into the VTT
- Implementing unofficial Discord automation
- Directly reading the bot database from the VTT

## Implementation Plan

### 1. UI entry point
- Add a clear Discord login action on the login screen
- Keep the existing book UI intact
- Present Discord as the identity provider, not just a social link

### 2. OAuth start endpoint
- Generate and store `state`
- Redirect to Discord authorization URL
- Request minimal necessary scopes
- Bind the `state` to the initiating session

### 3. OAuth callback endpoint
- Validate `state`
- Exchange the Discord `code` for an access token
- Fetch the Discord profile using the token
- Extract the stable `discord_user_id`

### 4. Bot verification
- Call the production bot verification endpoint
- Send `discord_user_id`, `guild_id`, purpose, and correlation metadata
- Receive `allowed/denied` and `player` status
- Fail closed on timeout, malformed response, or auth error

### 5. Local link and session
- If allowed, create or update the local Discord link
- Create the local JWT/session only after approval
- Reuse an existing link if it matches the same Discord identity
- Reject conflicting links unless a separate relink flow is explicitly designed

### 6. Denial handling
- Show a clear non-technical error if the bot denies access
- Do not create a local session on denial
- Log the denial for audit and support

## Recommended Backend Changes

### New data model or fields
- `discord_identity_links` table
- `discord_user_id` unique and indexed
- `discord_guild_id`
- `discord_username_snapshot`
- `link_status`
- `last_verified_at`
- `revoked_at`

### New routes
- `GET /api/auth/discord/start`
- `GET /api/auth/discord/callback`
- Optional: `POST /api/auth/discord/unlink`
- Optional: `GET /api/auth/discord/status`

### New service layer
- Discord OAuth helper
- Bot verification client
- Link persistence helper
- OAuth state helper

## Bot Contract for Deploy

The VTT expects the bot to expose a signed verification endpoint such as:

```json
{
  "discord_user_id": "123456789012345678",
  "guild_id": "987654321098765432",
  "vtt_user_id": 42,
  "purpose": "login",
  "state": "<oauth-state>"
}
```

Expected response:

```json
{
  "allowed": true,
  "player": true,
  "role": "player",
  "reason": null,
  "verified_at": "2026-03-29T18:00:00Z"
}
```

Denied response:

```json
{
  "allowed": false,
  "player": false,
  "reason": "not_in_player_list"
}
```

## Security Requirements

- Use OAuth2 Authorization Code Grant only
- Validate `state` on callback
- Keep Discord client secrets server-side only
- Fail closed if the bot is unavailable
- Treat Discord username/display name as display-only metadata
- Log link, approval, denial, and revocation events

## Test Plan

### Positive paths
- Discord user logs in successfully
- Bot returns allowed player
- Local VTT session is created
- Existing linked user logs in again without duplicate link

### Negative paths
- Invalid OAuth `state`
- Discord callback missing code
- Discord token exchange fails
- Bot verification times out
- Bot returns denied
- Existing link conflicts with another VTT account

### Regression checks
- Existing password login continues to work unless intentionally disabled
- MFA flow remains intact
- Refresh cookies still rehydrate sessions
- Login UI remains book-stable on desktop and mobile

## Acceptance Criteria

- Discord login can be initiated from the VTT
- The callback creates a stable Discord identity link
- The bot is consulted before any session is granted
- Unauthorized Discord users are denied
- Authorized players can enter the VTT with a local session
- The flow is observable through logs and audit entries
- The implementation is compatible with the current cookie/JWT session model

## Risks and Assumptions

- `high`: Bot availability is now on the login critical path
- `high`: OAuth or callback mistakes can lock users out if not tested carefully
- `medium`: Existing auth UX may need careful coexistence with Discord login
- `medium`: Relink and account migration rules need explicit handling
- `low`: Display name snapshot mismatches are acceptable because they are not authoritative

## Dependencies

- M01 Discover approved
- M02 Apply approved
- Discord developer application configured
- Bot verification endpoint or signed contract available
- Final decision on whether password login remains as fallback

## Priority

P1

## Source References

- Discord OAuth2 Authorization Code Grant, `state`, scopes, bot separation: [Discord OAuth2](https://docs.discord.com/developers/topics/oauth2?sa=D&source=editors&usg=AOvVaw1nL7mE4dLNI_zvQHDnUgCm&ust=1648698859771000)
- Current VTT auth stack: [vtt_app/auth/routes.py](/home/admin/projects/roll-drauf-vtt/vtt_app/auth/routes.py)
- Current login UI: [vtt_app/templates/login.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/login.html)
- Current cookie auth helper: [vtt_app/static/js/auth.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/auth.js)

