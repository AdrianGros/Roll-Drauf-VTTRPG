# Discover: Spielleitung am Handy, 2026-11-15

- status: complete
- input_summary: Android/DuckDuckGo um 15 Uhr nutzbar machen, iPhone mitprüfen.
- artifacts: dieses Dokument, retention_class=durable; private Zugangsdaten nicht aufbewahren.
- risks_and_assumptions: siehe Schweregrade unten.
- next_step: Apply gemäß verlinkter technischer Spezifikation.

## Auftrag und Grenze

Heute um 15 Uhr soll die Spielleitung über Android/DuckDuckGo spielen können.
Android/Chromium und iPhone/WebKit werden geprüft; ein physisches Telefon steht
der Automatisierung nicht zur Verfügung. Bestehende Rollen- und Datenfilter sind
verbindlich. Release aus einem sauberen, committed Worktree, direkt auf die
bestehende Live-Abnahmeumgebung; keine neue Umgebung als Voraussetzung.

## Ist-Zustand und Inventar

Live-Quelle: `714f277c8546676a98db9d1cf3aba0fa1041027a`, Image
`sha256:f2ecedaf58119284a424437389a4e1b36799b65968abbd0900f88bbeb298a345`.
Isolierter Arbeitsbranch ab `aea1afaae`; andere Worktrees bleiben unberührt.

| Funktion | Befund vor Umsetzung | Evidenz |
|---|---|---|
| Kleine Displays / Dock / Dialoge | Responsive Layout, svh, Safe Area und 44px Werkzeugziele vorhanden; bisherige Layer-Prüfung nur schmales Fenster ohne Touch | play.html, play-workspace.css, test_token_layers_browser.py |
| Token bewegen | Pointer Capture und touch-action:none am Token vorhanden; kein pointercancel und keine Zuordnung von move/up zum aktiven Finger | play-ui.js, _bindMapInteractions |
| Karte bewegen | Pan-Werkzeug vorhanden; kein eigener Pinch-Zoom; Browser kann Kartengesten übernehmen; Pan ignoriert Tokenflächen | play-ui.js, _bindViewportNavigation |
| Mehrfachauswahl | Auswahlrahmen oder Shift-Klick; kein sichtbarer Touch-Modus | play-dm.js, play-token-layers-dm.js |
| Kopieren / Einfügen | Nur Ctrl/Cmd+C/V, trotz sichtbarer Auswahlleiste | play-dm.js, _bindTokenClipboard |
| Layer / Verbergen / Freigeben | Buttons vorhanden, serverseitig geschützt; Mobilbedienung mit Touch noch zu prüfen | play-token-layers-dm.js, test_token_layer_permissions.py |
| Chat / Würfel / Initiative / Journal | Bestehende sichtbare UI; konkrete Touch-Abnahme erforderlich | play.html, play-ui.js |
| Wand-/Lichtauthoring, große Karten, Hintergrundwechsel | Bestehender Funktionsumfang, keine Geräte-Leistungs-/Suspendgarantie | Keine physische Gerätemessung |

## Internetrecherche und Konsequenzen für Apply

Recherchiert am 2026-11-15. Communityberichte sind Erfahrungsberichte, keine
Kompatibilitätsgarantie und keine repräsentative Statistik.

- [Diskussion über Foundry auf Telefonen/Tablets](https://www.reddit.com/r/FoundryVTT/comments/1lj9216/foundry_on_tablets_or_mobile/): Touch-Erweiterungen und deren Grenzen sind wiederkehrende Themen.
- [Foundry, offizielle Anforderungen](https://foundryvtt.com/article/requirements/): Desktop-Abmessungen sowie Maus/Tastatur sind dort vorausgesetzt, Safari derzeit nicht unterstützt. Das ist keine Anforderung unseres VTT, erklärt aber die Communityprobleme.
- [VE Mobile, Projektbeschreibung](https://github.com/Silvestrae/ve-mobile): eigene Telefonoberfläche statt bloßer Desktop-Skalierung; iPhone/iPad best effort. Daraus folgt für uns die zu prüfende Hypothese, Tastaturfunktionen durch sichtbare Touch-Aktionen zu ergänzen.
- [MDN Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events), [touch-action](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/touch-action): Browsergesten können pointercancel auslösen; aktive Pointer und Abbruch müssen explizit behandelt werden.
- [WebKit zu Viewport-Einheiten](https://webkit.org/blog/12669/new-webkit-features-in-safari-15-5/): svh/dvh berücksichtigen unterschiedliche Browserleisten-Zustände; bestehende svh-Nutzung ist grundsätzlich sinnvoll.
- [VisualViewport](https://developer.mozilla.org/en-US/docs/Web/API/VisualViewport): Tastatur kann den sichtbaren Viewport verkleinern, ohne den Layout-Viewport entsprechend zu verkleinern. Tastatureinblendung auf Hardware bleibt separat abzunehmen.
- [DuckDuckGo Android, Primärquelle](https://github.com/duckduckgo/Android): zusätzlich zu Chromium-Emulation bleibt die konkrete Android-App ein eigener Abnahmepunkt.

## Risiken, Abhängigkeiten und offene Fragen

- **Hoch:** ungewollte Tokenmutation bei Mehrfinger-/Abbruchgesten; Apply muss Drag abbrechen und Ursprungsposition wiederherstellen.
- **Mittel:** Tastaturzwang bei Auswahl/Kopieren; sichtbare Bedienung vor 15 Uhr erforderlich.
- **Mittel:** Chromium-Emulation bildet DuckDuckGo-App, System-WebView, Android-Tastatur und Energiesparen nicht vollständig ab. WebKit auf Linux ist kein physisches iPhone.
- **Mittel:** Querformat hat wenig Höhe; Dock und Auswahl dürfen Kernwerkzeuge nicht verdecken.
- **Niedrig:** große Karten, alter WebView, komplexes Authoring und Hintergrund-Suspend bleiben gesonderte Gerätematrix.

Kein offener Produktentscheid blockiert den begrenzten Touch-Fix. Nächster
Schritt: Apply mit expliziten Gestenverträgen, Akzeptanzkriterien und Rollback.

Nachtrag aus dem Touch-Proof: `_selectToken` öffnet schon auf pointerdown das
Token-Sheet. Nach einem Drag verdeckt es nachfolgende Kartengesten; im
Pointer-Protokoll landeten diese auf `tokenWidget` statt auf der Karte.
**Mittel:** Touch muss zwischen Antippen (Details) und Ziehen (Bewegung ohne
Dialogöffnung) unterscheiden. Desktop-Klickverhalten bleibt erforderlich.
Der Folge-Proof zeigte außerdem den Kompatibilitätsklick derselben Berührung
auf dem gerade neu geöffneten `tableSheetBackdrop`; dadurch schloss sich das
Sheet sofort wieder. Die Detailöffnung muss nach diesem Klick erfolgen.
Live mit Pixel-7-Profil war eine Timer-Lösung noch nicht verlässlich. Die
Folgeprüfung nutzte deshalb dieselben Geräteprofile und Kartengrößen lokal.
WebKit lieferte nach preventDefault teilweise keinen Kompatibilitätsklick.
Apply muss sowohl fehlende als auch auf den neuen Hintergrund umgeleitete Klicks
behandeln.
