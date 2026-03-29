# M3: APPLY — Implementation Checklist

**Phase**: DAD-M APPLY
**Milestone**: M3 (Week 3-4)
**Goal**: Stabilize book UI + add visual polish components + implement page-turn navigation

---

## Component Implementation Order

### Priority 1: Page-Turn Navigation Foundation (Core Feature)
🎯 **Must Have** — without this, pages don't navigate

- [ ] Implement `BookScene.pageTurn(url)` method
  - [ ] Create page-turn overlay div
  - [ ] GSAP timeline: rotateY 0° → -90° → -180° (0.6s total)
  - [ ] At midpoint (t=0.3s), navigate window.location.href
  - [ ] Remove overlay on complete
  - [ ] Test: Dashboard → Campaigns → Dashboard (smooth transitions)

- [ ] Update `goTo(path)` on all pages
  - [ ] dashboard.html: Replace all `goTo()` calls with BookScene.pageTurn()
  - [ ] campaigns.html: Same
  - [ ] characters.html: Same
  - [ ] Update nav buttons, card clicks, breadcrumb links

- [ ] Add keyboard shortcuts
  - [ ] Left Arrow: Navigate to previous page
  - [ ] Right Arrow: Navigate to next page
  - [ ] ESC: Return to dashboard
  - [ ] Tab: Cycle through interactive elements on current page

### Priority 2: Visual Book Components (Polish)
🎯 **High Value** — dramatically improves book authenticity

- [ ] Page Numbers
  - [ ] Add footer element to each page (hidden on mobile)
  - [ ] CSS: position absolute, bottom 20px, centered
  - [ ] Font: Cinzel 0.9rem, rgba(0,0,0,0.3) color
  - [ ] Increment dynamically: Dashboard=1-2, Campaigns=3-4, Characters=5-6
  - [ ] Test: Show on desktop 2-page, hide on mobile

- [ ] Book Spine/Binding
  - [ ] Enhance inset shadow on cover edges
  - [ ] Add subtle texture via background-image or pattern
  - [ ] Spine label: horizontal text rotated 90° on spine
  - [ ] Desktop only (hide on mobile)

- [ ] Page Edge Detail
  - [ ] Top/bottom of pages: thin dark line border (1px solid rgba(0,0,0,0.2))
  - [ ] Subtle page-layering effect: offset shadow on stacked pages
  - [ ] Test at different screen sizes

- [ ] Bookmark Indicator
  - [ ] Ribbon element on right edge of book spine
  - [ ] Position: top-right of .book-back
  - [ ] Color: matches current section (gold for active, gray for inactive)
  - [ ] Animate slide: transitions on page-turn (0.3s ease)
  - [ ] Sections: Dashboard, Campaigns, Characters (3 positions)

### Priority 3: Form & Input Stabilization
🎯 **Medium Value** — improves usability & accessibility

- [ ] Form Wrapper Enhancement
  - [ ] Add subtle background to form area (rgba(0,0,0,0.1))
  - [ ] Border: 1px solid rgba(212,175,55,0.2)
  - [ ] Border-radius: 4px
  - [ ] Padding: 30px 20px
  - [ ] Max-width: 400px, centered on page

