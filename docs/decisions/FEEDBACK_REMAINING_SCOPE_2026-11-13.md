# Remaining feedback — owner directions and execution checkpoint

Status: active delivery; retention permanent. Owner instruction: finish the remaining
feedback plan with Codex. The existing B01–B11 program is the authorized scope;
no external implementation agents or new dependency approvals are implied.

Owner answers in this work cycle:

- N07: the DM approves specific published homebrew options per campaign. This is
  an explicit allowlist, not permission to bypass arbitrary prerequisites or
  to elevate a Player context. Design and test server authorization before delivery.
- N11: leave “scale to 0%” pending until the control is identified. This is an
  owner-deferred item; do not reinterpret it as brush size or erase softness.

Execution checkpoint:

1. B06a raster credit compatibility is committed/pushed as `e8bfcf9a1`, deployed
   and verified through normal DM and Player Maps exports. Proof:
   `docs/proofs/feedback-b06a-2026-11-13/delivery.json`.
2. B06b brushes, independent eraser values, coastline controls and draft/auth
   protection are live as `c7f620f92`, with DM/Player browser proof and scoped
   cleanup in `docs/proofs/feedback-b06b-2026-11-13/delivery.json`.
3. B07 is live as `ea3fb25a6`, with PostgreSQL ID repair `6297593cd`,
   role journeys and scoped cleanup in `docs/proofs/feedback-b07-2026-11-13/delivery.json`.
   B08–B10 and N07 each require their bounded Discover/Apply output before code,
   then focused checks, a source commit/push, the guarded existing production
   release workflow, live role journeys and scoped test-data cleanup.
4. B11 ends with a combined live validation and owner checklist. Owner acceptance
   is a separate observation; do not claim it happened automatically.

The current worktree is `/home/admin/projects/roll-drauf-vtt-feedback-20261110`,
branch `feat/protocol-feedback-20261110`. Preserve the unrelated original checkout.
The current live image and the release record must be rechecked before each release.
Do not stop after B06 or report the overall program complete while required later
packages remain. Keep the implementation register and delivery proofs current.
