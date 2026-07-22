artifact: soll-output
date: 2026-04-01
status: approved-and-applied

## Zielbild

`signup` and `register` must behave like real chapters of the same book runtime.

Required properties:

- centered persistent book object remains the UI container
- auth chapters render as spreads inside `BookScene`
- no separate `book-shell` runtime for these two routes
- existing validation and API behavior remain intact
- `register` may transition directly into `dashboard`
- `signup` may return to `login` after successful account creation

## Constraints

- preserve existing form field ids and submission behavior
- avoid reopening the login spread architecture
- keep the change bounded to the auth runtime realign
