---
name: dadm-discover
description: Use for repository research, audits, current-state mapping, milestone discovery, risk inventory, and fact-finding when implementation is not yet approved.
---

# DAD-M Discover

Use this skill when the task is about understanding the current state before design or implementation.

## Goal

Produce a reviewable Discover output with facts, scope boundaries, risks, assumptions, and a clear next step into Apply.

## Load order

1. `dadm-framework/runtime/AI_BIOS.md`
2. `dadm-framework/runtime/file-registry.yaml`
3. `runtime/cards/discover-card.md`
4. `runtime/cards/deliverables-min.md`

Default profile for this repo: `standard`.

## Do

- inventory the relevant files, configs, routes, models, tests, and operational constraints
- separate current-state facts from design ideas
- capture risks and assumptions with severity
- identify open questions that block safe design
- leave an explicit next step for Apply

## Do not

- implement code
- choose architecture
- hide design work inside the research artifact

## Expected output

Include:

- input summary
- current-state summary
- relevant inventory
- dependencies or external constraints
- risks and assumptions with severity
- open questions
- next step

## Good prompt shapes

- `$dadm-discover Research this repository and produce a Discover output for milestone M01. Scope: Discord login and bot-backed authorization. Constraints: no code changes.`
- `$dadm-discover Audit the current login system, name the real files involved, and identify what Apply needs first.`
