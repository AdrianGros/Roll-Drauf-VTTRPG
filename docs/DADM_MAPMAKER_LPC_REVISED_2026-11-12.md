---
date: 2026-11-12
profile: standard
phases: discover, apply, deploy, monitor
status: deployed and live-verified
---

# Kartenwerkstatt: LPC Revised zerlegen (statische Kartenmotive)

## Auftrag

Owner, 11.11.2026 („Jo“): nach den Kenney-Paketen auch LPC Revised zerlegen.

## Discover

- LPC Revised hat 64.310 Einträge. **63.972 davon sind Figuren-Animationsbögen**
  (Körper, Kleidung, Haare) für einen Charakter-Baukasten, also keine statischen
  Kartenmotive. Für die Karte relevant sind 315 Sheets mit zusammen 30,6 Mpx:
  Objekte (188), Bauteile (98) und Gelände (29).
- Ein Probelauf erkannte 3.047 freistehende Motive. Die Erkennung ist bei LPC
  **empfindlich**: In 119 der 259 Motiv-Sheets ändert sich die Motivzahl
  zwischen 2, 4 und 6 px Verbindungsabstand. Grund: LPC packt Varianten oft Kante
  an Kante (Bettbausätze, Truhen, Kisten, Arbeitsplatten, Sesselreihen,
  Lebensmittel). Dort kann keine Pixelanalyse Motive trennen, die sich berühren.
- Bäume, Pflanzen, Blumen und Felsen sind ebenfalls dicht gepackt, berühren
  sich aber nur an den Kronenrändern.
- Unter den 315 Sheets sind Hilfsebenen (Leuchtmasken, Schatten, ein
  Cutaway-Overlay) und Animationsstreifen (Wasserfall, Türen mit je 112
  Öffnungsbildern, Feuer, Kessel, Fernsehrauschen).
- 62 Sheets sind Raster-Bausätze: Böden, Wände, Dächer, Borten, Zäune,
  Holzbrücken, Gelände und Klippen. Eines davon (Treppenwand, 254×251 px) ist
  nicht durch 32 teilbar.

## Apply

1. **Mehrere Sheets pro Profil**, jedes mit eigenem Modus. Das Profil
   `tools/mapmaker_slices/lpc-revised.json` beschreibt 191 Sheets: 63 im
   32-px-Raster (nur Kacheln) und 128 als freistehende Motive (nur Stempel).
2. **Auswahlregel für Motiv-Sheets:** Ein Sheet wird nur aufgenommen, wenn die
   Motivzahl bei 2 und 4 px Abstand gleich bleibt (überall mindestens 4 px Luft)
   und keine Gruppe über das Vierfache der mittleren Größe hinausgeht. Dazu kommen
   sichtgeprüfte Ausnahmen (Steinsäulen, Dachkanten, Zierfenster B) und
   bestätigte Ein-Motiv-Sheets (Kopierer, Kühlschrank, Herd, Schminktisch,
   Rankenteppich, Nähmaschinentisch, Schleifstein, Werktisch, Briefkästen,
   Sägemehl). Ein-Motiv-Sheets, die sich in der Sichtprüfung als mehrere
   aneinanderstoßende Varianten zeigten, wurden wieder herausgenommen.
3. **Neue Trennverfahren (Opt-in je Sheet, sichtgeprüft):**
   - *Projektionsprofil*: Pixel je Spalte und Zeile zählen und an tiefen Tälern
     trennen (höchstens 12 % des Spitzenwerts, mindestens 20 px je Seite). Damit
     stehen Bäume, Pflanzen und Felsen einzeln, Stämme bleiben an ihren Kronen.
   - *Raster-Übersteuerung je Block*: Der Buschblock der Pflanzen und die
     Blütenbusch-Reihen werden in ihre 32-px-Felder geteilt.
4. **Nicht zerlegt, mit Begründung im Profil:** Figurenbögen, Hilfsebenen,
   Animationsstreifen, die Treppenwand und die dicht gepackten Modul-Sheets. Sie
   bleiben wie bisher als ganze Sheets mit Ausschnittdialog verfügbar; Figurenbögen
   bleiben unter „Figuren & Kleidung“.
