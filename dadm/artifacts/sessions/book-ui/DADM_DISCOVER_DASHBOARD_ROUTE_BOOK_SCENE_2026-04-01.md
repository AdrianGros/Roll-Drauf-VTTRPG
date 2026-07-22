# DAD-M Discover: Dashboard Route Book Scene

Date: 2026-04-01
Phase: DISCOVER
Status: complete

## Objective

Freeze the remaining gap after the login-scene pilot.

## Findings

- the login route already presents a book-native dashboard pilot
- direct visits or reloads on `/dashboard` still fall into [dashboard.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/dashboard.html)
- that route still contained the older app-like dashboard structure

## Discover Conclusion

The remaining inconsistency was not the login transition anymore, but the direct dashboard route.

The correction target is therefore:

- make `/dashboard` boot into the same book-scene architecture
- stop exposing the old dashboard shell as the active route experience
