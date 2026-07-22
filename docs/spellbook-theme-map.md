# Spellbook Theme - Implementation Mapping (Phase 2 & 3)

**Status:** Phase 1 ✅ Complete → Moving to Phase 2
**Goal:** Asset-to-CSS Mapping & CSS Integration
**Timeline:** 2-3 hours total

---

## 📊 IMPLEMENTATION PHASES

```
Phase 1: ✅ Download & Organize (COMPLETE)
├── Create directory structure ✓
├── Generate download checklists ✓
├── Create manual instruction docs ✓
└── Ready for manual asset downloads

Phase 2: ⏳ Asset Optimization (Next)
├── Download all assets from sources
├── Organize files by category
├── Compress images (PNG optimization)
├── Convert fonts to WOFF2
├── Verify quality & colors
└── Ready for CSS integration

Phase 3: ⏳ CSS Integration (Final)
├── Create CSS custom properties (variables)
├── Map assets to CSS classes
├── Update HTML templates
├── Test dark mode / light mode
├── Browser testing
└── Deploy to production
```

---

## 🗺️ ASSET MAPPING DETAIL

### **Category 1: BACKGROUND TEXTURES**

#### 1.1 Galaxy/Nebula Backgrounds
```
Source Files (from Pixabay):
├── bg-galaxy-dark.png (2560x1440)
├── bg-galaxy-purple.png (2560x1440)
├── bg-galaxy-cosmic.png (2560x1440)
└── bg-nebula-pink.png (2560x1440)

CSS Integration:
:root {
    --vtt-bg-galaxy-dark: url('/static/images/textures/bg-galaxy-dark.png');
    --vtt-bg-galaxy-purple: url('/static/images/textures/bg-galaxy-purple.png');
}

Usage in Templates:
<div class="hero-section-galaxy">
    /* background-image: var(--vtt-bg-galaxy-dark); */
</div>

Templates to Update:
- vtt_app/templates/play.html (Hero Section)
- vtt_app/templates/campaigns.html (DM Lobby)
```

#### 1.2 Parchment Textures
```
Source Files (from AmbientCG):
├── texture-parchment-light.png
├── texture-parchment-aged.png
└── texture-parchment-dark.png

CSS Integration:
:root {
    --vtt-texture-parchment: url('/static/images/textures/texture-parchment-light.png');
    --vtt-texture-parchment-dark: url('/static/images/textures/texture-parchment-dark.png');
}

Usage in CSS:
.content-card {
    background-image: var(--vtt-texture-parchment);
    background-size: 400px 400px;
    opacity: 0.15;
}

Files to Update:
- vtt_app/static/css/spellbook-theme.css (add texture rules)
- vtt_app/static/css/theme.css (add variables)
```

---

### **Category 2: ICON SETS (80-100 Icons)**

#### 2.1 Game-Icons.net SVG Icons (PRIMARY)
```
File Organization:
vtt_app/static/icons/
├── Campaign Category:
│   ├── icon-campaign-book.svg
│   ├── icon-campaign-scroll.svg
│   ├── icon-campaign-library.svg
│   └── icon-campaign-quill.svg
├── Session Category:
│   ├── icon-session-play.svg
│   ├── icon-session-pause.svg
│   ├── icon-session-resume.svg
│   ├── icon-session-time.svg
│   └── icon-session-players.svg
├── Combat Category:
│   ├── icon-combat-swords.svg
│   ├── icon-combat-shield.svg
│   ├── icon-combat-dagger.svg
│   ├── icon-combat-fire.svg
│   └── icon-combat-poison.svg
├── Spell Category:
│   ├── icon-spell-wand.svg
│   ├── icon-spell-sparkles.svg
│   ├── icon-spell-swirl.svg
│   ├── icon-spell-book.svg
│   └── icon-spell-hand.svg
├── Inventory Category:
│   ├── icon-inventory-backpack.svg
│   ├── icon-inventory-chest.svg
│   ├── icon-inventory-potion.svg
│   └── icon-inventory-coin.svg
└── Status/Badge Category:
    ├── icon-status-active.svg
    ├── icon-status-hidden.svg
    ├── icon-badge-dm.svg
    └── icon-badge-combat.svg

Color Customization:
All SVGs need to be colorized (Purple #4a235a + Gold #d4af37)

CSS/HTML Integration:
<img class="icon icon-campaign" src="/static/icons/icon-campaign-book.svg" alt="Campaign">

CSS:
.icon {
    width: 32px;
    height: 32px;
    filter: invert(1) sepia(0.5) hue-rotate(270deg) saturate(1.2);
}

Templates to Update:
- vtt_app/templates/campaigns.html (navigation, action buttons)
- vtt_app/templates/play.html (session controls)
- vtt_app/templates/register.html (form decorations)
```

