# Apply Output

```
artifact: apply-output
milestone: VTT-SESSION-BOUNDARY-2026-03-30
phase: APPLY
status: complete
date: 2026-03-30
```

## Input Summary

This Apply pass worked from:

- `docs/DADM_SESSION_CONTROL_2026-03-30_VTT.md`
- `docs/DADM_DISCOVER_VTT_SESSION_REENTRY_2026-03-30.md`
- `M02_APPLY_Discord_Login_Bot_SSOT.md`
- `M02_APPLY_Login_UI_Rebalance.md`
- `M03_DEPLOY_Discord_Login_Bot_SSOT.md`
- `M03_DEPLOY_Login_UI_Rebalance.md`
- user direction for this session: prefer narrower Deploy tracks instead of one bundled mixed workstream

## Solution Design

### Session boundary decision

The active VTT session is split into two bounded Deploy tracks instead of one bundled change:

- Track A: `LOGIN-UI-REBALANCE`
- Track B: `DISCORD-LOGIN-BOT-SSOT`

This split is required to reduce scope bleed, preserve reviewability, and keep DAD-M phase boundaries explicit.

### Track A: `LOGIN-UI-REBALANCE`

#### Goal

Stabilize the login page geometry so the branding panel and form panel match the intended left/right book layout.

#### Scope

- `vtt_app/templates/login.html`
- `vtt_app/static/css/book-scene.css`
- closely related login-only style or behavior adjustments in:
  - `vtt_app/static/css/components.css`
  - `vtt_app/static/css/theme.css`
  - `vtt_app/static/js/auth.js`
  - `vtt_app/static/js/book-scene.js`

#### Design boundary

- `book-scene.css` remains the single source of truth for login geometry.
- `login.html` keeps structure, semantics, and component-adjacent behavior only.
- branding stays on the left book page.
- the form card stays on the right book page.
- mobile collapse remains functional.

#### Deploy readiness

Track A may proceed to Deploy in this session because its boundary is local, already described, and does not depend on external system contracts.

### Track B: `DISCORD-LOGIN-BOT-SSOT`

#### Goal

Add Discord OAuth login and gate access through the bot-backed player authority model without violating the existing auth/session model.

#### Scope

- `.env.example`
- `.env.vtt.roll-drauf.de.example`
- `vtt_app/config.py`
- `vtt_app/auth/routes.py`
- `vtt_app/auth/discord_oauth.py`
- `vtt_app/models/discord_identity_link.py`
- `vtt_app/models/__init__.py`
- login entry-point changes in `vtt_app/templates/login.html`

#### Design boundary

- stable identity key is `discord_user_id`
- bot remains the source of truth for player eligibility
- VTT owns local link persistence and session creation
- no authorization by Discord username or display name
- existing password login remains present unless an explicit later decision removes it

#### Deploy readiness

Track B does not have an unconditional Deploy handoff yet.

It is held behind explicit gating because the current session still lacks confirmed answers for:

- bot verification endpoint or signed contract availability
- accepted fallback/coexistence policy for password login
- session-level acceptance that the current verification gap is tolerable for continued local Deploy work

### Relationship between tracks

- Track A and Track B may touch the same login surface, but they are not equally risky.
- Track A is primarily local presentation/layout work.
- Track B is identity, session, and external-contract work.
- If Track A Deploy changes `login.html`, those changes must preserve a clean insertion point for Track B’s Discord entry action.
- Track B must not reopen Track A’s geometry decisions unless the current UI structure blocks the identity flow.

### Session routing rule

For the rest of this session:

- UI-only structural/layout work routes to Track A Deploy.
- Discord identity, OAuth, bot verification, or auth contract work routes to Track B and remains gated until its TBDs are explicitly accepted.

## Acceptance Criteria

```text
AC-VTT-SESSION-01: The session is split into two named Deploy tracks with explicit file boundaries.
AC-VTT-SESSION-02: Track A is explicitly allowed to proceed to Deploy without requiring Discord external dependencies.
AC-VTT-SESSION-03: Track B is explicitly held behind unresolved dependency and policy gates rather than being silently bundled into Track A.
AC-VTT-SESSION-04: The intended relationship between Track A and Track B on the shared login surface is documented.
AC-VTT-SESSION-05: The next Deploy step for this session can be named without ambiguity.
```

## Risks and Assumptions

| # | Description | Severity | Blocking |
|---|---|---|---|
| R1 | Even after the split, both tracks touch `login.html`, so careless edits can still cause merge or behavior conflicts. | `medium` | yes |
| R2 | The Discord track still depends on external configuration and policy that are not confirmed in-session. | `high` | yes |
| R3 | The local verification environment is not yet cleanly reproducible, which weakens confidence for any auth-heavy Deploy continuation. | `medium` | yes |
| R4 | Preserving password-login fallback is treated as the safe default for this session unless explicitly overturned later. | `low` | no |

## Open TBDs

| # | TBD | Priority | Owner |
|---|---|---|---|
| T1 | Confirm whether the bot verification contract is available enough to continue Track B Deploy in this session. | blocking | session owner |
| T2 | Confirm whether password login remains an accepted fallback target for the current Discord design. | important | session owner |
| T3 | Decide whether Track B should continue later in Apply, Human Decision, or a future Deploy after dependency confirmation. | blocking | session owner |

## Next Step

Deploy must continue with Track A `LOGIN-UI-REBALANCE` only, while Track B `DISCORD-LOGIN-BOT-SSOT` remains gated until its unresolved dependencies and policy decisions are explicitly accepted.
