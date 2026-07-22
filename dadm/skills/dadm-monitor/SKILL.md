---
name: dadm-monitor
description: Use for post-implementation validation, regression checks, release evidence, residual risk capture, and deciding the next bounded follow-up after deploy.
---

# DAD-M Monitor

Use this skill when the main implementation is done and the repo needs validation rather than more feature work.

## Goal

Validate outcomes, capture regressions or residual risk, and define the next bounded action.

## Load order

1. `dadm-framework/runtime/AI_BIOS.md`
2. `dadm-framework/runtime/file-registry.yaml`
3. `runtime/cards/monitor-card.md`
4. `runtime/cards/deliverables-min.md`

Default profile for this repo: `standard`.

## Do

- check whether acceptance criteria were truly met
- gather release or test evidence
- identify regressions, incidents, or verification gaps
- recommend the next bounded action

## Do not

- add silent feature work
- use Monitor as a hidden Deploy phase

## Expected output

Include:

- observed results
- validation evidence
- residual risks
- recommended next action

## Good prompt shapes

- `$dadm-monitor Validate the current Discord login branch and capture residual risks before we move forward.`
- `$dadm-monitor Review the release evidence, summarize what passed, and name the highest-priority follow-up.`
