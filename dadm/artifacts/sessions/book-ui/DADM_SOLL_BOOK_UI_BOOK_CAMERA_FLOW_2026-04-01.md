# DAD-M Soll: Book Camera Flow

Date: 2026-04-01
Phase: SOLL
Status: target-defined
Scope: target UX and system model for the persistent book journey

## Objective

Define the desired user journey and scene model for the new book-native authenticated experience.

## Target Journey

### S-01

The book object remains the primary container before and after login.

The user should never feel like they left the book and landed in a normal app shell.

### S-02

Successful login becomes a physical and spatial transition:

1. open cover
2. turn page
3. camera zooms into the next page
4. dashboard is revealed as that page

### S-03

Authenticated navigation should feel like moving through a storybook.

- menu lives on the page, not above it as detached app chrome
- chapters are pages or page regions
- navigation transitions are page turns or camera moves inside the same scene

### S-04

The dashboard should follow the mockup's composition logic.

Expected layout:

- top embedded `menu ribbon`
- small top-right utility/emblem area
- upper row:
  - `Meine Kampagnen`
  - `Charaktere`
- lower wide row for widgets:
  - calendar
  - forum/community
  - homebrew builder
  - workshop/community modules

### S-05

Access control must match the key-based product policy.

If registration keys are the intended gate, then account creation must require a valid key and public signup must not remain a parallel bypass.

## Non-Goals

- do not turn the whole product into a heavy 3D simulation at all times
- do not make dense work routes unreadable just to preserve spectacle
- do not reintroduce generic app headers outside the page plane

## Target Architecture Summary

Recommended target:

- one persistent `book scene`
- one transformable `camera stage`
- page targets inside the scene
- authenticated dashboard/menu rendered as content on the visible page

This keeps the illusion coherent while still allowing real DOM content and usable layouts.