- [ ] Input Field Styling
  - [ ] Background: var(--vtt-surface-input, #141420)
  - [ ] Text: var(--vtt-text-primary, #e8d5b7)
  - [ ] Border: 2px solid var(--vtt-border-subtle)
  - [ ] Focus state: border-color #d4af37, box-shadow gold glow
  - [ ] Placeholder: rgba(232,213,183,0.5)
  - [ ] Padding: 12px 16px

- [ ] Button Styling
  - [ ] Height: 44px (min touch target)
  - [ ] Font-weight: 600
  - [ ] Transition: all 0.3s ease
  - [ ] Hover: background-color shift + shadow lift
  - [ ] Focus: outline 2px solid #d4af37

- [ ] Label Positioning
  - [ ] Labels inside `<label>` tags (not placeholder text)
  - [ ] Position: above input (display: block)
  - [ ] Font-weight: 600, color: #4a235a
  - [ ] Margin-bottom: 8px

- [ ] Validation Display
  - [ ] Error message below input
  - [ ] Color: #ff6b6b
  - [ ] Font-size: 0.85rem
  - [ ] Margin-top: 4px
  - [ ] Test: Empty field, invalid email, password mismatch

### Priority 4: Responsive Breakpoints Implementation
🎯 **High Value** — ensures mobile/tablet usability

- [ ] Mobile-First CSS Rewrite
  - [ ] Base styles: 320px viewport
  - [ ] Book: full width minus 20px padding (max 320px)
  - [ ] Single-page view (right page hidden)
  - [ ] Stack navigation vertically

- [ ] Tablet (768px) Adjustments
  - [ ] Book: 500w × 650h
  - [ ] Padding: 30px
  - [ ] 2-page capable (gutter 10px)
  - [ ] Adjust grid: 2 columns instead of 3

- [ ] Desktop (1024px+) Enhancements
  - [ ] Book: 600w × 750h (optimal reading width)
  - [ ] Full 2-page spread with 20px gutter
  - [ ] Sidebar space for bookmarks/navigation
  - [ ] Grid: 3 columns for cards

- [ ] Test Devices
  - [ ] iPhone SE (375px)
  - [ ] iPad (768px)
  - [ ] Desktop 1024px
  - [ ] Desktop 1600px (ensure book doesn't scale larger)

### Priority 5: Accessibility Fixes
🎯 **Medium Value** — WCAG AA compliance

- [ ] ARIA Labels
  - [ ] `<div id="book" role="region" aria-label="Spellbook application shell">`
  - [ ] Book cover: `aria-label="Book front cover - click or press Enter to open"`
  - [ ] Each page: `aria-label="Page 1: Dashboard - Campaigns Section"`
  - [ ] Forms: `aria-describedby` linking labels to error messages

- [ ] Keyboard Navigation
  - [ ] Tab order: form inputs, buttons, links (logical flow)
  - [ ] Focus indicators: 2px solid #d4af37 outline with 2px offset
  - [ ] Trap focus during book animation (make inputs disabled, re-enable after)
  - [ ] ESC on open book returns to login

- [ ] Screen Reader Support
  - [ ] Skip link: "Skip to main content" hidden link at top
  - [ ] Announcement on page-turn: aria-live="polite" updates
  - [ ] Form validation errors: announced immediately via aria-alert

- [ ] Color Contrast Verification
  - [ ] Text on dark backgrounds: #e8d5b7 on #201530 = 12.1:1 ✅
  - [ ] Button borders: check 3:1 ratio vs background
  - [ ] Icon colors: ensure visible on backgrounds

- [ ] Motion Preferences
  - [ ] Respect `prefers-reduced-motion: reduce` (already done)
  - [ ] Optional: Add Settings page toggle for "Reduce animations"

### Priority 6: Font Loading & Fallbacks
🎯 **Low Value** — already working with fallbacks, nice-to-have

- [ ] Self-Host Fonts (Optional)
  - [ ] Download Cinzel & BadScript from Google Fonts
  - [ ] Place in `/static/fonts/`
  - [ ] Update `fonts.css` to use local paths with `@font-face`
  - [ ] Add fallback: `font-family: 'Cinzel', Georgia, serif;`
  - [ ] Test: Verify no CORS errors, fonts load in 100ms

---

## CSS Architecture for M3

### File Organization
```
vtt_app/static/css/
├── spellbook-theme.css         (color vars, dark mode vars)
├── book-scene.css              (3D book structure + responsive)
├── components.css              [NEW] (forms, buttons, pages)
├── responsive.css              [NEW] (breakpoint-specific layout)
└── fonts.css                   (font imports)
```

### CSS Variables to Define
```css
:root {
    /* Colors */
    --vtt-accent: #d4af37;
    --vtt-text-primary: #e8d5b7;
    --vtt-text-secondary: #9e8fa0;
    --vtt-surface-card: #201530;
    --vtt-surface-input: #141420;
    --vtt-border-subtle: rgba(255,255,255,0.10);
    --vtt-success: #4ade80;
    --vtt-error: #ff6b6b;

    /* Spacing */
    --vtt-spacing-xs: 4px;
    --vtt-spacing-sm: 8px;
    --vtt-spacing-md: 16px;
    --vtt-spacing-lg: 24px;
    --vtt-spacing-xl: 32px;

    /* Typography */
    --vtt-font-heading: 'Cinzel', Georgia, serif;
    --vtt-font-body: 'Segoe UI', Arial, sans-serif;
    --vtt-font-mono: 'Courier New', monospace;

    /* Book Dimensions */
    --vtt-book-width: 600px;
    --vtt-book-height: 750px;
    --vtt-page-padding: 40px;
}

@media (max-width: 1023px) {
    :root {
        --vtt-book-width: 500px;
        --vtt-book-height: 650px;
        --vtt-page-padding: 30px;
    }
}

@media (max-width: 767px) {
    :root {
        --vtt-book-width: 100%;
        --vtt-book-height: auto;
        --vtt-page-padding: 20px;
    }
}
```

---

## Testing Checklist for M3 Complete

### Functional Testing
- [ ] Book opens automatically on login page load
- [ ] Login form submits and page-turns to dashboard
- [ ] Dashboard navigates to campaigns page with page-turn
- [ ] Campaigns navigates to characters page
- [ ] Back navigation works (breadcrumb or back button)
- [ ] Keyboard: Arrow keys navigate pages
- [ ] Keyboard: Tab cycles through form fields
- [ ] Form validation shows/hides error messages correctly

### Visual Testing
- [ ] Book dimensions correct on desktop/tablet/mobile
- [ ] Single-page view on mobile, 2-page on desktop
- [ ] Page numbers visible (desktop only)
- [ ] Bookmark moves to correct position on navigation
- [ ] Spine shadow visible and realistic
- [ ] Form background distinct from page background
- [ ] Text contrast acceptable (12:1+ for off-white on dark)
- [ ] No text overflow at any breakpoint

### Performance Testing
- [ ] Page-turn animation smooth (60fps, no jank)
- [ ] Book open animation smooth (0.8s cover flip)
- [ ] GSAP animations don't cause layout thrashing
- [ ] Fonts load within 200ms (or fallback gracefully)
- [ ] No console errors or warnings

### Accessibility Testing
- [ ] Screen reader announces book region
- [ ] Focus indicators visible on all interactive elements
- [ ] Keyboard-only user can navigate entire interface
- [ ] Form validation errors announced to screen readers
- [ ] prefers-reduced-motion: reduce disables animations
- [ ] Color contrast passes WCAG AA (4.5:1+)
- [ ] Touch targets are 44×44px minimum

### Cross-Browser Testing
- [ ] Chrome 90+ (baseline)
- [ ] Firefox 88+
- [ ] Safari 14+
- [ ] Edge 90+
- [ ] Mobile browsers (iOS Safari, Chrome Android)

---

## Definition of Done (M3 Complete)

✅ All Priority 1 items complete (page-turn navigation)
✅ All Priority 2 items complete (visual polish)
✅ All Priority 3 items complete (form stability)
✅ Responsive breakpoints tested on 3+ devices
✅ Accessibility: WCAG 2.1 Level AA achieved
✅ Zero console errors
✅ Manual testing passed: functional, visual, performance, a11y
✅ Git commit with feature branch merged to main
✅ Deployed to vtt.roll-drauf.de staging for user review

