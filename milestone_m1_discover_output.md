# Discover Output Template

Use this template to record the result of a Discover phase. Fill in all sections before
closing the phase. This artifact is immutable once the phase is closed.

For the standard phase output structure and retention rules, see `framework/core/deliverables.md`.

---

```
artifact: discover-output
milestone: M1
phase: DISCOVER
status: complete
date: 2026-03-26
```

---

## Input Summary

- User request: Analyze features of Roll20 and Foundry VTT, their importance for a VTT, implementation complexity, and programming language recommendation (preference: Python).
- External sources: General knowledge of VTT platforms (Roll20, Foundry VTT).
- Additional feedback: Interview with DM using Foundry Overlay Mod (Matt). Key pain points and feature wishes.
- Constraints: Project is for D&D sessions on Discord, aiming to replace Roll20/Foundry.

---

## Current-State Summary

- Workspace: Python project directory exists, but no code yet.
- DAD-M Framework: Cloned and available for structure.
- No existing VTT code or assets.

---

## Inventory

| # | Name | Description | Location | Status |
|---|---|---|---|---|
| I1 | Roll20 Features | List of key features from Roll20 VTT | External (roll20.net) | present (based on knowledge) |
| I2 | Foundry VTT Features | List of key features from Foundry VTT | External (foundryvtt.com) | present (based on knowledge) |
| I3 | Python Environment | Python setup for development | Workspace | unclear (needs check) |

---

## Dependencies

- Python 3.x: For backend logic (present, assuming standard install).
- Web technologies: HTML/JS for frontend (missing, needed for full VTT).
- Libraries: Flask/Django for web server (missing).

---

## Analysis of VTT Features

### Roll20 Key Features
- Character Sheets: Integrated sheets for D&D, etc.
- Dice Rolling: With macros and automation.
- Map Tools: Dynamic lighting, fog of war.
- Token Management: Drag-and-drop tokens.
- Audio/Video: Integration with voice chat.
- Marketplace: Assets and modules.
- API: For custom integrations.

### Foundry VTT Key Features
- Self-hosted: Runs on user's server.
- Modular System: Add-ons for customization.
- Advanced Mapping: Layers, walls, hex grids.
- Journal System: Notes and lore.
- Audio Playlists: Background music.
- Combat Tracker: Initiative and automation.
- Macro System: Custom scripts.
- API: For modules and extensions.

### Importance for VTT
- Essential: Map display, token placement, dice rolling, text chat (core gameplay).
- Important: Character management, initiative tracking (D&D specific).
- Nice-to-have: Audio/video, dynamic effects, marketplace (enhancements for immersion).

### Implementation Complexity
- Low: Dice rolling (simple random functions in Python).
- Medium: Map and token (canvas rendering in JS).
- High: Dynamic lighting (WebGL shaders), multi-user sync (WebSockets), audio/video (WebRTC).

### Programming Language Recommendation
- Python: Good for prototyping and backend (your preference). Use Flask for server.
- Better alternatives: For full VTT, JavaScript/Node.js for real-time features, or C# with Unity for 3D.
- Recommendation: Stick with Python for MVP, combine with JS for frontend. Complexity is manageable with web stack.

---

## Additional Feedback from DM Interview

- **Cinematik/Animationen**: Foundry Overlay wirkt statisch – verbessere flüssige Übergänge und Effekte.
- **Map Tools**: Integrierter Map Maker, Map Editor, Dungeon Generator (ähnlich Asgard Fantasy Map Generator). Hex-generierte Karten.
- **Navigation**: Zurückwischen (Swipe-Gesten) für intuitive Bedienung.
- **UI/UX**: All-in-One-Erlebnis, nicht viele Einzelseiten – zentrale Übersicht.
- **Charaktersheets**: Übersichtlich gestalten (inspiriert von Foundry's Beidesfreundlichkeit, besser als Roll20's Überladenheit).
- **Integrationen**: D&D Beyond Overlay schön, aber technisch hakelig – smooth integrieren.
- **Effekte**: Editor für Map-Effekte, Dynamic Lighting, schönere Bildeffekte und Szenematik. Mehr Bilderbezug (Assets).
- **Lokalisierung**: Übersetzung unbedingt einbauen.
- **DM-Erlebnis**: DM soll sich wie in einem Strategiespiel fühlen – Minigame zum Steuern von Nationen auf Weltkarte für Session-Pacing.
- **Einfachheit**: Einstieg für DM so einfach wie möglich mit vorhandenem Standard-Setting.
- **Externe APIs**: Asgard Leute nach API fragen für Map-Generator-Integration.

---

## Open Questions
- Specific D&D features needed (e.g., spell tracking, HP management)?
- Target platform: Web app or desktop?
- Team size: Solo or with others?
- Asgard API availability for map generator integration?
- Standard D&D setting details for easy DM onboarding?

---

## Risks
- High complexity for real-time features may require web expertise.
- Localization (translations) adds overhead.
- Dependency on external APIs (e.g., Asgard) for map generation.
- DM Minigame feature may expand scope significantly.
- Scope creep: Start with core features.

---

## Next Steps
- Proceed to Apply phase: Design tech stack and architecture.</content>
<parameter name="filePath">c:\Users\adria\Desktop\DAD-M\02_Projects\Programmieren\Python\VTT\milestone_m1_discover_output.md