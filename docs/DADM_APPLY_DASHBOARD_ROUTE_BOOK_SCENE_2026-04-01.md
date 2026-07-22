# DAD-M Apply: Dashboard Route Book Scene

Date: 2026-04-01
Phase: APPLY
Status: complete

## Objective

Replace the active `/dashboard` route experience with the same book-scene architecture used by the login pilot.

## Applied Changes

### A-01

[dashboard.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/dashboard.html) now boots the dashboard through the book scene instead of rendering the old dashboard shell as the active experience.

### A-02

[book-scene.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/book-scene.js) now exposes a direct dashboard bootstrap path so the route can open straight into the already-open book state.

### A-03

The direct route now reuses the same dashboard page composition, data snapshot loading, and book-native menu ribbon as the login-scene pilot.

## Scope Kept

Changed files:

- [dashboard.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/dashboard.html)
- [book-scene.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/book-scene.js)

The wider authenticated route family was intentionally left untouched.
