# B07 vision event and reload correction

Status: Discover / Apply complete; retention permanent. Input: second live B07
journey after the separately tested PostgreSQL ID repair.

Observed: light edits save `bright_radius=300, dim_radius=350` in PostgreSQL,
while the active DM view retains radius 100. Every private `fog:updated` advances
the session-wide sequence but reaches only its owner. Other clients see a gap
on the next shared event and resync. Resync reloads bootstrap, which contains no
vision geometry or fog, and the UI skips geometry reload for an unchanged map.
The Player UI never fetches persisted own fog on entry/reload. Medium delivery
blocker; this explains stale vision with real fog enabled. The initial local UI
fixture had fog disabled, so it did not exercise this sequence path.

Design: retain private fog payloads and the existing shared sequence contract.
For each private fog event, emit to its owner first, then a payload-free
`state:tick` with the same sequence to the session. The owner's duplicate tick
is discarded normally; every other authorized connection receives a contiguous
sequence without fog contents. Reuse this helper for geometry changes, token
movement/sight updates and fog reset. Keep all existing context delivery guards.

On explicit bootstrap recovery, reload auxiliary vision data as well. A Player
fetches only its own fog via the existing authorized GET endpoint, never wall or
light geometry. Reset stale map data immediately; with fog enabled and no saved
fog, an empty mask remains covered until an authorized vision update. Drop old
map/request responses and older fog versions. DM geometry fetches retain their
own request ordering. No new context, room, permission, schema or dependency.

Acceptance: two real clients, fog-enabled map, two successive light edits and
wall edits visibly update without reload; own fog survives reload/reconnect;
private contents never arrive at other users; all recipients receive sequence
positions; Player still initializes no DM controls/listeners and gets geometry
403s. Verify real sockets/domain and browsers, then commit/push, app-only overlay
on the actual B07 image, repeat live journeys and remove scoped fixtures.
Previous image is rollback; the additive ID repair stays compatible with it.
