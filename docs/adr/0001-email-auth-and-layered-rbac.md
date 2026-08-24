# ADR-0001: Email authentication and layered RBAC

- Status: Accepted
- Date: 2026-08-24

## Context

The application already contains local user accounts, invitation-key
provisioning, Discord OAuth, platform roles, profile tiers, and campaign
membership roles. The previous entry flow treated Discord as the only public
authentication path and redirected standard signup routes away from the
application. That prevented normal users from creating and using a local
account and made the authorization boundaries difficult to reason about.

## Decision

1. Email/password is the canonical standard authentication flow.
2. Discord OAuth remains available as an optional identity link/login path;
   its server and bot checks still apply when that path is used.
3. Public registration creates a least-privilege Player account by default.
   Registration keys remain optional on standard signup and can apply their
   explicitly assigned profile tier. Key-only registration remains available
   for invitation workflows.
4. Authorization is layered: platform roles govern staff operations, campaign
   roles govern campaign operations, and resource relationships govern access
   to concrete campaigns and sessions. Account usability is checked before any
   of those grants are considered.

## Consequences

- Users can access the site without joining Discord.
- Discord remains useful without becoming a hidden prerequisite.
- A normal user cannot obtain platform access merely by registering or knowing
  a campaign-level role.
- Existing username logins remain compatible while the UI and API prefer email.
- Future permissions should be added to the narrowest applicable boundary,
  rather than expanding a global role.

## Rejected alternatives

- Redirecting signup to Discord: it hides the missing account flow instead of
  implementing one.
- Treating the legacy account role as the only authorization source: it cannot
  express platform staff scope, campaign membership, and resource ownership
  independently.
