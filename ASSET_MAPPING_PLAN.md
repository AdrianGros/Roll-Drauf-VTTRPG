# Asset Mapping & Planning: roll drauf vtt

Date: 2026-03-26
Status: Discovery Complete - Ready for Download

## FREE ASSET SOURCES (Verified)

### PRIMARY SOURCES

**itch.io** https://itch.io/game-assets/free
- 500+ free assets tagged: tokens, VTT, spell-icons
- License: CC-BY, CC0 (check per pack)
- Best for: Character tokens, skill icons, UI elements

**OpenGameArt.org** https://opengameart.org/
- Community art repository - ALL Creative Commons
- Painterly Spell Icons (256x256, multiple power levels)
- UI Elements: Buttons, panels, backgrounds
- License: All CC-BY or CC0

**Forgotten Adventures** https://www.forgotten-adventures.net/
- D&D/VTT focused: Creatures, Heroes, NPCs
- 500+ free tier tokens available
- Maps and terrain assets
- License: Free tier included

**Dead Hawk Publishing**
- Free token packs (hand-drawn OSR style)
- "Lost Citadel" pack: 19 characters
- Format: 400x400 PNG, light/dark variants
- License: Free to use

**2 Minute Tabletop** https://www.2minutetabletop.com/
- Free D&D battle maps
- VTT-ready assets
- License: Free for personal use

---

## ASSET CATEGORIES & SOURCES

### A. CHARACTER TOKENS (PRIORITY 1)
Sources: Forgotten Adventures, Dead Hawk, itch.io
Format: 400x400 PNG with transparency
What: Human, Elf, Dwarf, Halfling, Tiefling
      NPCs (merchants, guards), Monsters
      All genders, varied appearances

### B. SPELL & ABILITY ICONS (PRIORITY 2)
Sources: OpenGameArt (Painterly), PROJECT MUTANT (itch.io)
Format: 64x64 to 256x256 PNG
What: Fireball, Shield, Heal, Buffs, Debuffs
      Attack, Defend, Dodge, Parry icons

### C. UI ELEMENTS (PRIORITY 3)
Sources: OpenGameArt, Kenney Assets (itch.io)
Format: PNG scalable
What: Buttons, panels, health bars, tabs
      Chat backgrounds, inventory grids

### D. STATUS EFFECTS (PRIORITY 4)
Sources: Game-Icons.net, OpenGameArt
Format: 48x48 PNG
What: Poisoned, Charmed, Blinded, Burned, Frozen
      Buff/debuff badges for character panel

### E. FONTS (PRIORITY 3)
Sources: Google Fonts (free CDN)
Suggestions:
  - Cinzel (fantasy headers)
  - Merriweather (readable body)
  - Roboto Mono (code/logs)
License: OFL (free to use, embed)

---

## FOLDER STRUCTURE

vtt_app/static/assets/
  tokens/
    characters/
      human/ (male, female variants)
      elf/
      dwarf/
      halfling/
      tiefling/
    npcs/ (merchants, guards, mages)
    monsters/ (goblins, orcs, undead)
  
  icons/
    spells/ (fire, ice, lightning, healing)
    abilities/ (attack, defend, dodge)
    status_effects/ (poison, charm, blind)
  
  ui/
    buttons/
    panels/
    bars/
  
  fonts/
    Cinzel-Bold.woff2
    Merriweather-Regular.woff2
  
  ATTRIBUTION.md (all sources & licenses)

---

## QUICK START CHECKLIST

Phase 0 (THIS WEEK):

[ ] Download sources:
    [ ] Forgotten Adventures free tier (https://www.forgotten-adventures.net/)
    [ ] Dead Hawk Publishing token pack
    [ ] OpenGameArt Painterly Spells
    [ ] PROJECT MUTANT 100 Fantasy Icons (itch.io)
    [ ] Kenney UI Pack (if available)

[ ] Organize into folder structure

[ ] Create ATTRIBUTION.md with all sources:
    - Pack name
    - Source URL
    - License type
    - Author name
    - Date downloaded

[ ] Test rendering:
    - Add sample token to character-sheet.html
    - Display icon in hotbar mock
    - Verify CSS scaling works

---

## IMPLEMENTATION ROADMAP

PHASE 0 (NOW): Asset Discovery & Download
  Goal: High-quality free assets organized

PHASE 1 (M5): Token Integration
  - Character list shows tokens
  - Character editor preview
  - Game UI uses tokens

PHASE 2 (M5-6): Icon Integration
  - Hotbar with spell icons
  - Status effect badges
  - Ability buttons

PHASE 3 (M6+): Full UI Styling
  - Custom panels with assets
  - Gradient bars with icons
  - Cohesive fantasy aesthetic

PHASE 4 (M7+): Advanced
  - Battle maps with tiles
  - VFX effects
  - Token creator

---

## QUALITY CRITERIA

Before using any asset:
- License verified (CC-BY, CC0, or explicitly free)
- PNG format with transparency (for tokens/icons)
- Size 256x256 or larger (scale down in CSS)
- Fantasy art style (cohesive with theme)
- Attribution in ATTRIBUTION.md
- No watermarks or bloat

---

## PERFORMANCE CONSIDERATIONS

Token loading:
- 400x400 resized to 100x100 in CSS (saves bandwidth)
- Cache tokens in JS after first load
- Lazy-load non-critical assets

Icons:
- Create sprite sheets (all spells in one image)
- Use CSS background-position for individual icons
- Reduce HTTP requests significantly

UI:
- Prefer CSS gradients + borders over images
- Use fonts from Google Fonts CDN
- Compress PNG to WebP with fallback

---

READY TO DOWNLOAD ASSETS!

Next: Phase 1 begins with real graphics instead of placeholders.
