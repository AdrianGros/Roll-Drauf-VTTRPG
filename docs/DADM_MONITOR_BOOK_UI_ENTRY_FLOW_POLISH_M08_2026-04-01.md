# DAD-M Monitor: Book UI Entry Flow Polish (M08)

Date: 2026-04-01
Milestone: M08
Phase: MONITOR
Status: approved

## What To Watch

- signup failures should appear on `username`, `email`, or `password` when the server message identifies one of those fields
- register password guidance should no longer contradict backend validation
- success and loading banners should remain visible and not regress routing behavior

## Fast Regression Checks

- submit weak password on `signup`
- submit weak password on `register`
- submit duplicate username/email on both routes
- submit invalid key on `register`

## Closure

The slice is approved because it resolves the clearest documented auth inconsistency while staying inside the milestone change budget.
