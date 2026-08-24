# Roll-Drauf Domain Context

## Identity and accounts

**User account** is the local account that owns a profile, sessions, campaigns,
and characters.

**Standard login** is authentication with the account's email address and
password. A username remains a display and compatibility identifier, not the
canonical login identity.

**Discord identity link** is an optional external identity associated with a
local user account. It can provide a convenient login route when the Discord
server and bot authorize it; it does not replace the local account.

**Account state** describes whether an account is usable, deactivated, under a
deletion request, or permanently deleted. An unusable account cannot enter
protected areas.

## Authorization

**Platform role** is a global operational role such as owner, admin, moderator,
or supporter. It grants narrowly scoped staff capabilities across campaigns.

**Profile tier** describes the account's product entitlement and capacity,
such as player, DM, or headmaster. It is not a substitute for a platform role.

**Campaign role** is a user's relationship to one campaign: owner/DM, co-DM,
player, or observer. It controls what that user may do inside that campaign.

**Resource relationship** is the concrete ownership or membership relationship
used to authorize access to a campaign, session, map, character, or token.

**RBAC boundary** means that every protected operation evaluates the account's
usable state, then the relevant platform role, campaign role, or resource
relationship. A role from one boundary does not implicitly grant rights in
another boundary.

## Access defaults

**New standard account** starts as a least-privilege Player with no platform
role. An invitation key may grant an explicitly assigned profile tier; it does
not silently grant platform staff privileges.

## Product surfaces

**VTT overview** is the protected personal starting point for campaigns,
characters, session preparation, and the live table. Its content must remain
useful when a user has no Discord account and no Discord membership.

**Discord integration** is an optional external identity and community
connection. Discord login, server membership checks, and community messaging
must not be prerequisites or primary content on the VTT overview.

**Guild** is a Discord/community metadata concept, not a VTT workspace
resource. Guild data may remain available to the optional integration boundary,
but it is not shown, ranked, or created by the VTT overview.
