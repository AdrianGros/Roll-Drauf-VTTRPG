# DAD-M Session Control

```
artifact: session-control
session: VTT-2026-03-30
status: active
date: 2026-03-30
profile: standard
```

## Purpose

This artifact locks the current working session into DAD-M mode.

For this session:

- work must stay phase-explicit
- BIOS routing is active
- the push step is deferred until the end of the VTT session
- workflow override is allowed only if the user explicitly says `Gummibärchen`

## Input Summary

Session inputs at start:

- root repo policy: `AGENTS.md`
- runtime BIOS: `dadm-framework/runtime/AI_BIOS.md`
- BIOS control-plane artifacts:
  - `dadm-framework/runtime/bios.policy.md`
  - `dadm-framework/runtime/bios.routing.yaml`
  - `dadm-framework/runtime/bios.registry.json`
- active VTT workstream artifacts already present in the tree:
  - `M01_DISCOVER_Discord_Login_Bot_SSOT.md`
  - `M01_DISCOVER_Login_UI_Rebalance.md`
  - `M02_APPLY_Discord_Login_Bot_SSOT.md`
  - `M02_APPLY_Login_UI_Rebalance.md`
  - `M03_DEPLOY_Discord_Login_Bot_SSOT.md`
  - `M03_DEPLOY_Login_UI_Rebalance.md`
- active code/config changes for Discord login and login UI rebalance

## BIOS Routing Decision

Prompt intent for this step:

- test the new DAD-M control plane
- force structured work for the current VTT session
- avoid drifting directly into implementation without phase visibility

Resolved phase:

- `DISCOVER` for session control and active-workstream re-entry

Reason:

- the repo already contains Deploy-style changes, but today’s session has not yet been anchored in a current DAD-M control artifact
- before any further VTT code work, the session needs an explicit phase gate and active-workstream decision
- this is consistent with BIOS behavior: prompt -> phase classification -> capability resolution -> routing plan

## Current Active Workstream

The working assumption for this session is:

- primary active VTT workstream: Discord login plus login UI rebalance

Evidence:

- matching M01, M02, and M03 artifacts already exist for both topics
- matching uncommitted file changes exist in auth, model, env, template, CSS, and JS files

## Allowed Actions In This Session

Until the user says `Gummibärchen`, the session must:

- stay inside explicit DAD-M phases
- write or update artifacts before crossing phase boundaries
- treat BIOS as router, not as duplicated instruction store
- defer push commands and actual push execution until the current VTT session is wrapped

## Forbidden Actions In This Session

- silent implementation outside an active Deploy step
- silent architecture decisions inside Deploy
- silent phase changes
- pushing partial session state as if the day is complete

## Next Gate

The next required step is:

- produce a clean Discover checkpoint for the active VTT workstream that answers whether the session should proceed to `Apply` or can re-enter `Deploy` safely

## Deferred TODO

Push is intentionally deferred until session wrap-up.

When the session closes, decide whether to:

1. commit and push only the Codex/DAD-M control-plane work
2. commit and push the VTT workstream changes
3. split framework and app changes into separate pushes
