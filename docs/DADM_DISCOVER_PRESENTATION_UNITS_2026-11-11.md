# Discover P4: Darstellung, UI-Sprache und Distanzen

status: abgeschlossen, immutable. Profil standard. input_summary: autorisiertes
Programm P4; P1/P2 und die laufende P3-Lieferung. artifacts: diese Inventur,
retention permanent.

Istzustand/Inventar: `static/css/theme.css` definiert kanonische Pergament-/Tinten-
Tokens plus ältere Aliase. Bogen, Spieltisch, Creator und Eagle haben zusätzlich
feste Farben und eigene Komponentenstile. `static/mapmaker/mapmaker.css` nutzt
lokale Aliase derselben VTT-Tokens, importiert die globale Theme-CSS bewusst nicht.
`models/app_theme_settings.py` und `endpoints/theme.py` verwalten eine globale
Admin-Palette; die untersuchten Hauptweg-Skripte haben keinen gemeinsamen
Benutzerpräferenz- oder UI-Sprachdienst.

`sheet-feedback.js/.css` stellt den bestehenden kompakten SRD-Bogen zusammen.
`vtt.sheet.display.v1` enthält lokale theme/unit-Präferenzen für diesen Bogen.
Pergament/Nacht und m/ft existieren dort, nicht durchgängig in allen Hauptwegen.
`vtt-main-nav.js` bildet die gemeinsame Navigation mit Kontomemo; neue Controls
müssen auch in der schmalen Karten-/Tisch-Navigation erreichbar bleiben.

Seiten sind eigenständige HTML-Dateien; es gibt kein gemeinsames `base.html`.
Die Catch-all-Routen in `vtt/__init__.py` liefern Hauptseiten per
`send_from_directory`; Eagle nutzt seine eigene Blueprint-Template-Antwort,
Mapmaker eine separate statische Modul-Anwendung. UI-Texte stehen sowohl im
Markup als auch in dynamischen JS-Renderern. Regelquellen/Charakter-/Ortsnamen
sind von authored UI-Labels zu unterscheiden. In den untersuchten Hauptwegen
wurde kein bestehender DE/EN-Schlüsselkatalog gefunden.

Distanzen: `CampaignMap.grid_size` ist Pixel pro Feld, keine physische Größe.
Es gibt `light_rules` als Beleuchtungsdaten, aber kein physisches Rastermaß.
`play-ui._formatMeasureDistance` setzt derzeit pauschal 5 ft pro Feld voraus;
die dortige Notiz bezeichnet dies ausdrücklich als früheren Platzhalter.
SRD-Bewegung wird kanonisch als Meter berechnet; `species_profiles.py` und der
kompakte Bogen verwenden bereits D&D-konform 0,3 m pro Fuß. Der Mapmaker speichert
Pixelgeometrie und prüft Dokumente über `mapmaker_document.normalize_document`.

Abhängigkeiten: vorhandene browsernative Speicherung, CSS/DOM, bestehende
Kontext-/Ressourcenprüfung aus P1 und Map-/Bogen-Serialisierung. Keine neue
Laufzeitabhängigkeit durch diesen Befund festgelegt.

Risiken/Annahmen: medium – bisherige feste Farbpaarungen können bei globaler
Nachtansicht unlesbar werden; reale Vorder-/Hintergrundpaare prüfen. medium –
naive Textübersetzung könnte Nutzernamen, Homebrew oder Regeltexte verändern;
Übersetzungsgrenze muss explizit bleiben. medium – die 5-ft-Annahme erfindet für
unkalibrierte Karten ein Maß; physische Kalibrierung und Pixel müssen getrennt
sein. medium – DM-Kalibrierung darf einem Owner in Player-Kontext nicht erlaubt
sein. low – Präferenzen dürfen gespeicherte Spielwerte nicht umschreiben.
I04 (Regelbuchübersetzung/Rechte) bleibt offen und ist unabhängig von UI-DE/EN.

Recherche: [WCAG 2.2 Kontrast](https://www.w3.org/TR/WCAG22/#contrast-minimum)
und [W3C-Berechnung/Erklärung](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
geben die 4,5:1-Grenze für normale Texte an. [CSS color-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/color-scheme)
beschreibt die passende Darstellung nativer Controls; [HTML lang](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Language)
unterscheidet Dokument-/Element-Sprache von Inhaltsmetadaten.

Offene Fragen: zusätzliche FR/ES- oder Regeltextübersetzungen nicht beauftragt;
kein Blocker für das vereinbarte UI-DE/EN. Nächster Schritt: Apply definiert
Präferenz-/Katalogvertrag, Farbgrenze, kalibrierte Tischdistanz, Rollout und
repräsentative Sprach-/Viewport-/Rollenprüfungen vor jeglicher P4-Implementierung.
