# M2: Visual Target Reference & Design System

**Purpose**: Visual guide showing what M3 should produce

---

## Desktop (1024px+) — Two-Page Spread Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                          BROWSER WINDOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                        ┌─────────────────────┐                 │
│                        │  📖 SPELLBOOK OPEN  │                 │
│                        │                     │                 │
│        ┏━━━━━━━━━━━━━┓ │ ┌─────────────────┐ │ ┌─────────────┐ │
│        ┃             ┃ │ │ PAGE 1: LOGIN   │ │ │  PAGE 2:    │ │
│        ┃  LEFT PAGE  ┃ │ │ (Initial Form)  │ │ │  DASHBOARD  │ │
│        ┃             ┃ │ │                 │ │ │  (if logged)│ │
│        ┃   [FORM]    ┃ │ └─────────────────┘ │ │             │ │
│        ┃             ┃ │ [Page Number: 1]    │ │             │ │
│        ┗━━━━━━━━━━━━━┛ │ ╱╱╱ SPINE ╱╱╱      │ │   [Stats]   │ │
│                        │ └─────────────────┘ │ │   [Grid]    │ │
│                        │                     │ │             │ │
│        Bookmark ───→ 🎀                      │ └─────────────┘ │
│        (Current Page)  │                     │                 │
│                        └─────────────────────┘                 │
│                                                                 │
│  [Dashboard] [Campaigns] [Characters] [Logout]   ← Header Nav  │
└─────────────────────────────────────────────────────────────────┘

Dimensions:
  Book width: 600px (300px per page + 20px gutter)
  Book height: 750px
  Gutter/spine: 20px between pages
  Page padding: 40px internal
  Margins: 40-60px around book
  Bookmark height: 80px, width: 12px, positioned right edge
```

**Key Visual Elements**:
- Gold accent border (#d4af37) on book edges
- Inset shadow on spine (left side of center) = binding effect
- Page background: parchment gradient (#e8d5b7 → #f5e6d3)
- Page numbers: centered bottom, Cinzel font, subtle gray
- Bookmark: gold ribbon positioned on current section (moves on nav)

---

## Tablet (768px) — Still Two-Page Capable

```
┌────────────────────────────────────────────┐
│           TABLET VIEWPORT (768px)          │
├────────────────────────────────────────────┤
│          ┏━━━━━━━━━━━━━━━━━━━┓            │
│          ┃                   ┃            │
│    ┌─────┃  TWO-PAGE SPREAD  ┃─────┐    │
│    │ ┌──┃─────┬──────────────┃──┐  │    │
│    │ │Pg│  1  │  PAGE 2      │2 │  │    │
│    │ │  │     │  (or content)│  │  │    │
│    │ │  │     │              │  │  │    │
│    │ │  │ [F] │   [CONTENT]  │  │  │    │
│    │ │  │ [O] │              │  │  │    │
│    │ │  │ [R] │              │  │  │    │
│    │ │  │ [M] │              │  │  │    │
│    │ └──┃─────┴──────────────┃──┘  │    │
│    └─────┃                   ┃─────┘    │
│          ┗━━━━━━━━━━━━━━━━━━━┛          │
│                                        │
└────────────────────────────────────────────┘

Dimensions:
  Book width: 500px
  Book height: 650px
  Margins: 20-30px
  Page padding: 30px
  Gutter: 10px
```

---

## Mobile (320px) — Single-Page View

```
┌──────────────────────────────┐
│   MOBILE (375px - iPhone SE) │
├──────────────────────────────┤
│                              │
│        ┏━━━━━━━━━━━━┓        │
│        ┃  SPELLBOOK ┃        │
│        ┃            ┃        │
│        ┃ [FORM OR]  ┃        │
│        ┃ [CONTENT]  ┃        │
│        ┃            ┃        │
│        ┃            ┃        │
│        ┗━━━━━━━━━━━━┛        │
│                              │
│      Navigation (Bottom)     │
│   [◀] [HOME] [NEXT] [▶]     │
│                              │
└──────────────────────────────┘

Dimensions:
  Book: 320px wide, full height
  Margin: 10px sides
  Padding: 20px
  Single page layout
  Navigation in header or bottom
  Bookmark hidden (shown in section indicators)
