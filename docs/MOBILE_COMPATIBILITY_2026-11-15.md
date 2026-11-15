# Handy-Spielbetrieb: Android/DuckDuckGo und iPhone, 15.11.2026

Zielgerät des Besitzers: **Android mit DuckDuckGo**. Chromium-Touch emuliert die
relevante Eingabeklasse; DuckDuckGo verwendet Android WebView ([Primärquelle](https://duckduckgo.com/duckduckgo-help-pages/privacy/web-tracking-protections)).
Die konkrete App, System-WebView-Version und Gerätehardware sind damit nicht
abgenommen. WebKit mit iPhone-Profil ist ebenfalls ein Engine-Test, kein echtes iPhone.

## Bedienung der Session

1. Auf `https://vtt.roll-drauf.de` anmelden → Kampagne → Sitzung **als DM öffnen**.
2. **Bewegen**: ein Finger verschiebt die Karte, auch auf Tokenflächen. Zwei Finger
   auf der Karte verschieben/zoomen; `+`, `−` und `FIT` bleiben Alternativen.
3. **Wählen**: Token ziehen zum Bewegen; Token antippen für dessen Details.
   Ziehen öffnet kein verdeckendes Detailfenster mehr.
4. **Layers** unten → Player- oder Dungeon-Master-Layer. Neue Tokens entstehen im
   aktiven Layer. **Token** öffnet zunächst das Token-Menü; mit `×` schließen,
   dann eine freie Kartenposition antippen und das Erstellen bestätigen.
5. **Layers → Mehrfachauswahl** aktivieren, Menü schließen und Tokens antippen.
   Die Auswahlleiste zeigt gruppierte Anzahl und **Kopieren**, **Einfügen**,
   **Spielern zeigen**, **Vor Spielern verbergen**, **Auswahl aufheben**.
   Mehrfachauswahl wieder ausschalten, um einzelne Tokens zu ziehen.
6. **Einfügen** setzt die Kopien in die Kartenmitte des aktiven Layers. Der Button
   bleibt auch nach Aufheben der Auswahl unter **Layers** erreichbar.
7. **Initiative** für Kampfstart/Zugwechsel/Kampfende; **Chat** zum Schreiben;
   **Journal → Tools** für Würfel. Seitlich scrollbare Werkzeugleiste bei Bedarf
   mit dem Finger verschieben. Hoch- und Querformat sind vorgesehen.

## Funktionsmatrix und Grenzen

Die endgültigen Prüfergebnisse stehen im Deploy/Monitor-Nachweis und in
`proofs/mobile-2026-11-15/live.json`; diese Tabelle beschreibt den Prüfungsumfang.

| Funktion | Vorher | Prüfung / Abnahmestatus |
|---|---|---|
| Passwort-Login, Kampagnenhub, autorisierter DM-Einstieg | Vorhanden | Beide Engines gegen Live über sichtbare Navigation vorgesehen; Discord-OAuth nicht separat abgenommen |
| Token tippen / ziehen | Details öffneten schon bei Drag-Beginn | Touch-Drag und Tap getrennt; Chromium mit nativer Browser-Toucheingabe und Serverzustand |
| Pan auf Tokenfläche | Start wurde als Tokenbewegung behandelt | Pan darf Tokenversion/-position nicht ändern |
| Pinch-Zoom / Zweifinger-Pan | Kein eigener Karten-Pinch | Native Chromium-Multitouch-Prüfung; iOS-Pinch physisch noch offen |
| Abgebrochene Gesten | Kein pointercancel-Cleanup | Abbruch und zweiter Finger dürfen keinen Drag speichern |
| Mehrfachauswahl | Auswahlrahmen oder Shift erforderlich | Sichtbarer Touch-Modus, beide Engines |
| Kopieren / Einfügen | Nur Tastatur | Sichtbare Buttons, beide Engines; kein OS-Clipboard nötig |
| Layer, versteckte Platzierung, Freigeben/Verbergen | Vorhanden, Touch nicht nachgewiesen | Beide Engines, paralleler Player, Bootstrap/Socket-Datenschutz und Reload |
| Initiative | Vorhanden | Kampfstart, nächster Zug und Kampfende per Touch im Querformat |
| Chat / Würfel / Journal | Vorhanden | Nachricht senden, d20 würfeln, Journal öffnen per Touch |
| Tokens umbenennen, HP, Zustände, Charakterbogen | Sichtbare Token-/Bogen-Steuerung vorhanden | Nicht vollständig auf echter Handyhardware abgenommen |
| Messen | Long-Press und sichtbares Werkzeug vorhanden | Abbruch auf Mehrfingerbedienung ergänzt; vollständiger mobiler Messkatalog offen |
| Kartenwechsel / Upload / Assetbibliothek | Sichtbare Menüs und Datei-Inputs vorhanden | Android-Dateiauswahl / große Bilder nicht vollständig geprüft |
| Wände / Lichter / Fog-Authoring | Bestehende Klick- und Bearbeitungswerkzeuge | Präzises Touch-Authoring nicht vollständig abgenommen; keine neue Authoringoberfläche |
| Beyond20 / externe Erweiterungen | Desktop-Integrationspfad vorhanden | Für DuckDuckGo-Handy nicht als nutzbar nachgewiesen; interne Würfel geprüft |
| Bildschirmtastatur / Screenlock / Hintergrund / schwaches Netz | Browser-/Systemverhalten abhängig | Echte Geräteabnahme offen; kein Offlinebetrieb zugesagt |

## Recherche → technische Entscheidungen

[Communityberichte](https://www.reddit.com/r/FoundryVTT/comments/1lj9216/foundry_on_tablets_or_mobile/)
beschreiben Touch-Erweiterungen als zentrale Voraussetzung. Das ist keine
repräsentative Statistik. [Foundry selbst](https://foundryvtt.com/article/requirements/)
setzt Desktop-Abmessungen und Maus/Tastatur voraus; [VE Mobile](https://github.com/Silvestrae/ve-mobile)
verfolgt eine eigene Telefonoberfläche. Unsere daraus abgeleitete Entscheidung:
Kernaktionen sichtbar machen und Gesten ausdrücklich behandeln, statt lediglich
das Desktopfenster schmaler darzustellen.

[Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events)
und [touch-action](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/touch-action)
begründen Pointer-ID-Zuordnung, Abbruchbehandlung und begrenzte Karten-Gestenfläche.
Aus [W3C Target Size](https://www.w3.org/WAI/WCAG21/Understanding/target-size)
übernehmen wir 44px als Ziel für die neuen Auswahlbuttons; das ist kein Nachweis
vollständiger WCAG-Konformität. Bestehende svh/dvh-/Safe-Area-Behandlung bleibt;
[VisualViewport](https://developer.mozilla.org/en-US/docs/Web/API/VisualViewport)
erklärt die gesondert zu prüfende Bildschirmtastatur.

## Gerätekatalog für die nächste Abnahme

| ID | Gerät / Ablauf | Status |
|---|---|---|
| M-H01 | Besitzer: Android/DuckDuckGo, Login → DM → Gesten → Layerfreigabe | NOT_RUN auf Hardware |
| M-H02 | Android/DuckDuckGo: Chat und Tokenname mit Bildschirmtastatur, Senden/Schließen erreichbar | NOT_RUN auf Hardware |
| M-H03 | iPhone/Safari: Hoch-/Querformat, Pinch, Safe Area, Tastatur | NOT_RUN auf Hardware |
| M-H04 | Beide: Sperren/Entsperren, Appwechsel, zwei Tabs, Reconnect ohne Rollenwechsel | NOT_RUN auf Hardware |
| M-H05 | Beide: reale Sessionkarte mit üblicher Tokenanzahl, Netzwechsel/WLAN→Mobilfunk | NOT_RUN auf Hardware |
| M-H06 | Beide: Bogenaktionen, HP/Zustände, Messen, Kartenwechsel, Datei-Upload | NOT_RUN vollständig |
| M-H07 | Beide: Wand-/Licht-/Fog-Authoring und sichtbare Alternative zu Rechtsklick/Escape | NOT_RUN vollständig |

Technische Details: [Discover](DADM_DISCOVER_MOBILE_2026-11-15.md),
[Apply](DADM_APPLY_MOBILE_2026-11-15.md). Automatisierte Ergebnisse und echte
Benutzerabnahme werden getrennt erfasst.
