# B07 — local shapes and authorized vision verification

Status: Apply complete. Retention permanent. Input: B07 Discover, S06–S08.

Add a visible native shape selector beside the existing measurement tool. Modes:
waypoint distance (existing default), cone, circle/sphere projection and square.
Each non-line shape uses an origin and endpoint; a third click starts a new shape.
Pointer preview, Escape/right-click cancellation and tool-switch clearing remain.
Mouse and existing touch long-press entry paths both use the same geometry.

Circle origin is its center; endpoint gives Euclidean radius. Square origin is
a corner; the larger axis delta gives equal side lengths in the indicated
quadrant. Cone origin is its apex, endpoint sets axis length and direction; base
width equals axis length, matching the official SRD cone definition. Labels name
radius, side length or cone length, using the existing map scale/unit formatting.
Grid snapping still controls input points; geometry itself uses pixel coordinates.
Overlays are local/transient, do not mutate state or broadcast, and are available
in each independently authorized presentation surface.

Vision verification: update legacy fixtures to enter explicit authorized table
contexts, including socket join/action context payloads. Check real DM wall and
light placement, editing/deleting, reload persistence and Player denial/data
projection. Keep the existing domain geometry tests. A freshly confirmed app
defect requires its own recorded correction before release; an un-reproduced
report is not labeled as a fixed bug.

Presentation correction: move existing wall/light viewport listener registrations
out of the shared `_bindViewportNavigation` into `_bindVisionViewport` in the
existing `PlayDMSurface.methods`, called only by `_bindVisionControls`. Player
composition must never initialize those listeners. Keep common measurement,
view navigation and domain rendering independent; retain every server guard.

Acceptance: correct geometry/labels in all shape modes at grid and free scales;
keyboard cancellation; desktop and mobile role journeys; no Player DM handlers;
permission and vision/fog tests; DM wall/light UI persistence and visible effect.
No new dependency, schema or server transport contract for measurement shapes.

Confirmed measurement interaction correction: treat null/absent token IDs as
deselection, never numeric zero, and skip token selection/drag listeners while
the measurement tool is active. Measuring over blank space or a token must not
open the token dock or move a token. Existing normal selection remains reachable.

Deploy handoff: implement after B06 delivery, focused browser/domain/context
checks, commit/push, guarded app-only overlay on the actual current image,
authenticated normal navigation for both roles, scoped fixture cleanup, proof
and rollback record. Medium geometry/context risks are handled by these explicit
contracts and checks; no unresolved product decision is carried into Deploy.