```

---

## Page Turn Animation Sequence

**Frame 0 (start)**:
```
┌──────────────────────┐
│  Current Page Visible│  (dashboard)
│  rotateY: 0°         │
└──────────────────────┘
```

**Frame 1 (midpoint @ t=0.3s)**:
```
┌──────────────────────┐
│       ▲ ▼            │  (edge-on, perpendicular to screen)
│  rotateY: -90°       │  (invisible, at this point navigate)
└──────────────────────┘
```

**Frame 2 (end @ t=0.6s)**:
```
┌──────────────────────┐
│  Next Page Visible   │  (campaigns)
│  rotateY: -180°      │
└──────────────────────┘
```

**GSAP Timeline Pseudo-Code**:
```javascript
gsap.timeline()
  .to(pageOverlay, {
    rotationY: -180,     // rotateY (CSS) → rotationY (GSAP camelCase)
    duration: 0.6,
    ease: 'power2.inOut',
    force3D: true        // GPU acceleration
  }, 0)
  .eventCallback('onUpdate', () => {
    if (timeline.progress() === 0.5) {
      window.location.href = nextPageUrl;  // Navigate at midpoint
    }
  });
```

---

## Form Component Anatomy

### Login Form (on book page)

```
         ┌─────────────────────────────────┐
         │     [Roll Drauf Spellbook]      │
         │                                 │
         │   ┌─────────────────────────┐   │
         │   │ Form Container          │   │
         │   │ (bg: rgba(0,0,0,0.1))   │   │
         │   │ (border: 1px gold-ish)  │   │
         │   │                         │   │
         │   │  Benutzername *         │   │
         │   │  [______________]       │   │
         │   │   ↳ error msg (red)     │   │
         │   │                         │   │
         │   │  Passwort *             │   │
         │   │  [______________]       │   │
         │   │   ↳ error msg (red)     │   │
         │   │                         │   │
         │   │  ┌─────────────────┐    │   │
         │   │  │     ENTER       │    │   │
         │   │  │ (hover: glow)   │    │   │
         │   │  └─────────────────┘    │   │
         │   │                         │   │
         │   │ Noch kein Konto?        │   │
         │   │ [Jetzt anmelden]        │   │
         │   └─────────────────────────┘   │
         │                                 │
         └─────────────────────────────────┘

Styling:
  Label: Cinzel, 14px, #4a235a
  Input: 44px height, rgba(0,0,0,0.15) bg, 2px border
  Button: 44px height, 16px font, gradient bg, hover glow
  Error: #ff6b6b, 12px, margin-top 4px
  Focus outline: 2px solid #d4af37
```

---

## Component State Diagram

```
                    ┌─────────────────┐
                    │  BOOK CLOSED    │
                    │ (Page Load)     │
                    └────────┬────────┘
                             │ autoplay
                             ▼
           ╔═══════════════════════════════════╗
           ║  BOOK OPENING ANIMATION           ║
           ║  (2s: cover flip + form fade)     ║
           ╚═════════════════╤══════════════════╝
                             │
                             ▼
                    ┌─────────────────┐
                    │  BOOK OPEN      │
                    │ LOGIN FORM LIVE │
                    └────────┬────────┘
                             │
                ┌────────────┼────────────┐
                │                        │
         [Submit]                   [Signup]
                │                        │
                ▼                        ▼
      ┌──────────────────┐    ┌──────────────────┐
      │ PAGE TURN ANIM   │    │ Navigate to      │
      │ 0.6s duration    │    │ signup.html      │
      │ Navigate to      │    │ Direct redirect  │
      │ /dashboard       │    │                  │
      └────────┬─────────┘    └──────────────────┘
               │
               ▼
      ┌──────────────────┐
      │  DASHBOARD PAGE  │
      │  BOOK OPEN       │
      │  PAGE 1-2 SHOWN  │
      └────────┬─────────┘
               │
        ┌──────┼──────────┐
        │                 │
    [Campaigns]      [Characters]
    [Page Turn]      [Page Turn]
        │                 │
        ▼                 ▼
   ┌──────────┐      ┌──────────────┐
   │CAMPAIGNS │      │ CHARACTERS   │
   │PAGE 3-4  │      │ PAGE 5-6     │
   └──────────┘      └──────────────┘