#### 2.2 Kenney Assets Fantasy Icons (BACKUP/CONSISTENCY)
```
Location (after extraction):
vtt_app/static/icons/kenney-fantasy-*.png

Purpose:
- Consistent UI icon set
- Backup for styles not available in Game-Icons
- UI element icons (settings, close, minimize)

Color Scheme:
- Already matches fantasy aesthetic
- May need slight tint adjustment for Lila/Gold theme

Templates to Update:
- UI components (buttons, dropdowns)
```

---

### **Category 3: ORNAMENTS & DECORATIVE ELEMENTS**

#### 3.1 Borders & Frames (Kenney Fantasy UI)
```
Files:
vtt_app/static/images/ornaments/
├── border-corner-tl.png (top-left)
├── border-corner-tr.png (top-right)
├── border-corner-bl.png (bottom-left)
├── border-corner-br.png (bottom-right)
├── border-h-top.png (horizontal top)
├── border-h-bottom.png (horizontal bottom)
├── border-v-left.png (vertical left)
└── border-v-right.png (vertical right)

CSS Integration:
.card-spellbook {
    border: 2px solid var(--vtt-accent);
    background: linear-gradient(135deg, var(--vtt-light-text), var(--vtt-bg));
    box-shadow:
        inset 0 0 0 1px var(--vtt-accent),
        0 0 20px rgba(212, 175, 55, 0.2);
    position: relative;
}

.card-spellbook::before {
    content: '';
    position: absolute;
    top: -10px;
    left: -10px;
    right: -10px;
    bottom: -10px;
    background-image: url('/static/images/ornaments/border-corner-tl.png');
    background-size: 30px 30px;
    background-position: top left;
    background-repeat: no-repeat;
    pointer-events: none;
}

Templates to Update:
- vtt_app/templates/campaigns.html (session cards)
- vtt_app/templates/play.html (panels)
- Custom component templates
```

#### 3.2 Dividers & Separators
```
Files:
vtt_app/static/images/ornaments/
├── divider-h-gold-thin.svg
├── divider-h-gold-thick.svg
├── divider-h-purple-thin.svg
└── divider-v-gold.svg

CSS Integration:
.divider {
    background-image: url('/static/images/ornaments/divider-h-gold-thin.svg');
    background-size: 100% 4px;
    background-position: center;
    background-repeat: no-repeat;
    height: 4px;
    margin: 20px 0;
}

Templates:
- Between section headers
- Between page sections
```

#### 3.3 Wax Seals & Stamps
```
Files:
vtt_app/static/icons/
├── seal-campaign.svg
├── seal-session.svg
├── seal-combat.svg
└── seal-spell.svg

Usage:
- Logo backgrounds
- Stamp effects on badges
- Authenticity markers

CSS:
.seal {
    width: 120px;
    height: 120px;
    background-image: url('/static/icons/seal-*.svg');
    filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
}
```

#### 3.4 Ribbons & Bookmarks
```
Files:
vtt_app/static/images/ornaments/
├── ribbon-gold-01.svg
├── ribbon-purple-01.svg
└── ribbon-bookmark.svg

Usage:
- Page header ribbons
- Bookmark elements in navigation
- Decorative accents

CSS:
.ribbon {
    position: absolute;
    right: 0;
    top: 10px;
    width: 100px;
    height: auto;
    background-image: url('/static/images/ornaments/ribbon-*.svg');
}
```

---

### **Category 4: BOOK FRAMES & STRUCTURES**

