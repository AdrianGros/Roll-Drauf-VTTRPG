# Feature Research: Responsive/Accessibility/Realtime Quality

**Date:** 2026-08-27  
**Slice:** 11 — cross-cutting responsive/accessibility/realtime quality  
**Status:** research/discover only; no production code changed  
**Target file:** `docs/PLAYTABLE_FEATURE_RESEARCH_11_QUALITY_2026-08-27.md`

## 1. Status and input summary

This research pass examines cross-cutting quality concerns that span all prior slices (scenes, menus, map tools, token HUD, statuses, combat, hotbar, chat, loot, and vision). The goal is to ensure that every feature works reliably on desktop and mobile, responds to keyboard and pointer input, handles network delays and reconnection gracefully, respects user motion preferences, and performs well even with many tokens or complex scenes.

The research answers these questions:

- What accessibility and responsive-design patterns must every feature respect?
- How should focus, menus, dialogs, and keyboard navigation behave across slices?
- How should live updates and optimistic state conflict when the server and client disagree?
- What performance budgets and testing strategies keep the table playable at scale?
- How do we verify that every feature works on desktop, tablet, and phone?

## 2. Current Roll-Drauf state and relevant file inventory

### Existing implementation seams

- **Responsive layout**: `play.html` uses CSS media queries to move widgets between desktop (floating anchored panels) and mobile (bottom-sheet `#tableSheet`). Breakpoints are at 768px and 1024px. ([vtt/templates/play.html](../vtt/templates/play.html) lines 1368–1372, 1463–1466)

- **Focus and keyboard**: Limited keyboard support exists. Tab navigation is browser-default. No custom focus restoration on dialog open/close. No explicit focus trap in modals. ([vtt/static/js/play-ui.js](../vtt/static/js/play-ui.js))

- **Pointer and touch**: Click handlers are the primary input. Touch is partially supported (tap equals click). No explicit `touch-action` CSS to prevent accidental zoom/pan. Hover-only UI exists in some places (e.g., token hover HUD). ([vtt/static/js/play-client.js](../vtt/static/js/play-client.js))

- **Live updates**: Socket events broadcast token state, scene changes, chat, and combat updates in real time. No explicit optimistic state or conflict resolution for rapid edits. ([vtt/static/js/play-socket.js](../vtt/static/js/play-socket.js))

- **Offline/reconnect**: Basic disconnect/reconnect banner exists. No explicit replay of pending actions or conflict detection if the server state changed during offline time. ([vtt/play/routes.py](../vtt/play/routes.py))

- **Performance**: Large token counts and complex scenes are not yet stress-tested. No explicit throttling of resize events, scroll events, or frequent socket emissions. Map pan/drag uses direct DOM mutation without requestAnimationFrame coordination.

- **Motion preferences**: No `prefers-reduced-motion` media query support. Animations and transitions may trigger motion sickness in sensitive users.

- **Tooltips**: No standard tooltip pattern. Hover/context-menu help is inconsistent.

### Files not yet modified

- `vtt/static/js/play-ui.js` — widget rendering and keyboard/focus handling
- `vtt/static/js/play-client.js` — pointer input and drag behavior
- `vtt/static/js/play-socket.js` — live update conflict handling
- `vtt/templates/play.html` — focus trap and dialog behavior
- `vtt/play/routes.py` — offline/reconnect flow
- Test suite — no acceptance tests for keyboard, mobile, or performance yet

## 3. Web research and source-backed findings

### W3C Accessibility (WCAG 2.2) and Mobile Accessibility

The W3C Web Content Accessibility Guidelines 2.2 define the global standard for accessible web content. Key criteria relevant to VTT quality:

