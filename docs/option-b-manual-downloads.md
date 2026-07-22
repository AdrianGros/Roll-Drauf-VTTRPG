# Option B: Manual Downloads - Step by Step Guide

**Auto-Completed Items:**
- ✅ Google Fonts (Cinzel, Bad Script, Pirata One) - DONE
- ✅ fonts.css (CSS @font-face definitions) - DONE
- ✅ Directory structure - DONE

**Pending Manual Downloads:**
- ⏳ Kenney Assets Bundle
- ⏳ Game-Icons.net (30-50+ icons)
- ⏳ Pixabay Galaxy Backgrounds

---

## 1️⃣ KENNEY ASSETS BUNDLE (10-15 minutes)

### Where to Download
- **URL:** https://kenney.nl/assets
- **File:** Fantasy Game Assets 8.0 (or All-in-1 Bundle)
- **Format:** ZIP
- **Size:** ~50-100 MB
- **License:** CC0 (no attribution needed)

### Step-by-Step Download

1. **Visit website:**
   - Go to https://kenney.nl/assets
   - Scroll down to "Fantasy Game Assets 8.0"

2. **Download:**
   - Click the download button (usually green "Download" or cloud icon)
   - Save file

3. **Extract:**
   ```bash
   unzip ~/Downloads/fantasy-game-assets-8.0.zip \
     -d vtt_app/static/downloads/kenney-assets/
   ```

4. **Organize (automated):**
   ```bash
   bash organize_kenney_assets.sh
   ```

### What You Get
- 130+ Fantasy UI borders and frames
- 60+ Fantasy icons and sprites
- Game fonts (already have better ones from Google Fonts)

### Files Organization (Auto-Done)
```
After organize_kenney_assets.sh:
vtt_app/static/
├── images/ornaments/      ← Borders, UI elements
├── icons/kenney-*.png     ← UI icons (backup set)
└── images/                ← Fantasy sprites
```

---

## 2️⃣ GAME-ICONS.NET ICONS (20-30 minutes)

### Where to Download
- **URL:** https://game-icons.net/
- **Format:** SVG (vector, scalable)
- **Quantity Target:** 32+ icons
- **License:** CC-BY 3.0 (give credit to game-icons.net)

### How to Download Icons

1. **Visit:** https://game-icons.net/

2. **For EACH icon below:**
   - Type icon name in search box
   - Click the icon when found
   - Click "Download" button
   - **Select SVG format**
   - Save to: `vtt_app/static/icons/`
   - **Rename file to match pattern: `icon-{category}-{name}.svg`**

### Priority Icons to Download

#### 📚 Campaign/DM (4 icons)
```
Search → Download → Save as
"book" → download → icon-campaign-book.svg
"scroll" → download → icon-campaign-scroll.svg
"library" → download → icon-campaign-library.svg
"scroll quill" → download → icon-campaign-quill.svg
```

#### ▶️ Session/Play (5 icons)
```
"play" → icon-session-play.svg
"pause" → icon-session-pause.svg
"resume" → icon-session-resume.svg
"hourglass" → icon-session-time.svg
"crowd" → icon-session-players.svg
```

#### ⚔️ Combat (5 icons)
```
"crossed swords" → icon-combat-swords.svg
"shield" → icon-combat-shield.svg
"dagger" → icon-combat-dagger.svg
"poison" → icon-combat-poison.svg
"fire" → icon-combat-fire.svg
```

#### ✨ Spells/Magic (15 icons)
```
"sparkles" → icon-spell-sparkles.svg
"wand" → icon-spell-wand.svg
"magic swirl" → icon-spell-swirl.svg
"spell book" → icon-spell-book.svg
"magic palm" → icon-spell-hand.svg
"gem" → icon-spell-gem-1.svg
"gem" (2nd variant) → icon-spell-gem-2.svg
"star" → icon-spell-star-1.svg
"star" (variant) → icon-spell-star-2.svg
"feather" → icon-spell-feather.svg
"sparkle glow" → icon-spell-glow.svg
"magic wand 2" → icon-spell-wand-2.svg
"crystal" → icon-spell-crystal.svg
"rune stone" → icon-spell-rune.svg
"arcane" → icon-spell-arcane.svg
```

#### 💰 Inventory/Items (8 icons)
```
"backpack" → icon-inventory-backpack.svg
"treasure chest" → icon-inventory-chest.svg
"potion" → icon-inventory-potion.svg
"coin" → icon-inventory-coin.svg
"ring" → icon-inventory-ring.svg
"scroll" → icon-inventory-scroll.svg
"key" → icon-inventory-key.svg
"sack" → icon-inventory-sack.svg
```

#### 🏆 Status/Badges (5 icons)
```
"eye" → icon-status-visible.svg
"eye hiding" → icon-status-hidden.svg
"check mark" → icon-status-active.svg
"crown" → icon-status-dm.svg
"warning" → icon-status-alert.svg
```

### Bulk Download Tip

If Game-Icons.net offers bulk download (check their account features):
1. Create free account on game-icons.net
2. Add all icons to collection
3. Download bulk ZIP (if available)
4. Extract to `vtt_app/static/icons/`

---

## 3️⃣ PIXABAY GALAXY BACKGROUNDS (10-15 minutes)

