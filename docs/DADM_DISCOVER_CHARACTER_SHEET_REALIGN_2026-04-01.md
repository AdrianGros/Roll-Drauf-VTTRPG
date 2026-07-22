# DAD-M Discover: Character Sheet Realign

Date: 2026-04-01
Status: completed

## Ist-Zustand

- `character-sheet` ist bereits als Focus-Route mit Spellbook-Shell vorhanden.
- Die Daten- und CRUD-Logik fuer Core, Spells, Equipment und Inventory ist intakt.
- Der groesste verbleibende Gap lag in der Huelle:
  - separater App-Header
  - Fokusroute nicht in derselben page-native Ribbon-Logik wie `dashboard`, `campaigns`, `characters`
  - Focus-Sheet wirkte noch wie Shell-Seite statt wie naechster Zoom-Schritt derselben Buchwelt

## Problem

- Unter dem neuen Book-Camera-Ziel war `character-sheet` nur teilweise realigned.
- Die Route gehoerte formal zum Spellbook-System, aber noch nicht deutlich genug zur neueren Seitenkomposition.
