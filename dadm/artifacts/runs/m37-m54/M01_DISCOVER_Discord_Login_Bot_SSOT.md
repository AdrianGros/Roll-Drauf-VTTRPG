# DAD-M Milestone Plan — M01 Discover: Discord Login & Bot SSOT
date: 2026-03-29
status: draft
basis: Current VTT auth stack with JWT cookies, MFA, and login-book UI
source_of_truth: Discord bot is the single source of truth for Discord user identity and player eligibility

## Objective
Define the current-state auth flow and the target Discord login flow for the VTT so that the bot remains the single source of truth for Discord identity and player access.

## Current State

### VTT Auth
- Username/password login exists in [vtt_app/auth/routes.py](/home/admin/projects/roll-drauf-vtt/vtt_app/auth/routes.py)
- MFA is TOTP-based and already works as a second login factor
- JWT access and refresh cookies are already used
- Refresh cookies can now be made persistent via the login `remember_me` flag
- The login screen already supports an MFA follow-up step in [vtt_app/templates/login.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/login.html)

### Data Model
- `User` currently has password, MFA, session tracking, platform role, and profile tier
- There is no Discord identity field yet on the user model
- There is no Discord link table yet
- There is no bot-backed verification contract yet

### Existing Access Control
- Campaign and session access currently rely on VTT user/session state and campaign membership
- Discord is only mentioned in copy and branding, not as an auth provider

## Key Findings

1. Discord-Username is not a safe identity key.
2. Discord user ID must be treated as the stable identity.
3. The bot, not the VTT, must decide whether a Discord identity is an allowed player.
4. The VTT should only manage local session state and account linking.
5. OAuth2 `state` must be used to bind the Discord redirect back to the initiating VTT session.

## Target Flow

1. User clicks `Mit Discord anmelden` in the VTT.
2. VTT redirects to Discord OAuth2 authorization code flow.
3. Discord returns an authorization `code` to the VTT callback.
4. VTT exchanges the code for a Discord access token.
5. VTT fetches the Discord identity using `identify` scope.
6. VTT extracts the stable `discord_user_id`.
7. VTT asks the bot whether this Discord ID is allowed and whether the user has `player` status.
8. If the bot returns allowed, the VTT creates or links the local account and session.
9. If the bot returns denied, the VTT blocks access and shows a clear error.

## Bot SSOT Contract

The bot owns:
- the canonical Discord user ID
- the guild membership truth
- the player/non-player decision

The VTT owns:
- local user records
- login sessions and cookies
- the visual login flow
- optional display-name snapshots for UI only

## Recommended Data Model Direction

### New fields or tables to add later
- `discord_user_id`
- `discord_guild_id`
- `discord_linked_at`
- `discord_username_snapshot` for display only
- optional `discord_link_status`

### Rules
- Never authorize by username or nickname
- Never treat the snapshot as source of truth
- Store only one canonical Discord identity per linked VTT account unless an explicit re-link flow is designed

## Security Requirements

- Use OAuth2 Authorization Code Grant, not implicit flow
- Use `state` to prevent CSRF and redirect tampering
- Keep the Discord client secret only on the backend
- Verify the bot response before granting access
- Fail closed if the bot is unavailable or the Discord user is unknown

## Source References

- Discord OAuth2 Authorization Code Grant, `state`, `identify`, `guilds.members.read`: [Discord OAuth2](https://docs.discord.com/developers/topics/oauth2?sa=D&source=editors&usg=AOvVaw1nL7mE4dLNI_zvQHDnUgCm&ust=1648698859771000)
- Discord bot users and bot authorization flow: [Discord OAuth2](https://docs.discord.com/developers/topics/oauth2?sa=D&source=editors&usg=AOvVaw1nL7mE4dLNI_zvQHDnUgCm&ust=1648698859771000)
- Current VTT login handler: [vtt_app/auth/routes.py](/home/admin/projects/roll-drauf-vtt/vtt_app/auth/routes.py)
- Current login UI: [vtt_app/templates/login.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/login.html)
- Current cookie auth helper: [vtt_app/static/js/auth.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/auth.js)

## Open Questions for M02

1. Should Discord login be mandatory or optional alongside password login?
2. Should linking happen on first Discord login or via a separate account-link step?
3. Does the bot expose a direct HTTP API, a shared database, or a signed verification endpoint?
4. Is a single Discord guild enough, or do we need multi-guild support?
5. Should we keep password login as a fallback for admins, or migrate fully to Discord?

## M01 Acceptance Criteria

- The current auth state and its gaps are documented
- The Discord identity boundary is clear
- The bot SSOT decision is explicit
- The next implementation milestone can proceed without re-litigating identity ownership

