artifact: discover-output
date: 2026-04-01
status: completed

## Context

The non-`play` route audit showed a runtime split inside the product family:

- `login`, `dashboard`, `campaigns`, and `characters` already ran inside the persistent `BookScene`
- `signup` and `register` still rendered through the older `book-shell` stack

This meant the auth onboarding family looked related, but was not actually part of the same centered book runtime.

## Ist State

- `signup.html` rendered as a standalone parchment shell with its own header, frame, and footer
- `register.html` rendered through the same older shell family
- both routes had correct form behavior, but not the newer persistent-book behavior
- the runtime split was architectural, not just visual

## Gap

The project still carried two UI runtimes for non-`play` routes:

1. the newer centered `BookScene`
2. the older `book-shell` page family

That contradicted the current layout contract for non-`play` routes.
