---
name: dadm-apply
description: Use for solution design, architecture scoping, interface definition, and milestone planning after discovery is complete and before any implementation starts.
---

# DAD-M Apply

Use this skill when the repo already has enough facts and now needs a design package.

## Goal

Turn the discovered boundary into a clear, implementable plan without writing code.

## Load order

1. `dadm-framework/runtime/AI_BIOS.md`
2. `dadm-framework/runtime/file-registry.yaml`
3. `runtime/cards/apply-card.md`
4. `runtime/cards/deliverables-min.md`

Default profile for this repo: `standard`.

## Do

- review the relevant Discover artifact first
- define the target state and explicit boundaries
- specify interfaces, data contracts, ownership, rollout notes, and acceptance criteria
- document tradeoffs and unresolved decisions

## Do not

- implement code
- expand scope silently
- start Deploy while medium-or-higher findings remain unresolved or unaccepted

## Expected output

Include:

- design summary
- solution boundary
- interfaces or data contracts
- acceptance criteria
- risks and tradeoffs
- explicit Deploy handoff

## Good prompt shapes

- `$dadm-apply Design the approved Discord login flow inside the discovered constraints. No implementation yet.`
- `$dadm-apply Convert the Discover findings into an implementation-ready plan with acceptance criteria and rollout notes.`
