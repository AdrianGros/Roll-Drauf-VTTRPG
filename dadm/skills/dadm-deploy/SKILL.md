---
name: dadm-deploy
description: Use for approved implementation work, targeted code changes, and verification after Apply has defined the design and boundaries.
---

# DAD-M Deploy

Use this skill when the design is already approved and the task is now to implement it safely.

## Goal

Implement the approved design, keep scope tight, and leave clear verification evidence.

## Load order

1. `dadm-framework/runtime/AI_BIOS.md`
2. `dadm-framework/runtime/file-registry.yaml`
3. `runtime/cards/deploy-card.md`
4. `runtime/cards/deliverables-min.md`

Default profile for this repo: `standard`.

## Do

- implement only the approved scope
- keep changes minimal and reviewable
- run targeted verification and record exact commands or gaps
- summarize files changed, proofs, and acceptance checks

## Do not

- invent new architecture
- hide unrelated cleanup inside the patch
- claim verification that did not happen

## Expected output

Include:

- implementation summary
- files changed
- verification run
- proofs or evidence
- acceptance checklist

## Good prompt shapes

- `$dadm-deploy Implement the approved Discord callback flow and verify the changed auth paths.`
- `$dadm-deploy Apply the target login UI rebalance from the approved design. Keep the patch minimal and list the verification steps.`