```

---

## Color Palette Application

### Dark Mode (Current Implementation)

```
Background (page):        #e8d5b7 (parchment)
Background (dark):        #201530 (dark purple card)
Text Primary:             #e8d5b7 (off-white - used in headers)
Text Secondary:           #9e8fa0 (muted gray)
Accent (interactive):     #d4af37 (gold)
Border:                   rgba(255,255,255,0.10)
Success:                  #4ade80 (green - for valid state)
Error:                    #ff6b6b (red - for errors)
Warning:                  #fbbf24 (amber - for warnings)
```

### Contrast Verification

```
Off-white (#e8d5b7) on dark (#201530):
  Luminance check: 12.1:1 ratio ✅ (exceeds 4.5:1 AA, exceeds 7:1 AAA)

Gold (#d4af37) on dark (#201530):
  Luminance check: 8.3:1 ratio ✅ (exceeds 4.5:1 AA)

Muted gray (#9e8fa0) on dark (#201530):
  Luminance check: 6.2:1 ratio ✅ (exceeds 4.5:1 AA)
```

---

## Typography Hierarchy

```
h1 (Page Title)
├─ Font: Cinzel, 2rem (desktop) / 1.8rem (tablet) / 1.5rem (mobile)
├─ Weight: 700 (bold)
├─ Color: #d4af37 (gold)
├─ Letter-spacing: 1px
└─ Example: "Dashboard", "Spellbook"

h2 (Section Title)
├─ Font: Cinzel, 1.3rem (desktop) / 1.2rem (tablet) / 1.1rem (mobile)
├─ Weight: 700
├─ Color: #d4af37
└─ Example: "Recent Campaigns", "Characters"

h3 (Card Title)
├─ Font: Cinzel, 1.1rem
├─ Weight: 700
├─ Color: #e8d5b7
└─ Example: "Storm's Fury", "The Wizard"

body (Regular Text)
├─ Font: Segoe UI, 1rem (desktop) / 0.95rem (tablet) / 0.9rem (mobile)
├─ Weight: 400
├─ Color: #e8d5b7
├─ Line-height: 1.6
└─ Example: Card descriptions, form labels

small (Meta Text)
├─ Font: Segoe UI, 0.85rem
├─ Weight: 400
├─ Color: #9e8fa0
└─ Example: "Lvl 5 Wizard • Human", "Status: Active"

code (Monospace)
├─ Font: Courier New, 0.9rem
├─ Color: #4ade80 (success green for code)
└─ Example: API responses, JSON data
```

---

## Responsive Behavior Matrix

| Element | Desktop (1024px) | Tablet (768px) | Mobile (320px) |
|---------|------------------|----------------|----------------|
| **Book Width** | 600px | 500px | 320px (full) |
| **Book Height** | 750px | 650px | Auto (aspect) |
| **Layout** | 2-page spread | 2-page (condensed) | 1-page (stacked) |
| **Page Padding** | 40px | 30px | 20px |
| **Gutter** | 20px | 10px | N/A |
| **Grid Columns** | 3 cols | 2 cols | 1 col |
| **Sidebar** | Visible (40px) | Hidden | Hidden |
| **Header** | Top nav bar | Top nav bar | Hamburger menu |
| **Footer** | Page numbers | Page numbers | Hidden |
| **Page Number Font** | 0.9rem | 0.8rem | N/A |
| **Bookmark** | Visible (12px wide) | Visible (10px) | Hidden |
| **Touch Target Size** | 44px (min) | 44px (min) | 44px (min) |

---

## Animation Timing Reference

| Animation | Duration | Easing | Use Case |
|-----------|----------|--------|----------|
| Book Open | 2.0s total | power2.out | Initial load |
| ├─ Book rotation | 0.8s | power2.out | Straighten book |
| ├─ Cover flip | 1.2s | power2.inOut | Main action |
| ├─ Pages rustle | 0.4s | sine.inOut | Texture effect |
| └─ Form fade-in | 0.6s | power2.out | Content reveal |
| Page Turn | 0.6s | power2.inOut | Navigation |
| Button Hover | 0.3s | ease | Interactive feedback |
| Focus Outline | 0.2s | ease | Keyboard focus |
| Error Shake | 0.3s | easeInOut | Validation feedback |
| Bookmark Slide | 0.3s | ease | Section indicator |

---

## Accessibility Color & Motion Considerations

### prefers-reduced-motion: reduce

```css
@media (prefers-reduced-motion: reduce) {
    /* Disable all animations */
    #book,
    .book-cover,
    .page-turn-overlay,
    button,
    [aria-live] {
        animation: none !important;
        transition: none !important;
    }

    /* Instant page changes instead of animation */
    .book-pages { opacity: 1; }
    #login-content { opacity: 1; }
}
```

### High Contrast Mode (Windows)

```css
@media (prefers-contrast: more) {
    /* Increase border width */
    .book-cover { border-width: 3px; }

    /* Increase text weight */
    h1, h2, h3 { font-weight: 900; }

    /* Remove transparency */
    input { background: #141420 !important; }
    button { background: #4a235a !important; }
}
```

---

## Summary: What M3 Will Add to M2

✅ Current (M2): Functioning book open animation, basic login form
🔲 M3 Adds:
- Page numbers (each page numbered 1-6)
- Bookmark visual with section indicators
- Enhanced spine/binding shadows
- Page-turn navigation between pages
- Form validation with error messages
- Responsive single-page mobile view
- Keyboard navigation (arrows, tab, escape)
- ARIA labels for accessibility
- Self-hosted fonts (optional)
- CSS component system (reusable form, button, card styles)

