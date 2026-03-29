# M2: DISCOVER — Current State Analysis & Book UI Design Spec

**Phase**: DAD-M DISCOVER
**Milestone**: M2 (Week 2)
**Objective**: Establish baseline design system + identify visual/functional gaps before M3 (APPLY)

---

## 1. Current State Audit

### 1.1 What's Working ✅

**Login Page (book-scene.js + book-scene.css)**
- ✅ 3D book renders correctly with GSAP animations (rotationY fix applied)
- ✅ Book opens on page load with smooth cover flip (-160° rotation, 1.2s ease)
- ✅ Login form fades in after book opens (opacity transition, z-index: 9001)
- ✅ Spellbook theme colors applied (#d4af37 gold accents, #e8d5b7 off-white text, dark purples #4a235a)
- ✅ Book HTML structure correct (cover, pages stack, back cover using preserve-3d)
- ✅ Local GSAP loading (no CDN issues after fix)
- ✅ Responsive base: CSS has 3 breakpoints (1000px desktop, 768px tablet, 480px mobile)

**Dashboard Page**
- ✅ Dark theme applied with correct color vars
- ✅ Stat cards showing campaign/character counts
- ✅ Grid layout for campaign/character cards
- ✅ goTo() function ready for page-turn navigation integration

### 1.2 Visual Gaps Identified 🔴

| Gap | Location | Severity | Details |
|-----|----------|----------|---------|
| **Book dimensions unbalanced** | book-scene.css | HIGH | 550w × 700h (78% height ratio) vs desktop modern book ratio (65% width/height on tablet) |
| **No spine/binding effect** | book-cover | MEDIUM | Real books have visible spine on cover, adds depth |
| **Missing page numbers** | book-open-page | MEDIUM | Game books have page numbers, aids navigation |
| **No texture/aging** | .book-cover, .book-pages | MEDIUM | Flat gradient lacks paper texture, aged parchment feel |
| **Login form padding/positioning** | login.html | MEDIUM | Form floating in center with no reference to book structure |
| **No bookmark visual** | book-scene | LOW | Tabbed bookmark on spine adds authenticity |
| **Font rendering** | login.html | MEDIUM | Cinzel/BadScript fonts failing to load from CDN (console warns) |
| **No page edge detail** | book-pages | MEDIUM | Missing top/bottom page edge shadow/layering |
| **Mobile single-page not styled** | dashboard.html | LOW | Desktop shows 2-column grid; mobile should show single page |
| **Navigation state not tracked** | goTo() | MEDIUM | No breadcrumb or "current page" indicator |

### 1.3 Performance Baseline

**Animation Performance:**
- Book opening: ~2.0s timeline (0.8s book rotation + 1.2s cover flip + 0.6s fade)
- No reported jank/stuttering on tested browsers
- GSAP force3D: true enables GPU acceleration ✅

**Accessibility (WCAG 2.1 baseline):**
- ❌ No aria-labels on book elements
- ❌ No keyboard navigation (keyboard trap: login form not tab-accessible during animation)
- ❌ No focus indicators visible
- ❌ Contrast ratio check needed (off-white #e8d5b7 on dark #201530 = ~12:1 ✅ passes WCAG AAA)
- ✅ prefers-reduced-motion: reduce implemented (animations disabled)
- ❌ No alt text patterns for emoji icons

---

## 2. Book UI Design Specification

### 2.1 Target Design System

**Book Metaphor Principles** (from M1 research):
1. Authenticity with usability — don't sacrifice function for looks
2. Progressive disclosure — reveal controls as user needs them
3. Physical metaphors only where they aid understanding
4. Responsive: Desktop 2-page spread, Mobile single page

**Visual Hierarchy**:
```
Level 1: Book Shell (cover, spine, pages) — persistent, decorative
Level 2: Page Content (forms, cards, lists) — primary interaction
Level 3: Controls (buttons, inputs) — secondary, contextual
Level 4: Feedback (validation, loading states) — transient
```

### 2.2 Dimensions & Spacing

**Desktop (1000px+)**:
- Book: 600w × 750h (80% viewport height, centered)
- 2-page spread: left 300w + right 300w
- Page padding: 40px internal margins
- Gutter (spine): 20px between pages

**Tablet (768px - 999px)**:
- Book: 500w × 650h
- Still 2-page capable, reduced padding
- Page padding: 30px

**Mobile (<768px)**:
- Book: 320w × 480h (full-screen minus header/footer)
- Single page view (left page only visible)
- Page padding: 20px
- Bookmarks/navigation shift to right edge

**Responsive Spine Adjustment**:
```css
/* Desktop */
#book { width: 600px; height: 750px; }
.book-cover { width: 300px; }  /* covers 50% of #book width */

/* Tablet */
#book { width: 500px; height: 650px; }
.book-cover { width: 250px; }

/* Mobile */
#book { width: 320px; height: 480px; }
.book-cover { width: 320px; }  /* full width, pages hidden */
```

### 2.3 Color Palette (Spellbook Theme)

**Core Colors**:
```
Primary Accent (gold):        #d4af37
Primary Text (off-white):     #e8d5b7
Secondary Text (muted gray):  #9e8fa0
Dark Surface (card bg):       #201530
Dark Surface (input bg):      #141420
Border (subtle):              rgba(255,255,255,0.10)
Success:                      #4ade80
Error:                        #ff6b6b
Warning:                      #fbbf24
```

**Cover Gradients**:
```
Front Cover: linear-gradient(135deg, #3d1f4e → #4a235a → #3a1a48)
Back Cover:  linear-gradient(135deg, #3a1a48 → #4a235a)
Pages:       linear-gradient(90deg, #e8d5b7 → #f5e6d3 → #e8d5b7)
Spine:       Box-shadow inset -8px 0 20px rgba(0,0,0,0.5)
```

### 2.4 Typography

**Font Stack**:
```
Headings (h1-h3): 'Cinzel', 'Georgia', serif (fallback: serif)
Body Text:        'Segoe UI', 'Arial', sans-serif (fallback: sans-serif)
Monospace (code): 'Courier New', monospace
```

**Sizing (Responsive)**:
```
Desktop:
  h1 (page title):    2rem (32px)
  h2 (section):       1.3rem (21px)
  body:               1rem (16px)
  small (meta):       0.85rem (14px)

Tablet:
  h1: 1.8rem, h2: 1.2rem, body: 0.95rem

Mobile:
  h1: 1.5rem, h2: 1.1rem, body: 0.9rem
```

**Font Weights**:
- Headings: 600-700 (semibold-bold)
- Body: 400 (regular)
- Accent text: 600 (semibold)

### 2.5 Component Library (To Build in M3)

**Essential Components**:
1. **Page (layout wrapper)**
   - Left page, right page, or full-width single page
   - Automatic page number footer
   - Decorative page border

2. **Page Number (footer element)**
   - Centered at bottom of page
   - Small serif, centered alignment
   - Only visible on desktop 2-page spread

3. **Bookmark (navigation indicator)**
   - Ribboned tab on right edge of book
   - Indicates current section (Campaigns, Characters, Inventory, etc.)
   - Animated slide up/down on navigation

4. **Spine/Binding (decorative)**
   - Box-shadow inset on cover edges
   - 12-15px visible depth
   - Subtle texture pattern

5. **Form Wrapper (login, create campaign)**
   - Centered on page with generous padding
   - Label-on-top layout (mobile-first)
   - Input fields with focus indicators
   - Button with hover state

6. **Card Grid (campaigns, characters)**
   - Responsive: 3 col (desktop) → 2 col (tablet) → 1 col (mobile)
   - Hover: border highlight + shadow lift
   - Click: page-turn transition

7. **Navigation Menu**
   - Inside book header (top of page)
   - Breadcrumb style: "Dashboard > Campaigns"
   - Can hide/show with button (hamburger mobile)

---

## 3. Accessibility Baseline

### 3.1 WCAG 2.1 Level AA Compliance Checklist

| Criterion | Status | Fix Required |
|-----------|--------|--------------|
| **1.4.3 Contrast (AA)** | ✅ Pass | Off-white #e8d5b7 on #201530 = 12.1:1 ratio (exceeds 4.5:1 AA) |
| **1.4.11 Non-Text Contrast (AA)** | ⚠️ Check | Button borders must have 3:1 ratio vs background |
| **2.1.1 Keyboard (A)** | ❌ Fail | Form not accessible during book opening animation |
| **2.1.4 Character Key Shortcuts (A)** | ❌ Not Implemented | Page-turn shortcuts (arrow keys) not defined |
| **2.3.3 Animation from Interactions (AAA)** | ⚠️ Partial | prefers-reduced-motion respected, but no option to disable animations in UI |
| **2.5.5 Target Size (AAA)** | ⚠️ Check | Buttons should be 44×44px minimum (current 40-45px border) |
| **3.2.4 Consistent Identification (A)** | ⚠️ Check | Icons (📋 🧙 🏰 🗡️) need aria-label or title text |
| **4.1.3 Status Messages (AAA)** | ❌ Not Implemented | Loading states, form validation not announced to screen readers |
| **ARIA Labels** | ❌ Missing | All interactive elements need aria-label, aria-describedby |

### 3.2 Quick Wins (Easy Accessibility Fixes)

1. **Add aria-labels to book elements**:
   ```html
   <div id="book" role="region" aria-label="Spellbook opening animation">
   <div class="book-cover" aria-label="Book front cover - click to open">
   ```

2. **Make form accessible during animation**:
   ```javascript
   // Set pointer-events: auto on login-content immediately (not after fade)
   // Allow form submission even before animation completes
   ```

3. **Add keyboard navigation**:
   ```javascript
   // ESC to close book, Tab to navigate form, Enter to submit
   // Arrow keys to page-turn between sections
   ```

4. **Add motion preference option**:
   ```html
   <!-- Settings page: "Reduce animations" toggle -->
   <!-- Stores in localStorage, disables GSAP on reload -->
   ```

### 3.3 Font Loading Accessibility

**Current Issue**: Cinzel & BadScript fonts failing to load from Google Fonts CDN.
**Impact**: Fallback serif fonts render, slightly different metrics but readable.
**Fix Options**:
1. Self-host font files in `/static/fonts/` (recommended)
2. Use system serif fonts instead (e.g., Georgia)
3. Async load + fallback pattern

---

## 4. Device Breakpoints & Responsive Behavior

### 4.1 Breakpoint Map

```css
/* Mobile First */

/* Mobile (320px - 767px) */
@media (max-width: 767px) {
    /* Single-page book layout */
    #book { width: 320px; height: 480px; }
    /* Hide right page */
    .book-pages { display: none; }
    /* Full-width controls */
}

/* Tablet (768px - 1023px) */
@media (min-width: 768px) and (max-width: 1023px) {
    /* 2-page capable but smaller */
    #book { width: 500px; height: 650px; }
    /* Show both pages */
    .book-pages { display: flex; }
    /* Reduced padding */
}

/* Desktop (1024px+) */
@media (min-width: 1024px) {
    /* Full-size 2-page spread */
    #book { width: 600px; height: 750px; }
    /* Maximum comfort reading width */
}

/* Large Screens (1600px+) */
@media (min-width: 1600px) {
    /* Increase spacing around book, not book size */
    /* (Optimal reading width is 600px regardless) */
}

/* Ultra-wide (2000px+) */
@media (min-width: 2000px) {
    /* Consider dual-book layout for multi-user scenarios */
    /* Out of scope for VTT 1.0 */
}
```

### 4.2 Breakpoint-Specific Behaviors

**Mobile (320px):**
- Single page visible (left/top page)
- Book fills screen height minus header (50-60px)
- Right page hidden or stacked below (for page-turn animation preview)
- Navigation: hamburger menu or bottom tabs
- Touch-friendly buttons: 44px minimum

**Tablet (768px):**
- 2-page spread centered in viewport
- Gutter between pages visible (10-15px)
- Side margins: 20-30px
- Navigation: top menu bar + breadcrumb

**Desktop (1024px+):**
- 2-page spread as primary interface
- Consistent margins: 40-60px sides
- Bookmarks on right edge (navigation indicator)
- Sidebar navigation optional

---

## 5. Current Code State Summary

### 5.1 File Structure
```
vtt_app/
├── static/
│   ├── css/
│   │   ├── spellbook-theme.css    (color vars, dark mode)
│   │   ├── book-scene.css         (3D book styles)
│   │   ├── book-animation.js      (old particle system - can deprecate)
│   │   └── fonts.css              (font imports)
│   ├── js/
│   │   ├── gsap.min.js            (local GSAP copy)
│   │   ├── book-scene.js          (book open/close logic)
│   │   ├── auth.js                (login/auth)
│   │   └── book-animation.js      (old - can remove in M3 cleanup)
│   └── (other assets)
├── templates/
│   ├── login.html                 (book + form)
│   ├── dashboard.html             (stats + grids)
│   ├── campaigns.html             (campaigns grid)
│   ├── characters.html            (characters grid)
│   └── (other pages)
└── (backend routes)
```

### 5.2 Known Issues for M3 APPLY

1. **Font loading**: Cinzel/BadScript not loading → use system fallbacks
2. **No page-turn animation skeleton**: goTo() ready but pageTurn() not implemented
3. **Navigation state**: No breadcrumb or active section indicator
4. **Mobile book sizing**: Needs testing on actual devices
5. **Form validation**: No inline error messages or field indicators
6. **Loading states**: No spinner or skeleton screens during API calls

---

## 6. Design Specification Output (For M3 APPLY)

### Component Recipes

**Recipe 1: Book Container**
```css
.book-container {
    width: 600px;       /* 1024px+ */
    height: 750px;
    position: relative;
    perspective: 1000px;
    transform-style: preserve-3d;
}

@media (max-width: 1023px) {
    .book-container { width: 500px; height: 650px; }
}

@media (max-width: 767px) {
    .book-container { width: 100vw; height: auto; aspect-ratio: 320/480; }
}
```

**Recipe 2: Page Layout**
```css
.book-page {
    width: 50%;        /* When 2-page */
    background: linear-gradient(90deg, #e8d5b7 0%, #f5e6d3 100%);
    padding: 40px;
    color: #4a235a;
    font-family: 'Segoe UI', sans-serif;
    font-size: 1rem;
    line-height: 1.6;
}

.book-page-number {
    position: absolute;
    bottom: 20px;
    font-family: 'Cinzel', serif;
    font-size: 0.9rem;
    color: rgba(0,0,0,0.3);
}
```

**Recipe 3: Form Container**
```css
.book-form {
    max-width: 400px;
    margin: 0 auto;
    padding: 30px 20px;
}

.form-group {
    margin-bottom: 20px;
}

.form-label {
    display: block;
    font-weight: 600;
    margin-bottom: 8px;
    color: #4a235a;
}

.form-input {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid rgba(0,0,0,0.15);
    border-radius: 4px;
    font-size: 1rem;
    transition: border-color 0.2s, box-shadow 0.2s;
}

.form-input:focus {
    outline: none;
    border-color: #d4af37;
    box-shadow: 0 0 8px rgba(212, 175, 55, 0.3);
}
```

---

## Next Steps (M3 Preparation)

✅ **M2 Complete**: Baseline defined, gaps identified, spec created

🔲 **M3 APPLY Phase**:
- Implement page-number component
- Add spine/binding visual effects
- Implement page-turn navigation animation
- Build bookmark indicator
- Update responsive breakpoints on all templates
- Self-host fonts
- Add ARIA labels to book elements
- Stabilize form within book context

**Estimated Duration**: 1 week
**Priority**: Visual polish first, then accessibility

