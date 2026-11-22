# Apply: Playtable-Fenster frei positionieren

22.11.2026 · autorisierter Fehlerbericht: Fenster scrollen untereinander und lassen sich nicht frei platzieren. Enger Hotfix vor dem größeren Review-Paket.

Die Live-Basis ist `6a2fcedce` / Image `sha256:3de96a3ce53034adc559e5bca92b27d6adcb571848b75022d0bf3735493b358d`; `49e8b9944` ergänzt nur Dokumentation. Der Fenstercontroller hängt seine Fenster direkt an `body`. `book-shell.css` setzt dort `body.book-shell-app > * {position:relative}`, was die schwächere `.play-window {position:fixed}`-Regel überstimmt. Dadurch werden Fenster Teil des Dokumentflusses, obwohl der Dragcontroller Bildschirmkoordinaten schreibt.

Deploy-Grenze: ausschließlich die eigenen Fenster am Body explizit als feste, transformfreie Bildschirmflächen positionieren; Header schrumpft nicht, Body ist alleiniger flexibler Scrollbereich. Keine Änderung an Tischrechten, Fensterspeicherung, Inhaltsinstanzen oder Kartenkoordinaten. Bestehende Positionen und Reset bleiben erhalten.

Abnahme: Browser reproduziert vor Fix die falsche berechnete Position. Danach zwei gleichzeitig offene Fenster in DM/Player und Chromium/Firefox; echte Maus-/Touchbewegung verändert Position um die beabsichtigte Strecke, andere Fenster bleiben stehen. Scrollen verändert nur den eigenen Fensterinhalt, nicht Dokument oder Nachbarfenster. Close/Reload stellt Position wieder her. Mobil bleiben Header und Schließen erreichbar. Source/Image und app-only Rollback werden bei Lieferung protokolliert.
