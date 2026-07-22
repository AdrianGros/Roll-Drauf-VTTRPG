# DAD-M Research: Access Gate and Book Scene V2

Date: 2026-04-01
Phase: RESEARCH
Status: complete

## Sources Used

- Prezi zoom model:
  - https://support.prezi.com/hc/en-us/articles/360003498793-How-to-use-zoom-in-Prezi-Present
- web.dev animation performance:
  - https://web.dev/articles/animations-guide
- web.dev RAIL:
  - https://web.dev/articles/rail
- MDN `transform`:
  - https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/transform
- MDN `will-change`:
  - https://developer.mozilla.org/en-US/docs/Web/CSS/will-change

## Research Takeaways

### R-01

The most faithful implementation for the requested feel is a persistent scene with a moving camera, not a normal route handoff with decoration.

### R-02

The performant version of that idea should animate `transform` and `opacity`, not layout-heavy properties.

### R-03

The access-control correction should prefer one canonical registration model rather than two parallel onboarding stories.

## Derived Rules

### Rule A

Registration must have one canonical key-gated path.

### Rule B

The login-to-dashboard pilot should stay inside the book scene and treat the dashboard as page content, not as an external app shell.

### Rule C

The pilot may stay bounded to login -> dashboard and does not need to solve every authenticated route yet.
