# Roll-Drauf authorization baseline

The application uses two authorization layers. Platform roles govern operator
and moderation work; campaign roles govern a user's relationship to one
campaign. A token claim or a client-side badge never grants access.

## Platform roles

| Role | Scope | Allowed work |
| --- | --- | --- |
| No platform role | Own account and joined campaigns | Use assigned campaign/session features |
| Supporter | Cross-campaign read/support scope | Support and inspect the surfaces explicitly assigned to support |
| Moderator | Community-wide moderation | Review reports, apply or revoke moderation actions |
| Admin | Platform administration | Manage users, roles, quotas, registration keys, and operational settings |
| Owner | Full platform scope | Admin work plus role assignment and deployment-level decisions |

`profile_tier` controls product quota and availability. It is not a substitute
for a platform role and must not be used as an authorization shortcut.

### Profile tiers

| Profile tier | Product capability |
| --- | --- |
| Player | Participate in joined campaigns and assigned sessions |
| DM | Create and operate campaigns within quota |
| Headmaster | Create and operate campaigns with elevated capacity |

## Campaign roles

| Role | Read campaign | Manage members/assets | Control live session |
| --- | --- | --- | --- |
| Owner/DM | Yes | Yes | Yes |
| Co-DM | Yes | Yes, within assigned campaign | Yes |
| Player | Yes, while a member | Own character and assigned session actions | Only actions granted by the session |
| Observer | Read-only published context | No | No |

Every campaign, character, map, asset, token, chat message, and game session
check must verify the resource's campaign relationship before checking the
operation. Unknown IDs return the same denial shape as a resource the caller
cannot see.

## Recovery and role-change rules

- Password reset changes the password, consumes the reset token, and revokes
  the account's active sessions. It does not log the account in or bypass MFA.
- Email, MFA, platform-role, and campaign-role changes require an authenticated
  account and the appropriate step-up check.
- Role assignment is restricted to Owner/Admin code paths and is audited.
- Suspension and account lifecycle state are checked before every login and
  every authenticated request.

## Implementation order

1. Keep one browser auth path: email/username login with optional Discord
   linking, server-side session revocation, and the password-reset flow.
2. Add negative tests for guessed IDs, cross-campaign reads/writes, role
   escalation, suspended users, and stale sessions.
3. Complete refresh-token rotation/reuse detection and publish session
   termination controls before adding more privileged surfaces.