**Pointer Gestures (WCAG 2.5.1, Level A)**: Single-pointer alternatives must exist for all multi-pointer gestures (e.g., pinch-zoom). Touch gestures should not require multi-touch unless necessary. ([WCAG 2.5.1 Pointer Gestures](https://www.wcag.com/developers/2-5-1-pointer-gestures/))

**Dragging Movements (WCAG 2.5.7, Level AA)**: Any interaction that requires dragging must have a single-pointer alternative. For example, dragging a token to move it should also support click + arrows or click + WASD. ([Guidance on Applying WCAG 2.2 to Mobile Applications](https://w3c.github.io/matf/))

**Target Size (WCAG 2.5.8, Level AA)**: Touch and click targets must be at least 44×44 CSS pixels. Smaller targets are error-prone on touch. ([Mobile Accessibility: How WCAG 2.0 and Other W3C/WAI Guidelines Apply to Mobile](https://w3c.github.io/Mobile-A11y-TF-Note/TouchProposal.html))

**Motion Actuation (WCAG 2.5.4, Level A)**: Device motion (e.g., shake to undo) must have keyboard/button alternatives.

**Reduced Motion (WCAG 2.3.3, Level A via `prefers-reduced-motion`)**: Respect the `prefers-reduced-motion: reduce` media query. Animations and transitions should pause or simplify for users prone to motion sickness.

**Focus and Focus Visible (WCAG 2.4.7, Level AA)**: All interactive elements must have a visible focus indicator. It must not be removed by CSS (`outline: none` is a violation).

**Reflow (WCAG 1.4.10, Level AA)**: Content must reflow at 200% zoom without horizontal scroll. This ensures small-screen and magnified-screen users can read text without hunting horizontally.

**Orientation (WCAG 1.3.4, Level AA)**: Do not lock content to a single screen orientation. Allow portrait and landscape on both desktop and mobile. ([Mobile & Responsive Design — Applying WCAG Standards](https://www.accesify.io/blog/mobile-responsive-wcag/))

### MDN Web APIs for quality

**Pointer Events**: The `PointerEvent` API unifies mouse, touch, and stylus input into a single event model. Use `pointermove`, `pointerdown`, `pointerup`, and `pointercancel` instead of separate `mousemove`/`touchmove` handlers. Pointer events include `isPrimary` (first pointer of a multi-pointer gesture), `pointerType` (mouse/touch/pen), and `width`/`height` (contact area). ([MDN Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent))

**touch-action CSS property**: Prevent default browser behaviors (pinch-zoom, pan) on specific elements. Set `touch-action: none` for custom drag handlers, `touch-action: manipulation` to allow zoom but not double-tap-zoom, or `touch-action: auto` to allow defaults. ([MDN touch-action](https://developer.mozilla.org/en-US/docs/Web/CSS/touch-action))

**requestAnimationFrame**: Coordinate expensive DOM mutations (paint, layout) with the browser's display refresh cycle (typically 60 Hz). Batch mutations inside a single `rAF` callback to minimize layout thrashing. ([MDN requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame))

**ResizeObserver**: Watch for viewport or element size changes without polling. Use it to recalculate layout or tooltip position on resize. ([MDN ResizeObserver](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver))

**Performance.now() and performance.measure()**: Measure real time between events with microsecond precision. Use it to detect stalled input or rendering.

### VTT Performance and Scale Patterns

Based on Foundry VTT and Roll20 practices:

**Token rendering**: With 50+ tokens on screen, iterating and mutating each token's DOM on every update causes jank. Use CSS transforms (translate, scale) instead of left/top (layout-inducing). Batch updates with `requestAnimationFrame`. Consider CSS Grid or absolute positioning for initial placement; use transforms for animation.

**Event throttling**: Frequent socket events (token move, vision update) can overload the client. Throttle updates to 1–2 per frame (16–32ms). Use a queue model: receive events, batch them, apply once per frame.

**Focus trap in dialogs**: When opening a dialog, trap focus inside it (Tab cycles within the dialog). On close, restore focus to the element that opened it. Without this, keyboard users can tab into the background page behind a modal, causing confusion.

**Live region announcements**: Use `aria-live="polite"` for notifications (e.g., "Initiative updated: Alice goes next"). Screen-reader users will hear the update without it interrupting their current reading.

**Optimistic state**: When a player rolls dice, show the result immediately on the client while the server processes it. If the server disagrees (e.g., due to permission checks), reconcile the client state. Use a revision number or timestamp to detect stale updates.

## 4. Good examples

### Example 1: Foundry VTT responsive UI with drawer patterns

**Why it works**: Foundry separates content into drawers (character sheet, journal) and HUDs (token HUD, ruler). On desktop, multiple panels float and can be repositioned. On mobile, drawers slide up from the bottom, taking the full width. The same interaction works everywhere: click to open, Escape to close, keyboard navigation inside the drawer. No hover-only UI. All content is reflow-friendly at 200% zoom. ([Foundry UI Principles](https://foundryvtt.com/article/ui/))

**Applicable to Roll-Drauf**: Apply the drawer pattern to character sheets, loot transfer, and dialogs. On desktop, allow floating panels; on mobile (< 768px), always use bottom-sheet drawers. Ensure all controls remain accessible via keyboard and touch.

### Example 2: Discord/Slack focus and keyboard navigation

**Why it works**: Tab navigation is predictable and visible. All interactive elements have a clear focus ring. Escape closes dialogs/menus and returns focus to the trigger. Modals trap focus (Tab stays within the modal). Arrow keys navigate lists and menus. No hover-only UI.

**Applicable to Roll-Drauf**: Implement a focus trap in dialogs. Use `aria-labelledby` to link dialogs to their titles. Restore focus when closing. Test Tab navigation on every feature slice.

### Example 3: Apple iOS/Android native gestures with fallback buttons

**Why it works**: Gestures are fast (swipe, pinch, long-press), but every gesture has a visible button as a fallback. A new user discovers the button first; an experienced user learns the gesture. Touch targets are 44×44 minimum.

**Applicable to Roll-Drauf**: Provide visible buttons for all actions. Gestures (swipe to dismiss, drag to move token) are enhancements, not requirements. Ensure all buttons are ≥44×44 on mobile.

## 5. Bad examples and failure modes

### Failure 1: Hover-only menu or context UI

**Problem**: A token HUD or tool menu appears only on hover. Mobile users (no hover) cannot access it. Keyboard-only users cannot trigger it. Screen-reader users do not know it exists.

**Applied to Roll-Drauf**: All actions must have a visible button or be discoverable via keyboard. Do not hide the "more actions" menu behind hover.

### Failure 2: No focus indicator

**Problem**: The browser's default focus ring is removed via `outline: none`, and no replacement is provided. Keyboard users cannot see which element has focus. They cannot navigate efficiently.

**Applied to Roll-Drauf**: Keep or replace the default focus ring. Use a clear, high-contrast indicator (e.g., 2px solid blue border). Test with `tab` key on every slice.

### Failure 3: Drag-only interaction without keyboard alternative

**Problem**: Moving a token requires dragging. Keyboard-only users cannot move tokens. Users with motor disabilities may not be able to drag precisely.

**Applied to Roll-Drauf**: Provide arrow-key or WASD alternatives for dragging. Allow "click source, then click destination" workflows.

### Failure 4: Unthrottled resize/scroll events updating heavy DOM

**Problem**: Every resize event or scroll event triggers a full recalculation and reflow. With a large token count or complex scene, resizing the window causes seconds of jank. Mobile users resizing the viewport during play will see stuttering.

**Applied to Roll-Drauf**: Throttle resize events to once per 100–200ms using `requestAnimationFrame`. Batch token updates; do not update each token's position synchronously.

### Failure 5: No offline/reconnect resilience

**Problem**: A player's browser loses connection. If they retry an action (e.g., move token, roll), it may be lost or duplicated. If the server applied an action after the player disconnected (e.g., another player's turn), the client and server can diverge.

**Applied to Roll-Drauf**: Add a pending action queue. On reconnect, resend pending actions. Use a server-assigned action ID to detect duplicates. If a conflict is detected, notify the player and reconcile state.

### Failure 6: Animation induced motion sickness

**Problem**: Large-scale animations or frequent transitions cause dizziness in users sensitive to motion. These users cannot use the app at all if `prefers-reduced-motion` is not respected.

**Applied to Roll-Drauf**: Wrap all animations in `@media (prefers-reduced-motion: no-preference) { ... }`. Remove or simplify animations for users with `prefers-reduced-motion: reduce`.

## 6. Lessons learned

1. **Mobile is first-class, not an afterthought**: Apply WCAG mobile criteria from day one, not as a retrofit. Test every slice on a real mobile device (iOS Safari, Android Chrome) in addition to desktop.

2. **Keyboard and pointer input are equally important**: Drag interactions need single-pointer alternatives. Menu navigation must work with arrow keys and Enter, not just mouse clicks. Tooltips must be discoverable without hover.

3. **Focus management is foundational**: Visible focus rings, focus traps in dialogs, and focus restoration on close are non-negotiable. They enable keyboard users and assist users of assistive technology.

4. **Batching and throttling prevent jank**: Coordinate frequent updates (socket events, resize) with `requestAnimationFrame`. Do not update every token synchronously in response to a server event.

5. **Optimistic state requires careful conflict resolution**: Show results immediately to the client. If the server rejects or modifies the action, reconcile the UI. Use timestamps or revision numbers to detect stale data.

6. **Accessibility and performance are linked**: Reducing motion, simplifying layout, and batching updates all make the app faster and more accessible. Motion-sensitive users, low-bandwidth players, and users on older devices all benefit.

7. **Touch targets and hover surfaces must coexist**: Buttons must be ≥44×44px (mobile-friendly). Hover states are nice-to-have but not required. Right-click menus must have visible button alternatives.

## 7. Community favorites

**Community sentiment on VTT quality** (anecdotal, from Foundry forums, VTT subreddits, and accessibility discussions):

- **Keyboard shortcuts are highly valued by experienced players**: Players who have played dozens of sessions want quick ways to move tokens, roll dice, and open sheets without mouse clicks. Numeric hotkey slots (1–9 for actions) are expected.
- **Mobile play is underserved**: Many VTT communities play D&D over video with the app on a phone or tablet. Floating panels and hover-only UI frustrate mobile players. Bottom-sheet drawers and large touch targets are appreciated.
- **Connection resilience matters at the table**: Players are forgiving of occasional server hiccups if the app gracefully shows a "reconnecting..." banner and replays pending actions. Losing a roll or movement command to a disconnect is frustrating.
- **Reduced motion is appreciated but rarely tested**: Players with vestibular issues or migraines report that respecting `prefers-reduced-motion` is essential. Many VTT apps ignore this setting, forcing them to use the app with browser motion-handling plugins or not at all.
- **Focus management is invisible until it breaks**: Keyboard users do not notice good focus management, but a missing focus ring or unfocused modal causes immediate frustration and is reported as a blocker.
- **Large token counts (50+) slow down the table**: Campaigns with many minions or crowded dungeons can cause frame-rate drops on older devices. Batching updates and using CSS transforms (not layout-inducing properties) make a noticeable difference.

**Non-goals based on community feedback**:

- Do not require hardware-accelerated graphics. The app must work on older devices and low-bandwidth connections.
- Do not use animations as a required step (e.g., "wait for the token to slide across the map before the next action"). Instant updates with optional smooth animations keep play moving.

## 8. Roll-Drauf fit and explicit non-goals

### What belongs in Slice 11 (Quality)

Quality is a **cross-cutting concern**, not a single feature. Every feature slice (1–10) should respect these guidelines:

- Responsive layout: Works on desktop (>1200px), tablet (768–1200px), and phone (<768px).
- Keyboard input: Tab to navigate, Enter/Space to activate, Escape to close, arrow keys for lists/menus.
- Touch input: All actions have visible buttons (≥44×44px). No hover-only UI. `touch-action` is set appropriately.
- Pointer input: Use Pointer Events, not separate mouse/touch handlers.
- Focus management: Focus rings visible. Dialogs trap focus. Escape restores focus.
- Live updates: Socket events update the UI without user action. Optimistic state is reconciled on server response.
- Performance: Updates are batched and throttled. Large token counts do not cause jank.
- Motion: Animations respect `prefers-reduced-motion: reduce`.
- Testing: Acceptance criteria include keyboard, mobile, touch-action, and performance.

### What is deferred

- Custom gesture recognition (swipe, pinch) is not in Slice 11. It is an enhancement if time permits.
- Offline mode (full functionality without server) is deferred to a future slice. Slice 11 covers graceful reconnection only.
- Low-bandwidth optimization (mesh network, delta compression) is deferred.
- Performance profiling and optimization of specific bottlenecks is deferred until a slice is implemented and tested at scale.

## 9. Proposed interface/data/permission contracts

### Quality acceptance criteria (applies to every slice)

Each feature slice (1–10) must meet these criteria for desktop, mobile, and keyboard input:

#### Desktop (>1200px)

- All elements render at their intended size. No text overflow or clipping.
- Hover effects (tooltips, preview) are supplementary, not required.
- Click and keyboard input both work.
- Focus rings are visible on Tab navigation.
- Dialogs or drawers do not obscure critical gameplay elements for >2 seconds.

#### Tablet (768–1200px)

- Layout reflows to single-column or reduced-width layout.
- Floating panels are repositioned or converted to bottom-sheet drawers.
- Touch targets are ≥44×44 CSS pixels.
- Tap behaves like click.
- No hover-only UI.

#### Mobile (<768px)

- Layout is single-column or card-based.
- `#tableSheet` drawer is the primary surface for secondary actions (character sheet, settings, loot).
- Map remains the primary surface; controls are overlaid or docked.
- Touch targets are ≥44×44 CSS pixels.
- Orientation can be portrait or landscape. Content reflows to fill the viewport.

#### Keyboard input (all screen sizes)

- Tab navigates all interactive elements in a logical order.
- Shift+Tab navigates backward.
- Enter activates buttons and opens menus.
- Space toggles checkboxes and toggles.
- Escape closes dialogs, menus, and drawers; restores focus to the trigger.
- Arrow keys navigate lists, trees, and menus (Up/Down for vertical, Left/Right for expand/collapse trees).

#### Pointer input (mouse, touch, stylus)

- Pointer Events API is used for input detection (not separate mouse/touch handlers).
- `touch-action` CSS is set to prevent unintended browser behaviors (e.g., `touch-action: none` for custom drag, `touch-action: manipulation` for standard pan/zoom).
- Drag interactions have single-pointer alternatives (e.g., click source, then arrow keys to move).
- No multi-pointer gestures required (pinch-zoom is optional and must have button alternatives).

#### Focus and accessibility (all input modes)

- All interactive elements have a visible focus indicator (outline, border, or background color).
- Focus indicators meet WCAG AAA contrast requirements (3:1 minimum).
- Dialogs trap focus (Tab cycles within the dialog, not the background page).
- Live announcements use `aria-live="polite"` for real-time updates.
- Labels (`<label>` or `aria-labelledby`) link all inputs to descriptive text.
- Colors are not the only way to convey information (e.g., "red = disabled" also needs text).

#### Motion and animation (all users)

- Animations are wrapped in `@media (prefers-reduced-motion: no-preference) { ... }`.
- Users with `prefers-reduced-motion: reduce` see instant state changes instead of animations.
- No auto-playing sounds or vibrations (user controls audio/haptic feedback).

#### Live updates and offline/reconnect

- Real-time updates are applied to the UI without user action.
- If a local change and server change conflict, the server state is authoritative; the UI reconciles and notifies the player.
- Offline disconnections show a "Reconnecting..." banner.
- Pending local actions are queued. On reconnect, they are resent. Duplicates are detected and merged.
- No silent data loss (players are notified if an action could not be sent).

#### Performance (desktop and mobile)

- Token moves and updates are throttled to ≤2 per frame (16–32ms per frame at 60 Hz).
- Resize and scroll events are throttled to ≤1 per 100ms using `requestAnimationFrame`.
- DOM mutations are batched inside `requestAnimationFrame` callbacks.
- CSS transforms (translate, scale, rotate) are used for animations, not layout-inducing properties (left, top, width, height).
- With 50+ tokens on screen, the app maintains ≥30 FPS. Profiling shows bottlenecks and optimization targets.

#### Error handling and destructive actions

- Destructive actions (delete scene, reset Fog of War, leave session) require explicit confirmation.
- Confirmation dialogs are not dismissable by clicking outside (modal trap). They must be explicitly confirmed or canceled.
- Errors are shown in a live region (`aria-live="assertive"`) and a visual banner. The error message is actionable (not just "Error").

### Test matrix for all slices

| Feature | Desktop Keyboard | Desktop Mouse | Tablet Touch | Mobile Portrait | Mobile Landscape | Performance |
|---------|-----------------|---------------|--------------|-----------------|-----------------|-------------|
| 1. Scenes | Tab/Enter | Click | Tap | ≥44px targets | ≥44px targets | <100ms layer load |
| 2. App Menu | Escape/arrow | Click | Tap | ≥44px targets | ≥44px targets | <50ms menu open |
| 3. Map Tools | Drag alt (arrows) | Click/drag | Tap | ≥44px targets | ≥44px targets | 60 FPS with 20 tokens |
| 4. Token HUD | Tab/Enter | Click | Tap | ≥44px targets | ≥44px targets | <100ms sheet load |
| 5. Statuses | Tab/space | Click | Tap | ≥44px targets | ≥44px targets | <50ms picker open |
| 6. Combat | Arrow keys | Click | Tap | ≥44px targets | ≥44px targets | <100ms turn change |
| 7. Hotbar | 1–9 / arrow | Click | Tap | ≥44px targets | ≥44px targets | <100ms action exec |
| 8. Chat/Dice | Shift+Enter | Click | Tap | ≥44px targets | ≥44px targets | <100ms chat send |
| 9. Loot | Tab/Enter | Click/drag | Tap | ≥44px targets | ≥44px targets | <200ms transfer |
| 10. Vision | Tab/enter | Click/drag | Tap | ≥44px targets | ≥44px targets | 30 FPS with 50+ tokens |
| Quality | Focus trap | Focus ring | Focus ring | Reflow OK | Reflow OK | No jank on resize |

## 10. Risks and assumptions with severity labels

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Retrofitting keyboard support into existing code may require refactoring focus management. | **Medium** | Plan keyboard support during feature design, not after. Test Tab/arrow navigation during each slice. |
| Mobile testing requires a real device or browser emulation. Desktop testing alone misses touch-target and orientation issues. | **High** | Test on iOS Safari (iPhone) and Android Chrome (Pixel/Galaxy). Use Chrome DevTools device emulation as a first pass, but verify on real hardware. |
| Optimistic state conflicts can cause players to see stale data. Detecting and reconciling conflicts requires careful versioning. | **High** | Use server-assigned action IDs or timestamps for conflict detection. Always defer to server state as the source of truth. Notify players of reconciliation. |
| Large token counts (50+) may cause frame-rate drops if not carefully batched. | **Medium** | Profile with DevTools. Batch updates per frame. Use CSS transforms, not layout-inducing properties. Monitor FPS under load. |
| Socket event throughput can exceed the client's ability to render updates. | **Medium** | Implement server-side throttling (e.g., no more than 2 token updates per 16ms). Use delta encoding to reduce payload size. |
| Motion-sensitive users cannot use the app if animations are not optional. | **Medium** | Test with `prefers-reduced-motion: reduce` enabled during development. Wrap animations in media queries. |
| Focus traps can trap keyboard users if a dialog fails to close or opens another dialog. | **Medium** | Test focus trap/restore in each slice. Use browser DevTools to trace focus changes. Avoid nested modals. |
| Network latency can make optimistic state feel out-of-sync. | **Low** | Show a "pending" indicator next to optimistic changes. Reconcile silently on server response if no conflict. |
| Accessibility is language-dependent. Aria labels and live regions must be localized. | **Low** | Plan i18n for aria attributes. For now, use English and note this as a follow-up. |

## 11. Acceptance criteria for desktop, mobile, keyboard, permissions, realtime updates, errors, and destructive actions

### Desktop acceptance

- [ ] All widgets render at designed size (no clipping, overflow, or distortion).
- [ ] Focus rings are visible on Tab navigation (3:1 contrast minimum).
- [ ] Dialogs and modals are centered and do not move with scroll.
- [ ] Tooltips appear on hover and disappear on click or outside-click.
- [ ] Keyboard shortcuts (if any) are documented in Help or visible on buttons.

### Mobile acceptance

- [ ] Layout reflows to single-column at <768px.
- [ ] Floating panels convert to bottom-sheet drawers on mobile.
- [ ] Touch targets are ≥44×44 CSS pixels.
- [ ] Text is readable at 200% zoom without horizontal scroll.
- [ ] Portrait and landscape orientations both work without content loss.
- [ ] No hover-only UI. All actions have visible buttons.

### Keyboard acceptance

- [ ] Tab navigates all interactive elements in logical order (left-to-right, top-to-bottom).
- [ ] Shift+Tab navigates backward.
- [ ] Enter activates buttons.
- [ ] Space toggles checkboxes.
- [ ] Escape closes dialogs/menus and returns focus to the trigger.
- [ ] Arrow keys navigate lists and tree items (Up/Down for movement, Right/Left for expand/collapse).

### Permissions acceptance

- [ ] Players see only content they have permission to access (checked server-side).
- [ ] DM-only actions (delete scene, reset Fog of War, etc.) are not visible to players.
- [ ] Permission checks are enforced on the server; client-side checks are hints only.
- [ ] Players cannot escalate permissions via browser DevTools or network proxies.

### Realtime updates acceptance

- [ ] Token moves, status changes, and other player actions appear on all screens within 100ms.
- [ ] Live announcements (e.g., "Alice's turn") are audible to screen-reader users via `aria-live`.
- [ ] If a local change and server change conflict (e.g., two players move the same token), the server state wins. Players are notified of the conflict.
- [ ] A "Reconnecting..." banner appears on disconnect and clears on reconnect.
- [ ] Pending actions are resent on reconnect. Duplicates are detected (not executed twice).

### Error acceptance

- [ ] Errors are shown in a visual banner and a live region (`aria-live="assertive"`).
- [ ] Error messages are actionable (e.g., "Could not move token: permission denied. Ask the DM." instead of "Error 403").
- [ ] Network timeouts show "Request timed out. Please check your connection and try again."
- [ ] Users can dismiss error banners by clicking an X or pressing Escape.

### Destructive actions acceptance

- [ ] Delete, reset, or leave actions show a confirmation dialog with clear consequences.
- [ ] Confirmation dialogs are modal (cannot dismiss by clicking outside or pressing Escape outside the dialog).
- [ ] The confirmation button is labeled with the action (e.g., "Delete Scene" not just "OK").
- [ ] Dialogs include a reason or impact statement (e.g., "This will reset exploration for all players.").
- [ ] Undo is not promised unless explicitly implemented; the confirmation is the safety net.

## 12. Apply handoff: decisions still needed before implementation

1. **Focus trap implementation**: Should we use a standard library (e.g., `focus-trap` npm package) or hand-code it in play-ui.js? Hand-coding gives finer control; a library reduces bugs.

2. **Pointer Events browser support**: Can we require Pointer Events (IE11 and earlier do not support it) or must we polyfill? Recommendation: require modern browsers and test on IE11/Edge only if corporate clients demand it.

3. **Optimistic state versioning**: Use server-assigned action IDs, timestamps, or a revision number? Recommendation: use server-assigned IDs (simplest) for now; timestamp fallback if we need out-of-order delivery.

4. **Live region politeness**: Should we use `aria-live="polite"` (waits for natural pause) or `aria-live="assertive"` (interrupts) for combat/turn updates? Recommendation: use `polite` for ambient updates (token moves), `assertive` for time-critical updates (turn changes).

5. **Mobile sheet drawer height**: Should the drawer be full-screen, 80% of viewport, or 50% of viewport by default? Recommendation: use 80% for mobile and full-screen on very small phones (<400px height).

6. **Keyboard hotkey conflict with browser shortcuts**: Ctrl+S (save), Ctrl+W (close tab), etc. may conflict with game hotkeys. Should we warn users or avoid these keys? Recommendation: avoid Ctrl+*, Alt+*, and Cmd+* combinations; use 1–9, A–Z, arrow keys, and Shift+letter instead.

7. **Performance budget**: What is the target frame rate (60, 30, or adaptive)? What is the minimum number of tokens that must render at 60 FPS? Recommendation: target 60 FPS with 20 tokens, 30 FPS with 50+ tokens.

8. **Reduced motion testing**: How do we automate `prefers-reduced-motion` testing? Manual testing is required. Should we add a DevTools-accessible flag to override the system preference? Recommendation: use browser DevTools (Chrome: Rendering > Emulate CSS media feature) and automate with Playwright/Cypress.

---

**Completed research note for Slice 11 (Quality).**

### Sources

- [WCAG 2.5.1 Pointer Gestures](https://www.wcag.com/developers/2-5-1-pointer-gestures/)
- [Mobile Accessibility: How WCAG 2.0 and Other W3C/WAI Guidelines Apply to Mobile](https://w3c.github.io/Mobile-A11y-TF-Note/TouchProposal.html)
- [Guidance on Applying WCAG 2.2 to Mobile Applications](https://w3c.github.io/matf/)
- [Mobile & Responsive Design — Applying WCAG Standards](https://www.accesify.io/blog/mobile-responsive-wcag/)
- [MDN Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent)
- [MDN touch-action](https://developer.mozilla.org/en-US/docs/Web/CSS/touch-action)
- [MDN requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame)
- [MDN ResizeObserver](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver)
- [Foundry UI Principles](https://foundryvtt.com/article/ui/)
- [W3C APG Focus Management](https://www.w3.org/WAI/ARIA/apg/practices/keyboard/)
- [W3C APG Menu Button Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/)
