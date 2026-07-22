# Discover Output

```
artifact: discover-output
milestone: VTT-SESSION-REENTRY-2026-03-30
phase: DISCOVER
status: complete
date: 2026-03-30
```

## Input Summary

This Discover pass worked from:

- session control artifact: `docs/DADM_SESSION_CONTROL_2026-03-30_VTT.md`
- existing workstream artifacts:
  - `M01_DISCOVER_Discord_Login_Bot_SSOT.md`
  - `M01_DISCOVER_Login_UI_Rebalance.md`
  - `M02_APPLY_Discord_Login_Bot_SSOT.md`
  - `M02_APPLY_Login_UI_Rebalance.md`
  - `M03_DEPLOY_Discord_Login_Bot_SSOT.md`
  - `M03_DEPLOY_Login_UI_Rebalance.md`
- current uncommitted VTT file changes in auth, model, env, template, CSS, and JS files
- current repo DAD-M rules and BIOS control-plane artifacts

## Current-State Summary

- Relevant: the active VTT workstream is split across two tightly coupled topics:
  - Discord login with bot-backed authorization
  - login UI rebalance inside the book-style login experience
- Relevant: current worktree changes strongly match those two topics:
  - auth/backend/config changes for Discord OAuth and bot verification
  - UI/template/CSS/JS changes for the login screen rebalance
- Relevant: Discover, Apply, and Deploy draft artifacts already exist for both topics.
- Relevant: the current session did not begin from a clean, explicitly locked Deploy gate; it began from an in-progress working tree.
- Relevant: the Discord login workstream introduces operational and security dependencies that are outside the local code diff:
  - Discord developer application configuration
  - bot verification endpoint or signed contract
  - fallback or coexistence policy for password login
- Relevant: the login UI rebalance has a simpler local boundary than the Discord auth workstream, but both are currently mixed into the same uncommitted session state.
- Relevant: verification is not yet in a clean state for this session:
  - no completed targeted app verification for the current branch was recorded in today’s session
  - prior test execution in this environment exposed collection and environment issues rather than a green application signal

## Inventory

| # | Name | Description | Location | Status |
|---|---|---|---|---|
| I1 | Discord Discover draft | Discover notes for Discord identity and bot SSOT | `M01_DISCOVER_Discord_Login_Bot_SSOT.md` | present |
| I2 | Login UI Discover draft | Discover notes for login layout rebalance | `M01_DISCOVER_Login_UI_Rebalance.md` | present |
| I3 | Discord Apply draft | Design draft for Discord identity contract | `M02_APPLY_Discord_Login_Bot_SSOT.md` | present |
| I4 | Login UI Apply draft | Design draft for login layout target state | `M02_APPLY_Login_UI_Rebalance.md` | present |
| I5 | Discord Deploy draft | Implementation plan for Discord login | `M03_DEPLOY_Discord_Login_Bot_SSOT.md` | present |
| I6 | Login UI Deploy draft | Implementation plan for login rebalance | `M03_DEPLOY_Login_UI_Rebalance.md` | present |
| I7 | Discord auth code changes | OAuth helper, routes, model, config, env examples | `.env*`, `vtt_app/auth/*`, `vtt_app/models/*`, `vtt_app/config.py` | present |
| I8 | Login UI code changes | template, CSS, and JS changes for login book layout | `vtt_app/templates/login.html`, `vtt_app/static/css/*`, `vtt_app/static/js/*` | present |
| I9 | Session control artifact | DAD-M lock for this session | `docs/DADM_SESSION_CONTROL_2026-03-30_VTT.md` | present |

## Dependencies

| # | Dependency | Version | Status |
|---|---|---|---|
| D1 | Existing DAD-M workstream docs for Discord login | draft | present |
| D2 | Existing DAD-M workstream docs for login UI rebalance | draft | present |
| D3 | Discord developer application configuration | unknown | unclear |
| D4 | Bot verification endpoint or signed verification contract | unknown | unclear |
| D5 | Local verification path for current branch | current shell only | unclear |
| D6 | Password-login coexistence decision | not locked in current session | unclear |

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Discord login and login UI rebalance are mixed into one local working tree, which increases the risk of phase and scope bleed. | `medium` | yes |
| R2 | The current branch has Deploy-style code changes, but today’s session does not yet have an explicit approval gate that says Deploy may continue safely. | `medium` | yes |
| R3 | Discord login depends on bot/API configuration and policy decisions that are not yet confirmed in-session. | `high` | yes |
| R4 | Current verification status for this working tree is incomplete, so any claim that Deploy is ready would be weak. | `medium` | yes |
| R5 | The existing Apply and Deploy drafts may be sufficient, but they have not yet been re-ratified under the new BIOS control-plane workflow. | `low` | no |

## Open Questions

| # | Question | Priority | Owner |
|---|---|---|---|
| Q1 | Do we treat Discord login and login UI rebalance as one bundled Deploy step for this session, or split them into separate bounded steps? | blocking | session owner |
| Q2 | Is the bot verification contract available enough to proceed with Discord Deploy, or must that track pause at Apply/Human Decision? | blocking | session owner |
| Q3 | Does password login remain available as fallback in the intended target state for this session? | important | session owner |
| Q4 | Do we want the next DAD-M step to be a ratifying Apply checkpoint or a constrained Deploy continuation? | blocking | session owner |

## Next Step

Apply should ratify the session boundary for the active VTT workstream by deciding whether today’s work continues as one bundled Discord-plus-UI change or is split into separate bounded Deploy tracks, and by explicitly accepting or rejecting the unresolved Discord dependencies before more implementation proceeds.