5. Deutsche Namen je Sheet, nummeriert („Standuhr 1“, „Baum (Sommer) 7“,
   „Holzdielen A 12“). Schattenellipsen der Bäume heißen „Baumschatten“.

## Ergebnis

| Bereich | Stempel | Kacheln |
| --- | ---: | ---: |
| Gelände (Bäume, Pflanzen, Blumen, Wildblumen, Pilze, Felsen; Gelände-/Klippen-Tilesets) | 725 | 1.538 |
| Bauteile (Häuser, Türrahmen, Fenster, Säulen, Treppen, Brunnen, Dachkanten …; Böden, Wände, Dächer, Borten, Zäune) | 221 | 11.147 |
| Objekte (Möbel, Betten, Leuchten, Werkbänke, Lebensmittel, Stoffe, Rollstühle …) | 812 | 0 |

15.697 neue IDs; 1.254 pixelgleiche Kacheln ausgeblendet; 55 Splitter unter der
Mindestgröße verbucht. Der Katalog wächst von 75.373 auf 91.070 Einträge.

## Deploy

Commit `b1d5543c2` auf `feat/creation-engine-g1`, gepusht. Checks: vollständiger
Lauf 107 grün, 3 übersprungen (Flask-Varianten). Der Slicer-Test setzt alle
15.697 LPC-Zerlegungen pixelgenau neu aus den Original-Sheets zusammen
([`regression.txt`](proofs/mapmaker-lpc-revised-2026-11-12/regression.txt)).

Live lief inzwischen das fremde Release `feedback-atlas-final-20261111-af633057f`
(Cherry-Picks der Kartenwerkstatt-Commits plus Atlas, Übersetzungen und
Landmassen-Werkzeug). Die fünf überschriebenen Nicht-PNG-Dateien waren dort
byteidentisch mit der Basis `2ce033995`, keine der 14.265 neuen PNGs existierte.
Overlay aus `git archive` (14.270 Dateien, im Image per Hash geprüft). Image
`roll-drauf-vtt-app:lpc-revised-20261112-b1d5543c`
(`sha256:480d646fc769aef7093472ae6d7662bc8ec966dbe4d3582423312d8f629edd1e`),
live ab 2026-11-12 21:39 UTC. Nur der App-Dienst wurde neu erstellt. Rollback auf
das Atlas-Release: `/srv/migration/2026-11-12/lpc-revised/rollback.sh`.

## Monitor

- Health ok, keine Fehler im App-Log; DB/Redis/Mail unverändert. Der Server kennt
  91.066 Symbol-IDs. Öffentlich sind 5/5 Nicht-PNG-Dateien und 30/30
  Stichproben-PNGs hashgleich.
- Live über **Hauptnavigation → Karten**, Chromium 1440 und 390 px
  ([`live-journey.json`](proofs/mapmaker-lpc-revised-2026-11-12/live-journey.json)):
  „Standuhr 1“ und „Baum (Sommer) 7“ werden ohne Ausschnittdialog gesetzt,
  „Holzdielen A 1“ und „Gelände (Sommer) 1“ ins Raster gemalt. Die
  Kontrollfälle aus Tiny Town, Castle RPG und Roguelike funktionieren weiterhin.
  Die Kachelauswahl umfasst 14.374 Kacheln. Keine Konsolen- oder CSP-Fehler.
  Die Abnahme lief als Gast, angemeldete Player-/DM-Läufe gab es nicht.

## Restrisiken und nächster Schritt

- **Mittel, Ladezeit:** `lpc-revised/palette.json` wächst von 14,4 auf 17,1 MB
  und wird ungepackt ausgeliefert; mit gzip wären es 3,1 MB. Das Laden aller
  Paletten beim Start bestand schon vorher. Empfehlung: Kompression für JSON
  im Webserver aktivieren oder Paletten nachladen.
- Offen: 94 dicht gepackte LPC-Objekt-Sheets (Bettbausätze, Truhen, Kisten,
  Sesselreihen, viele Lebensmittel-Sammlungen) bleiben ganze Sheets mit
  Ausschnittdialog. Sie brauchen Rechteck-Authoring je Sheet, Bilderkennung
  allein trennt berührende Motive nicht.
- Niedrig: Kachelnamen der großen Tilesets sind nummeriert („Holzdielen A 37“);
  gefunden wird über Paket, Kategorie und Namen.
