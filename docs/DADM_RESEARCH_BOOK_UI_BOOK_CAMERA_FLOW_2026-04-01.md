# DAD-M Research: Book Camera Flow

Date: 2026-04-01
Phase: RESEARCH
Status: complete
Scope: best-practice guidance for a Prezi-like in-book zoom architecture

## Objective

Research how to implement the desired "page turn + zoom into the next page" experience in a way that stays performant and usable on the web.

## Sources Used

- Prezi support: How zoom works in Prezi Present
  - https://support.prezi.com/hc/en-us/articles/360003498793-How-to-use-zoom-in-Prezi-Present
- web.dev: high-performance CSS animations
  - https://web.dev/articles/animations-guide
- web.dev: RAIL performance model
  - https://web.dev/articles/rail
- MDN: `transform`
  - https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/transform
- MDN: `will-change`
  - https://developer.mozilla.org/en-US/docs/Web/CSS/will-change
- W3C: Reflow
  - https://www.w3.org/WAI/WCAG21/Understanding/reflow
- web.dev: responsive web design basics
  - https://web.dev/articles/responsive-web-design-basics

## Research Findings

### R-01 — Prezi's core idea is a camera moving across one canvas

Prezi describes zoom as a camera view moving smoothly across one large canvas. Frames define areas of interest, and zoom intensity is controlled by the size and arrangement of those framed areas.

Implication for this VTT:

- the right mental model is not "navigate to another page template"
- the right model is "stay in one book scene and move the camera to another framed page area"

### R-02 — The performant version of this idea is still DOM-first

web.dev recommends keeping motion on the composite stage and preferring `transform` and `opacity`.

Implication:

- a `scene + camera` implementation can be efficient if the animated layer is a transformable stage
- avoid animating `top`, `left`, `width`, `height`, or layout-heavy properties for the camera move

### R-03 — A transformed camera stage changes positioning behavior

MDN notes that transformed elements create a new coordinate space and containing block.

Implication:

- once we introduce a camera-transformed stage, "fixed" or detached app chrome inside that subtree behaves differently
- therefore navigation and content chrome should live naturally inside the page/stage, not as floating global UI pretending to be outside the book

### R-04 — `will-change` should be temporary, not sprayed across the app

MDN explicitly warns that `will-change` is a last resort and should be switched on and off only around the actual change.

Implication:

- only the camera stage and possibly the active turning page should receive temporary `will-change: transform`
- do not permanently layer-promote every page or panel

### R-05 — Performance budgets still matter during spectacle

RAIL keeps response under about `100 ms` and animation frames inside a roughly `10 ms` working budget if we want smooth motion.

Implication:

- login success should feel immediate
- the page-turn + zoom transition may be theatrical, but it cannot stall input or feel sluggish
- content should be prepared before the transition fires where possible

### R-06 — Reflow still applies after the zoom lands

W3C and web.dev both emphasize that content must still adapt to smaller widths without forcing normal horizontal scrolling.

Implication:

- the camera effect may zoom to a page
- but the page content itself must remain responsive when the viewport is narrow

## Architecture Options

### Option A — Hard route change plus overlay animation

Description:

- animate a page-turn overlay
- navigate to a separate HTML route
- render the dashboard there

Pros:

- lower code change

Cons:

- still breaks the "same object" illusion
- user will continue to feel the app boundary

Verdict:

- not sufficient for the requested UX

### Option B — Persistent DOM scene with camera stage

Description:

- keep the book scene mounted
- introduce a large scene/canvas area for page targets
- animate a camera container via `translate/scale`
- mount dashboard/navigation as page content inside that scene

Pros:

- matches the requested Prezi-like feeling
- can stay performant with transform-only animation
- preserves the book object continuously

Cons:

- requires architecture refactor of authenticated routes

Verdict:

- recommended

### Option C — Canvas/WebGL-first book world

Description:

- render the entire book and pages as a canvas or WebGL scene

Pros:

- maximum visual control

Cons:

- much heavier engineering cost
- worse content/accessibility ergonomics
- higher risk of recreating app UI inside a graphics engine

Verdict:

- overkill for the current product stage

## Recommended Technical Direction

Build a persistent `book-scene v2` with these layers:

1. `book object`
2. `turnable page plane`
3. `camera stage`
4. `page targets` mounted as real DOM content inside the stage

Transition pattern:

1. authenticate in the open book
2. pre-mount dashboard page content inside the scene
3. run a page-turn animation
4. animate camera `translate + scale` into the dashboard page target
5. keep later menu navigation inside the same stage

## Derived Rules

### Rule A

Do not solve this as another standalone page shell.

### Rule B

Use a persistent book scene and a transformable camera stage.

### Rule C

Keep animated properties to `transform` and `opacity` wherever possible.

### Rule D

Menu and content chrome must live on the page plane, not as detached app furniture.

### Rule E

Close the public-signup bypass before calling the onboarding flow book-faithful.

## Recommended Next DAD-M Slices

1. `DISCOVER/APPLY`: access-control alignment
   close public signup or require a key there too
2. `DISCOVER/SOLL`: `book-scene v2` architecture
   persistent scene, camera stage, authenticated page targets
3. `APPLY`: dashboard mockup pilot
   rebuild dashboard as one composed page inside the scene
4. `APPLY`: in-page menu ribbon navigation
   campaigns, characters, widgets as page-native navigation
