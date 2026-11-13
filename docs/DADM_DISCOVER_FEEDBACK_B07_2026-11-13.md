# B07 — lighting, walls and measurement discovery

Status: Discover complete for the bounded investigation/measurement slice.
Retention permanent. Input: S06–S08 and the owner's instruction to finish the program.

Inventory: shared transient measurement state/rendering in `play-ui.js`, common
measurement controls in `play.html`; authorized DM vision bindings in
`play-dm.js`, server vision routes/domain under `vtt/play`, and separate Player
composition in `play-player.js`. Existing measurements use waypoints, grid/free
distance and the saved map scale. Shape modes are absent.

Medium presentation finding: the common `_bindViewportNavigation` currently
registers DM wall/light pointer listeners even on the Player surface, although
their tool checks and server contexts restrict execution. Move those listener
registrations into the existing DM-only composition initializer. Server context
authorization remains authoritative; no server privilege bypass was established.

The legacy vision test run reports 14 fixture failures and 11 passing pure
geometry cases. All 14 failures stop at scene-stack setup with
`table_context_required`, before exercising walls/lights/fog. These fixtures
predate explicit server-authorized contexts. This is not evidence of a current
production vision defect. Raw discovery log: `/tmp/feedback-b07-vision-discover.log`.

Medium, controlled: the reported live defect has no exact reproduction yet.
Use explicit DM and Player contexts in updated targeted fixtures and real UI
placement/edit/reload flows; inspect fog configuration and visible effect before
choosing a correction. Never relax the required context boundary.
Medium, controlled: shape labels must preserve map scale and established distance
semantics. Shapes remain transient local overlays, with no resource writes,
attacks, target selection or new event delivery. Separate role composition stays.

Dependency: official SRD 5.2.1 cone glossary, verified against
https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf.
No new library is needed. No open owner question blocks these three cards.

Next: Apply the local shape/diagnostic contract; only confirmed vision defects
receive a further bounded fix design. Record an un-reproduced report honestly.

Browser-confirmed interaction defect: `_selectToken(null)` converts null to the
integer zero and opens the token dock. Blank-map clicks call that path, blocking
the second measurement point on mobile with the dock backdrop. Token pointer
handlers also run while measuring over a token. This is a shared interaction
bug, separate from the un-reproduced lighting report.