#### 4.1 Open Book Frame
```
Files:
vtt_app/static/images/frames/
├── frame-book-open-01.svg
└── frame-book-open-02.svg

Usage:
- Campaign view center decoration
- Session lobby background frame
- Hero section wrapper

CSS:
.frame-open-book {
    background-image: url('/static/images/frames/frame-book-open-01.svg');
    background-size: contain;
    background-position: center;
    background-repeat: no-repeat;
    min-height: 600px;
    position: relative;
}

Templates:
- vtt_app/templates/campaigns.html (main campaign display)
```

#### 4.2 Page Edge/Curl Effects
```
Files:
vtt_app/static/images/frames/
├── page-edge-curl.svg
├── page-corner-fold.svg
└── page-shadow.svg

CSS:
.page-corner {
    position: absolute;
    bottom: 0;
    right: 0;
    width: 50px;
    height: 50px;
    background-image: url('/static/images/frames/page-corner-fold.svg');
}
```

---

### **Category 5: FONTS**

#### 5.1 Google Fonts (WOFF2)
```
Files:
vtt_app/static/fonts/
├── cinzel-regular.woff2
├── cinzel-bold.woff2
├── badscript-regular.woff2
└── piratione-regular.woff2

CSS Font-Face Definitions:
@font-face {
    font-family: 'Cinzel';
    src: url('/static/fonts/cinzel-regular.woff2') format('woff2');
    font-weight: 400;
}

@font-face {
    font-family: 'Cinzel';
    src: url('/static/fonts/cinzel-bold.woff2') format('woff2');
    font-weight: 700;
}

@font-face {
    font-family: 'BadScript';
    src: url('/static/fonts/badscript-regular.woff2') format('woff2');
}

@font-face {
    font-family: 'PirataOne';
    src: url('/static/fonts/piratione-regular.woff2') format('woff2');
}

CSS Usage:
:root {
    --vtt-font-spellbook-title: 'Cinzel', serif;       /* Page titles */
    --vtt-font-spellbook-subtitle: 'BadScript', script;  /* Subtitles */
    --vtt-font-spellbook-accent: 'PirataOne', serif;     /* Decorative */
}

h1 { font-family: var(--vtt-font-spellbook-title); }
h2 { font-family: var(--vtt-font-spellbook-title); }
.spellbook-accent { font-family: var(--vtt-font-spellbook-accent); }

Templates:
- All headers and titles
- Campaign names
- Session titles
- Spell names
```

---

## 📝 CSS VARIABLE REFERENCE (Complete)

### **Color Variables**
```css
:root {
    /* Existing */
    --vtt-primary: #4a235a;          /* Deep purple */
    --vtt-accent: #d4af37;           /* Gold */
    --vtt-text: #2a2a2a;             /* Dark text */
    --vtt-bg: #f5e6d3;               /* Parchment */
    --vtt-dark-bg: #1a1a1a;          /* Near black */

    /* NEW - Galaxy Backgrounds */
    --vtt-bg-galaxy-dark: url('/static/images/textures/bg-galaxy-dark.png');
    --vtt-bg-galaxy-purple: url('/static/images/textures/bg-galaxy-purple.png');

    /* NEW - Parchment Textures */
    --vtt-texture-parchment: url('/static/images/textures/texture-parchment-light.png');
    --vtt-texture-parchment-dark: url('/static/images/textures/texture-parchment-dark.png');
}

@media (prefers-color-scheme: dark) {
    :root {
        --vtt-text: #f5e6d3;
        --vtt-bg: #1a1a1a;
        --vtt-bg-galaxy: var(--vtt-bg-galaxy-dark);
    }
}
```

### **Font Variables**
```css
:root {
    /* Existing */
    --vtt-font-body: 'Segoe UI', sans-serif;
    --vtt-font-heading: 'Georgia', serif;

    /* NEW - Spellbook Fonts */
    --vtt-font-spellbook-title: 'Cinzel', serif;
    --vtt-font-spellbook-subtitle: 'BadScript', script;
    --vtt-font-spellbook-accent: 'PirataOne', serif;
}
```

