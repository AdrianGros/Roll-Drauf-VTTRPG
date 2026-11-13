# B06 – Pinsel, Radierer und nachvollziehbares Sichern

Status: Apply abgeschlossen. Input N08–N11/N18/S18; N11 bleibt bis zur konkreten Reglerangabe offen.
Retention dauerhaft. Keine neue Bibliothek, kein Import weiterer Assets, kein neuer Anmeldetimer.

## Fakten / Grenze

Die vorhandene GIMP-artige Engine sammelt Masken und verrechnet Deckkraft einmal je Strich.
Pinsel/Radierer teilen derzeit ihre Werte. Raster haben bereits eine Küsten-/Brandungsoption.
Datei und IndexedDB speichern die gerasterten Pixel; Herkunft einzelner Bildpinsel ist daraus
nicht mehr ableitbar. Credits nehmen bisher benutzte Vektor-/Kachelpakete sowie alle Fotomaterialien
auf. Eigene Bibliothek, kontobezogene Entwürfe und Atlas-Lease sind verschiedene Speicherpfade.
Es gibt keinen belegten Editor-Inaktivitätslogout; die bestehende Authentifizierungsgrenze bleibt.

## Zwei Lieferungen / Attribution

B06a ergänzt zunächst konservative Raster-Credits: Sobald Rasterpixel im Dokument vorkommen,
werden alle freigegebenen lokalen Katalogquellen in CREDITS.txt/PNG-Metadaten aufgenommen.
Das ist eine Quellensammlung, keine Behauptung, jedes Paket werde sichtbar verwendet. Die vorhandenen
Manifesttexte, Lizenzangaben, Links und Ausgabewege bleiben maßgeblich. So gehen bei späterem
Bildpinseln keine Quellen verloren. Keine nachträgliche Pixelklassifikation oder beliebigen URLs.
Diese kleine Kompatibilitätslieferung wird separat committed, getestet und aktiviert, bevor der
Bildpinsel erscheint; sie ist damit das rückkehrfähige vorherige Image für B06b.

B06b setzt auf diesem Stand auf. Ein Bibliotheks-/Dateidokument mit Raster behält auch nach einem
Rollback auf B06a seine vollständigen Quellenangaben. Bestehende Projekte erhalten keine Datenbank-
oder Dokumentmigration. Zusätzliche optionale Küsteneffekte werden in JS/Python gleich validiert.

## Werkzeuge / Datenvertrag

Pinselspitzen Rund, Quadrat und Raute. Runde alte Striche behalten ihre Berechnung. Neue Spitzen
nutzen dieselben Größen-, Weichheits-, Druck- und Verlaufslimits. Ein Bildpinsel verwendet ein
explizit gewähltes bekanntes Symbol oder einen vorhandenen Bildausschnitt/Kachel. Erst dann wird
seine lokale Quelle geladen und eine kleine Spitze erzeugt; keine Vorberechnung des gesamten
Katalogs. Farbige Spitzen sammeln ihre Dabs in einem temporären Strichcanvas und werden einmal
mit Strichdeckkraft über das unveränderte Ausgangsbild verrechnet. Originalfarben bleiben erhalten;
Materialfarbregler sind bei Bildpinseln entsprechend erklärt/deaktiviert.

Materialpinsel bieten eigene Farbe und Texturanteil, ohne vorhandene Materialdefinitionen zu ändern.
Standard bleibt das originale Material mit 100 % Textur. Manuelle Farbe erhält bei Texturanteil
Struktur/Helligkeit des Materials. Alle Einstellungen werden pro Geste eingefroren. Radierer besitzt
eigene Werte: 100 % Deckkraft, 0 % Weichheit, positive Pixelgröße; Wechsel erhält jeweils die zuletzt
gewählten Werte. Die vorhandene Auswahl aktive Ebene/sichtbare Ebenen und deren Undo-Grenzen bleiben.
Keine Umdeutung von „Skalieren 0 %“ in einen wirkungslosen Pinsel mit Größe null.

Die bestehende Küstenlinie der aktiven Malebene wird direkt beim Pinsel erreichbar. Optional
`effects.coastColor` als #RRGGBB und `effects.coastWidth` (0–16 px), fehlend bisheriger Standard.
Beschriftung benennt ausdrücklich die Ebene. Änderungen sind reversible Ebeneneigenschaften,
kein stilles Umfärben anderer Ebenen oder Änderung aller bisherigen Striche.

## Lebenszyklus / Schutz

UI unterscheidet lokale Entwurfssicherung, Datei und Kontobibliothek. Der lokal bestätigte
Dokumentstand bekommt eine eigene Generation; nur dieser schützt beim Verlassen. Bei laufender
Geste, ausstehendem/fehlgeschlagenem lokalen Schreiben oder Atlas-Änderung ohne bestätigten Save
bleibt eine Verlassenswarnung. Sichtbarkeitswechsel beendet/verwift unvollständige Gesten sauber
und sichert den zuletzt abgeschlossenen Stand sofort statt nur auf beforeunload zu vertrauen.
Keine Hintergrundnavigation zur Übersicht; 401 von Bibliotheksoperationen zeigt ein klares
Anmeldeproblem und einen normalen Login-Einstieg in neuem Tab. Editor/Draft bleiben geöffnet;
403 ist weiterhin eine Berechtigungsablehnung. Nach Kontoänderung gelten weiter die vorhandenen
Save-Sperren und kontogetrennten Entwurfsräume. Keine Verlängerung der harten Authentifizierungsgrenze.

## Begründung / Kriterien / Handoff

[MDN Canvas-Komposition](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/globalCompositeOperation)
stützt Masken-/Farbkomposition mit den vorhandenen nativen Mitteln.
[beforeunload](https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeunload_event) ist keine
verlässliche alleinige mobile Sicherung; [visibilitychange](https://developer.mozilla.org/en-US/docs/Web/API/Document/visibilitychange_event)
liefert den zusätzlichen Lebenszykluseinstieg. Der aktuelle JS-Code besitzt bereits transiente
Gesten und Generationsschutz; diese Mechanismen werden erweitert, nicht ersetzt.

Medium: Bildquellen im Raster → B06a zuerst, komplette geprüfte Quellensammlung auch im Rollback.
Medium: zusätzliche temporäre Pixelpuffer → vorhandene Karten-/Historygrenzen, kleine begrenzte
Spitzencaches, erst gewählte Quelle laden. Medium: Strich-/Autosave-Rennen → Geste einfrieren,
Cancel/Undo/Redo und verzögertes IndexedDB-Schreiben testen. Medium: neuer Effekt-Schemaanteil →
JS/Python-/Datei-/Bibliotheks-Roundtrip. Kein Paket überschreibt fremde Daten oder lockert Kontextrechte.

Deploy: gezielte Pixel-, Undo-, Auth-/Kontowechsel-, Speicher- und Browserprüfungen; B06a und B06b
je Commit/Push, aktuelle Quelle/Image abgleichen, App-Release, normale UI-Reise Karten → Pinsel/
Bibliothek, Live-Proof und Rollbackbeleg. Ursachenfrage des früheren Ausstiegs bleibt als nicht
reproduziert dokumentiert; technische Schutzverbesserungen sind kein Beweis für dessen Ursache.
