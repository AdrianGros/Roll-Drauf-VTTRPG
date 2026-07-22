# DAD-M Discover: Access Gate and Book Scene V2

Date: 2026-04-01
Phase: DISCOVER
Status: complete

## Objective

Freeze the real baseline for the next correction block:

- registration access control
- login to dashboard book continuity

## Findings

### F-01

The current public registration path is still open.

Evidence:

- `/api/auth/register` creates accounts without any registration key check in [routes.py](/home/admin/projects/roll-drauf-vtt/vtt_app/auth/routes.py)
- [signup.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/signup.html) still submits to that public route

Impact:

- the Discord-bot registration key system is currently optional instead of mandatory
- this undermines the intended gatekeeping model

### F-02

The key-protected route already exists, but only as a parallel path.

Evidence:

- `/api/auth/register-with-key` validates and consumes registration keys
- [register.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/register.html) already uses it

Impact:

- the secure model exists technically
- the product flow still exposes a bypass through public signup

### F-03

The current login book scene is a beautiful threshold, but not a persistent book world.

Evidence:

- [book-scene.js](/home/admin/projects/roll-drauf-vtt/vtt_app/static/js/book-scene.js) opens the cover and then navigates away on page turn
- the dashboard lives as a separate route shell in [dashboard.html](/home/admin/projects/roll-drauf-vtt/vtt_app/templates/dashboard.html)

Impact:

- the handoff still feels like leaving the object
- this contradicts the target "through a fairy-tale book" journey

### F-04

The dashboard composition is still app-like rather than page-composed.

Evidence:

- detached header controls
- generic stat row
- generic recent-campaign and recent-character sections

Impact:

- even after the turn, the user sees an interface that reads more like an app dashboard than a designed book page

## Discover Conclusion

The next corrective block must do two things in order:

1. remove the public-signup bypass
2. prove the persistent-book illusion on the first authenticated step
