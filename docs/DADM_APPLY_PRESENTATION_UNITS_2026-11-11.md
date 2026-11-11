# Apply P4: sichere Ansichten, explizite UI-Sprache und kalibrierte Entfernungen

status: abgeschlossen, Übergabe Deploy. input_summary: Discover P4, autorisierter
Programmvertrag. artifacts: Präferenzdienst, CSS, DE/EN-Kataloge, Rastermaß,
Browser-/Rollenprüfungen; retention permanent.

## Präferenzen und Gestaltung

Gemeinsamer früher Browserdienst auf Übersicht/Kampagnen/Charakteren, Creator,
Bogen, Play, Eagle und Kartenwerkstatt; spätere P5/P6-Oberflächen verwenden denselben
Vertrag. Lokaler Schlüssel `vtt.display.v1`: schema, theme paper/night, language
de/en, unit m/ft, accent default/bronze/teal, stickyPortrait boolean. Ausschließlich
festgelegte Enumwerte; keine frei eingebbaren Styles. Vorhandene Bogenpräferenzen
werden einmal übernommen und weiterhin synchron bedient. Speicherung je Browser,
keine neue Kontoeinstellung oder Cross-device-Zusage. Präferenzdialog über die
normale Hauptnavigation. Theme/Einheit sofort; Sprachwechsel über ausdrücklich
beschriftetes Anwenden/Neuladen, damit dynamische Hauptwege konsistent starten.
Bestehender Schutz ungespeicherter Entwürfe bleibt wirksam.

Semantische Vorder-/Hintergrundtokens für beide Ansichten; bestehende feste
Komponentenfarben im vereinbarten Hauptwegumfang an diese Tokens anbinden.
Globale `AppThemeSettings` bleiben Admin-Konfiguration. Lesen der aktiven Palette
als Brandingbasis ist zulässig; Benutzerpräferenzen schreiben sie nicht. Akzent
wird nur mit sicherem Kontrast übernommen, sonst lesbare festgelegte Ableitung.
Normale Texte mindestens 4,5:1; aktiver Zustand zusätzlich Rand/Form und aria-Status.
Native Controls erhalten passendes color-scheme. Editor-Canvas und gespeicherte
Karten-/Tokenfarben werden dadurch nicht umgefärbt. Sticky-Porträt standardmäßig
aus, abschaltbar, nur bei ausreichend Platz und ohne zusätzliche Bewegung.

## Sprachvertrag

Stabile Schlüssel und explizit markierte, im Repository verfasste UI-Labels.
DE ist vollständiger Fallback, EN deckt den vereinbarten Hauptwegumfang ab.
Statische Markup-Texte/Attribute und bekannte UI-Renderer werden anhand ihrer
Quellposition annotiert; keine pauschale Übersetzung beliebiger DOM-Texte.
Vorhandener Node/Acorn-Parser der Testwerkzeuge darf die Quellinventur/-Umstellung
unterstützen; keine neue Runtime- oder Entwicklungsdependency erforderlich.
Katalog und Quelleninventar bleiben prüfbare Repo-Artefakte. Platzhalter werden
als Text eingesetzt, keine Ausführung oder Interpretation von Benutzertext.

Nutzernamen, Kampagnen-/Figuren-/Ortsnamen, Chat, Homebrew-Beschreibungen und
lizenzierte Regeltexte/-namen bleiben in ihrer jeweiligen Inhaltssprache.
Serverfehler/-Prüfreports werden nur an ihren expliziten UI-Seams anhand bekannter
Codes/Templates dargestellt; kein rekursives Umschreiben von JSON-Daten.
`lang` beschreibt die Oberfläche; fremdsprachige Regel-/Benutzerinhalte bleiben
inhaltlich unverändert. FR/ES und I04 bleiben gesondert. Prüfung umfasst
Platzhaltergleichheit, Katalogabdeckung der markierten UI, Benutzername gleich
UI-Wort, lange Texte und dieselben Bedienwege in beiden Sprachen.

## Physische Kalibrierung und Autorisierung

Additive Tabelle `campaign_map_scales`: map_id eindeutig/FK, meters_per_square
nullable Decimal(12,4), revision, updated_by und Zeit. Kein bestehendes Map-/SRD-
Feld wird umgedeutet. Nicht gesetztes Maß ist unkalibriert; bewusstes Löschen
setzt es wieder auf null. API im serverautorisierten Tischkontext:
GET/PUT `/api/play/campaigns/:c/sessions/:s/maps/:map/scale`. Schreiben nur DM/
Co-DM im aktuellen DM-Kontext, Map aus derselben Kampagne, gültige Version.
Owner als Player, fremde Session/Map und veraltete Revision werden verweigert.
Wert endlich, 0,01 bis 1.000.000 Meter/Feld, höchstens vier Nachkommastellen.

DM-Navigation: Tisch → Werkzeuge/Session-Steuerung → Kartenmaßstab. Dieser
Controller und sein Fragment werden ausschließlich in der P1-DM-Komposition
initialisiert. Player erhält nur das öffentliche numerische Maß in Map-Serialisierung
und Bootstrap. Ein sequenziertes `scene:scale_updated`-Ereignis löst denselben
gefilterten Bootstrap-Abgleich aus; keine neue schreibende Socket-Schnittstelle.

Ruler: Rasterpixel und physische Feldgröße getrennt. Mit Kalibrierung: Felder ×
Meter/Feld, Anzeige gemäß m/ft (0,3 m pro Fuß). Ohne Kalibrierung: Felder; ohne
Raster: Pixel. Die bisherige pauschale 5-ft-Annahme entfällt ausdrücklich.
Vorhandene Raster-/Freihand-Geometrie bleibt erhalten. Bogen-/Spezieswerte bleiben
kanonisch Meter; Anzeigepräferenzen verändern keine gespeicherten Spielwerte.
Karteneditor beschreibt seine Pixelgrößen weiterhin als solche; geografischer
Atlasmaßstab gehört in den P6-Datenvertrag.

## Gates und Rückweg

Medium-Risiken durch explizite Markierungen, sichere Tokens, additive Kalibrierung
und P1-Autorisierung im Entwurf behandelt. Vor Release: gezielte Sprach-/Kontrast-
und Rollen-/CAS-Tests, 320/390/1440 px, DE/EN, Pergament/Nacht, Reload/Persistenz,
kanonische Werte unverändert, normale Einstiege. Keine offenen technischen
Medium-Befunde im freizugebenden Umfang. Backup vor additiver Tabelle, bisheriges
P3-Image erhalten; altes Image ignoriert neue Kalibrierungstabellen und lokale
Präferenzen. Keine neuen Charakter- oder Kartenformate. Commit/Push, aktuelles
Image/Compose abgleichen, App-only-Deployment, technische Live-Prüfung und Monitor.
Nächster Schritt: Deploy innerhalb dieser Verträge, danach P5/P6 und gemeinsame
P7-Regressions-/Owner-Checkliste.