### **Image/Asset Variables**
```css
:root {
    /* Frame Images */
    --vtt-img-frame-book: url('/static/images/frames/frame-book-open-01.svg');

    /* Dividers */
    --vtt-img-divider-gold: url('/static/images/ornaments/divider-h-gold-thin.svg');

    /* Seals */
    --vtt-img-seal-campaign: url('/static/icons/seal-campaign.svg');
}
```

---

## ✅ PHASE 2: ASSET OPTIMIZATION CHECKLIST

After downloading all assets:

- [ ] Verify all image files downloaded (150+ files)
- [ ] Check image resolutions (min 2K for backgrounds)
- [ ] Convert PNG files to optimized format (TinyPNG or similar)
- [ ] Convert all SVG colors to match theme (#4a235a, #d4af37)
- [ ] Convert fonts to WOFF2 (all .ttf → .woff2)
- [ ] Create CSS variables document
- [ ] Generate asset inventory JSON (for documentation)
- [ ] Test file sizes and load times

---

## ✅ PHASE 3: CSS INTEGRATION CHECKLIST

After optimization:

- [ ] Update `vtt_app/static/css/theme.css` with new variables
- [ ] Update `vtt_app/static/css/spellbook-theme.css` with asset usage
- [ ] Create `vtt_app/static/css/fonts.css` with @font-face definitions
- [ ] Update `vtt_app/templates/campaigns.html` with new classes
- [ ] Update `vtt_app/templates/play.html` with new classes
- [ ] Update `vtt_app/templates/register.html` with icon usage
- [ ] Test in Chrome, Firefox, Safari (desktop & mobile)
- [ ] Test dark mode toggle
- [ ] Test on mobile viewport (320px, 768px, 1024px, 1440px+)
- [ ] Performance audit (Lighthouse)
- [ ] Deploy and test on vtt.roll-drauf.de

---

## 🔄 IMPLEMENTATION WORKFLOW

```
1. PHASE 1 (DONE)
   ├── Create directories ✓
   ├── Generate checklists ✓
   └── Ready for downloads

2. PHASE 2 (MANUAL - Est. 45 min)
   ├── Download from Game-Icons.net (25 min)
   ├── Download from Kenney Assets (5 min)
   ├── Download from Pixabay (10 min)
   ├── Download other sources (5 min)
   └── Organize files
        └── bash organize_spellbook_assets.sh (2 min)

3. OPTIMIZATION (Est. 15 min)
   ├── Compress images
   ├── Convert fonts
   ├── Verify colors
   └── Test load times

4. PHASE 3 (CSS Integration - Est. 60 min)
   ├── Update CSS variables (15 min)
   ├── Add @font-face rules (5 min)
   ├── Update HTML templates (30 min)
   ├── Test in browser (5 min)
   └── Deploy (5 min)

TOTAL TIME: 2-3 hours
```

---

## 📚 FILES TO UPDATE

**CSS Files:**
1. `vtt_app/static/css/theme.css` - Add variables
2. `vtt_app/static/css/spellbook-theme.css` - Add asset usage
3. `vtt_app/static/css/fonts.css` - NEW file with @font-face

**Template Files:**
1. `vtt_app/templates/campaigns.html` - Update icons/classes
2. `vtt_app/templates/play.html` - Update icons/classes
3. `vtt_app/templates/register.html` - Update styling

**Asset Directories:**
1. `vtt_app/static/images/textures/` - Backgrounds
2. `vtt_app/static/images/ornaments/` - Borders, dividers
3. `vtt_app/static/images/frames/` - Book structures
4. `vtt_app/static/icons/` - All icon SVGs
5. `vtt_app/static/fonts/` - WOFF2 fonts

---

## 🎯 SUCCESS CRITERIA

✅ Phase 3 Complete when:
- [ ] All assets loaded without 404 errors
- [ ] Colors match theme (Purple #4a235a + Gold #d4af37)
- [ ] Fonts render correctly (all styles)
- [ ] Icons are colorized properly
- [ ] Responsive on mobile/tablet/desktop
- [ ] Dark mode toggle works
- [ ] Performance good (Lighthouse score 85+)
- [ ] No console errors
- [ ] Browser compatibility verified

---

**Next Step:** Begin Phase 2 - Download assets from sources listed in SPELLBOOK_ASSETS_MANUAL_DOWNLOADS.md
