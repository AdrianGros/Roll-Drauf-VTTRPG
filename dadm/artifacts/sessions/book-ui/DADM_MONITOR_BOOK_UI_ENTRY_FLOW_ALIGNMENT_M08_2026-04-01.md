# DAD-M Monitor: Book UI Entry Flow Alignment (M08)

Date: 2026-04-01
Milestone: M08
Phase: MONITOR
Status: approved

## What To Watch

- signup success redirects should land on `login` with a visible confirmation
- register validation should not reject an `8-11` character password if it otherwise meets backend rules
- no regression in MFA continuation or Discord login exposure

## Residual Risks

- public signup still uses mostly general-error fallback
- cross-page success continuity is now clearer, but not yet shared through one unified auth component

## Approval

- scope_kept: yes
- live_check_used: no
- approved_to_proceed: yes