### Where to Download
- **URL:** https://pixabay.com/
- **Search Terms:** See below
- **Format:** PNG (important! not JPG)
- **Resolution:** Minimum 2K (2560x1440)
- **Quantity:** 5-7 images
- **License:** Free for commercial use, no attribution needed

### Step-by-Step Download

1. **Visit:** https://pixabay.com/

2. **Search with these terms (one at a time):**
   - "galaxy background 4k"
   - "nebula space"
   - "cosmic purple"
   - "space galaxy"
   - "nebula purple"

3. **For EACH search:**
   - Look for images with purple/blue tones
   - Check resolution (aim for 2K+)
   - Click image to open
   - Click "Download" button
   - **Select PNG format** (not JPG)
   - Save to: `vtt_app/static/images/textures/`

4. **Rename files:**
   ```
   bg-galaxy-dark.png
   bg-galaxy-purple.png
   bg-galaxy-cosmic.png
   bg-nebula-pink.png
   bg-nebula-blue.png
   bg-space-purple.png
   bg-space-cosmic.png
   ```

### Tips for Good Results

- **Color:** Look for purple, blue, pink nebulas
- **Style:** Prefer realistic/photographic over cartoon
- **Quality:** Download highest resolution available
- **Variety:** Get mix of different compositions
- **Orientation:** Portrait (vertical) or Landscape (horizontal)

### Example Search Results
Best to download these types:
- Spiral galaxy with purple haze
- Nebula cloud formations
- Cosmic space with stars and colors
- Aurora/northern lights style
- Colorful cosmic backgrounds

---

## ✅ VERIFICATION CHECKLIST

After completing all manual downloads, verify:

```bash
# Check structure
find vtt_app/static -type f | wc -l

# Should have approximately:
# - 4 WOFF2 fonts ✓ (already done)
# - 1 fonts.css ✓ (already done)
# - 30-50 Game-Icons SVGs (should download)
# - 60+ Kenney PNGs (should download & organize)
# - 5-7 Galaxy background PNGs (should download)
```

### Verify each directory:

```bash
# Fonts (should have 4 files)
ls -l vtt_app/static/fonts/*.woff2

# Icons (should have 35+ files)
ls -l vtt_app/static/icons/icon-*.svg | wc -l

# Textures/Backgrounds (should have 5-7)
ls -l vtt_app/static/images/textures/bg-galaxy-*.png | wc -l

# Ornaments (from Kenney, should have 10+ files)
ls -l vtt_app/static/images/ornaments/*.png | wc -l
```

---

## 📋 DOWNLOAD TRACKER

Use this checklist to track progress:

### Kenney Assets
- [ ] Download ZIP from kenney.nl/assets
- [ ] Extract to: `vtt_app/static/downloads/kenney-assets/`
- [ ] Run: `bash organize_kenney_assets.sh`
- [ ] Verify: `ls vtt_app/static/images/ornaments/` has files

### Game-Icons
- [ ] Campaign icons (4) → Save to: `vtt_app/static/icons/`
- [ ] Session icons (5) → Save to: `vtt_app/static/icons/`
- [ ] Combat icons (5) → Save to: `vtt_app/static/icons/`
- [ ] Spell icons (15) → Save to: `vtt_app/static/icons/`
- [ ] Inventory icons (8) → Save to: `vtt_app/static/icons/`
- [ ] Status icons (5) → Save to: `vtt_app/static/icons/`
- [ ] Total: 32+ icon SVGs downloaded

### Pixabay Backgrounds
- [ ] Search "galaxy background 4k" → Download 2 images
- [ ] Search "nebula space" → Download 2 images
- [ ] Search "cosmic purple" → Download 1-2 images
- [ ] Search "space galaxy" → Download 1-2 images
- [ ] Total: 5-7 PNG images to: `vtt_app/static/images/textures/`

### Verification
- [ ] All files in correct directories
- [ ] All SVGs named: `icon-{category}-{name}.svg`
- [ ] All backgrounds named: `bg-galaxy-*.png`
- [ ] Total files: ~100+

---

## 🚀 AFTER MANUAL DOWNLOADS COMPLETE

Once you've downloaded all assets:

1. **Organize Kenney Assets:**
   ```bash
   bash organize_kenney_assets.sh
   ```

2. **Verify Structure:**
   ```bash
   find vtt_app/static -type f | wc -l
   ```

3. **Next Phase - CSS Integration:**
   - Generate CSS variables
   - Update HTML templates
   - Deploy to vtt.roll-drauf.de

---

## ⏱️ TIME ESTIMATES

- Kenney download & extract: 5-10 min
- Game-Icons (32 icons): 20-30 min
- Pixabay (5-7 backgrounds): 5-10 min
- **Total: 30-50 minutes**

---

## 📞 TROUBLESHOOTING

### Game-Icons.net not loading?
- Try different browser (Chrome, Firefox, Edge)
- Clear browser cache
- Disable browser extensions

### Pixabay file not downloading?
- Try right-click → "Save image as"
- Check download folder for file
- Verify PNG format in download dialog

### File permissions?
```bash
chmod 644 vtt_app/static/icons/*.svg
chmod 644 vtt_app/static/images/textures/*.png
```

### Need more icons or textures?
See: `SPELLBOOK_ASSETS_DOWNLOAD_LIST.md` for additional sources

---

**Status:** Ready for manual downloads! ⏳

**Next Communication:** Share when downloads are complete, or request help if stuck!
