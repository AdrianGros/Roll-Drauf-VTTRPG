---
date: 2026-11-11
profile: standard
phases: discover, apply, deploy, monitor
status: deployed and live-verified
---

# Kartenwerkstatt: Castle RPG, LPC Castle und alle 2DPIXX-Sheets zerlegt

## Auftrag

Owner, 11.11.2026 („Jo“ auf den vorgeschlagenen nächsten Schritt): Die Sheets
von Castle RPG, LPC Castle und allen acht 2DPIXX-Paketen wie Tiny Town in ganze
Stempel und Rasterkacheln zerlegen. Grundlage sind die Owner-Entscheidungen vom
selben Tag: Bilderkennung erlaubt, nichts generieren, Kacheln getrennt von
Stempeln.

## Discover

- Bisher bot jedes dieser zehn Pakete nur das ganze Sheet mit manuellem
  Ausschnittdialog an. Castle RPG 512×512, LPC Castle 480×320 und fünf 2DPIXX-
  Sheets folgen einem 32-px-Raster; Ruinen, Interior und Dorf sind isometrische
  Einzelmotive ohne Raster.
- Erkennungsprobe ([`detect`](../tools/mapmaker_sheet_slicer.py)): gemalte
  Grafik ohne Umrisslinie verbindet sich häufiger, z. B. Laternenpfahl mit
  Ziehbrunnen oder Springbrunnen mit Kisten. Vollflächige Objektmitten
  (Fachwerkhaus, Felsbrocken, Plateau) werden nicht automatisch verbunden.
- 2DPIXX-Sheets enthalten einfarbige Füllkacheln (eingebackenes Schachbrett);
  LPC Castle ein Paketlogo und eine graue Wappenzeichen-Vorlage.
- Bei den isometrischen Sheets überlappen sich die Umrissrechtecke versetzter
  Blöcke und der beiden Dorfhäuser, obwohl sich die Pixel nicht berühren.

## Apply

1. **Profil-Erweiterungen (grid-alpha-v1):** `regions` benennen Rechtecke
   zeilenweise („Felsboden 1…n“), `kind: exclude` mit Begründung nimmt
   Nicht-Motive heraus, Komposite akzeptieren `{"rect": …}` (leere Zellen
   entfallen). Vollständige Verbuchung bleibt Pflicht.
2. **Neuer Modus components-v1** für Sheets ohne Raster: Pixelzusammenhang auf
   einer um wenige Pixel geweiteten Maske, damit Laub und Grasbüschel am Motiv
   bleiben und nahe, aber getrennte Blöcke getrennt bleiben. Jedes Motiv wird auf
   die eigenen Pixel maskiert. Isometrische Motive sind immer Stempel.
3. **Duplikate:** pixelgleiche Kacheln werden einmal angeboten, alle IDs bleiben
   auflösbar. Das betrifft vor allem die einheitlichen Füllflächen im Gebirge.
4. **Review per Bilderkennung:** Grenzen, Namen, Kategorien und Kachel/Stempel
   je Paket; Korrekturen stehen in `review.deviations` jedes Profils. Ablauf für
   weitere Pakete: [`tools/mapmaker_slices/README.md`](../tools/mapmaker_slices/README.md).

Unverändert: Editor-Code und Kartenformat. Die Lieferung besteht nur aus
Katalogdaten.

## Ergebnis je Paket

| Paket | Stempel | Kacheln | ausgeblendet¹ | ausgeschlossen |
| --- | ---: | ---: | ---: | ---: |
| 2DPIXX Wald | 9 | 33 | 31 | 13 Füllkacheln |
| 2DPIXX Höhle | 4 | 49 | 0 | 1 Füllkachel |
| 2DPIXX Schnee | 5 | 22 | 18 | 0 |
| 2DPIXX Stadt | 8 | 26 | 23 | 13 Füllkacheln |
| 2DPIXX Gebirge | 20 | 297 | 527 | 0 |
| 2DPIXX Ruinen (isometrisch) | 13 | 0 | 0 | 0 |
| 2DPIXX Interior (isometrisch) | 17 | 0 | 0 | 0 |
| 2DPIXX Dorf (isometrisch) | 6 | 0 | 0 | 0 |
| LPC Castle | 27 | 57 | 69 | Logo, Wappen-Vorlage |
| Castle RPG | 55 | 136 | 89 | 0 |

¹ Teile fester Objekte (Baumhälften, Torflügel …) und doppelte Kachelbilder;
weiterhin auflösbar. Insgesamt 1.541 neue IDs, 164 neue Stempel, 620 neue
Kacheln; der Katalog wächst von 72.085 auf 73.626 Einträge.

Beispiele: Castle RPG mit Uhrenbaum, Laternenpfahl, Ziehbrunnen, Springbrunnen,
Marktstand, Bannern, vier Fallgittertoren, Turm, Inseln und Wasserfall.
LPC Castle mit zwei Fallgittern, Toren, Rundturm und Bannern. Gebirge mit
Hängebrücken, totem Baum, Felsbrocken, Plateau und Abgrund. Wald mit großem
Laubbaum, Stümpfen und Truhen. Dorf mit zwei Steinhäusern, Brunnen, Zäunen und
Krügen.

## Deploy

Commit `bbb793c26` auf `feat/creation-engine-g1`, gepusht: Slicer, zehn neue
Profile mit Anleitung, Katalogdaten (1.245 neue PNGs, 5,7 MB) und Tests. Der
Editor-Code ist unverändert.

Checks ([`regression.txt`](proofs/mapmaker-sheet-packs-2026-11-11/regression.txt)):
43 Unit-Tests grün. Darin sind jede Zerlegung aller elf Profile neu aus dem Sheet
zusammengesetzt und verglichen sowie die korrigierten Grenzen festgeschrieben.
Der vollständige Lauf brachte 97 grün, 3 übersprungen (Flask-Varianten) und
1 rot. Der rote Fall war ein Testfehler: Nach einem wiederhergestellten
Entwurf fragte der Editor korrekt „Aktuelle Karte behalten?“, und der Test hat
die Rückfrage nicht bedient. Der Test beantwortet sie jetzt; die betroffenen
Fälle liefen danach dreimal grün. Ein zweiter Bau aller Pakete ist byteidentisch.

Seit der Kachelebene hatten andere Releases (`feedback-*`) das Live-Image
mehrfach erneuert, jeweils auf dem Kachel-Editor aufbauend. Alle 32 hier
überschriebenen Nicht-PNG-Dateien waren im laufenden
`feedback-origins-20261111-2b4924344` byteidentisch mit der Basis `50885c307`;
keine der neuen PNGs existierte. Overlay aus `git archive`, 1.277 Dateien im
Image per Hash geprüft. Aktives Image `roll-drauf-vtt-app:sheet-packs-20261111-bbb793c2`
(`sha256:e51a5ced9f91a9242afedc941444abe903380354884f29f3a14111c0445458e4`).
Nur der App-Dienst wurde neu erstellt, DB/Redis/Mail blieben unverändert.
Rollback auf `feedback-origins`: `/srv/migration/2026-11-11/sheet-packs/rollback.sh`.
Danach fehlen in Karten, die neue Stempel oder Kacheln nutzen, diese Symbole,
bis erneut ausgeliefert wird.

## Monitor

- `/health/live` ok (Start 12:48:58 UTC), keine Fehler im App-Log. Der Server
  kennt 73.622 Symbol-IDs (vorher 72.081). Öffentlich sind alle 32
  JSON/CSV/HTML-Dateien und 25 Stichproben-PNGs hashgleich zum Commit.
- Live über **Hauptnavigation → Karten** (`/mapmaker`), Chromium 1440 px
  ([`live-journey.json`](proofs/mapmaker-sheet-packs-2026-11-11/live-journey.json)):
  Laternenpfahl (Castle RPG), Banner rot (LPC Castle), Hängebrücke (Gebirge),
  Großer Laubbaum (Wald), Ziehbrunnen (Dorf) und Laubbaum (Ruinen) werden ohne
  Ausschnittdialog als ganze Stempel gesetzt. Pflaster, Steinmauer, Felsboden und
  Erdfläche werden ins Raster gemalt. Die Kachelauswahl zeigt 717 Kacheln. Bei
  390 px dasselbe für Castle RPG und LPC Castle. Keine Konsolen- oder
  CSP-Fehler.
- **Lücke wie bei den vorigen Kartenreleases:** Die Abnahme lief als Gast;
  angemeldete Player-/DM-Durchläufe wurden nicht ausgeführt. Editor, Paletten und
  Server-Validierung sind für alle Rollen identisch.

## Restrisiken und nächster Schritt

- Niedrig: Bezeichnungen der Bauteil-Kacheln sind zeilenweise nummeriert
  („Felsboden 12“). Gesucht wird über Paket, Kategorie und Bereichsnamen.
- Niedrig: Große Motive (Hängebrücke 448 px) starten auf 256 px skaliert,
  das ist die bestehende Grenze für die Startgröße von Stempeln.
- Offen: Kenney Roguelike (16 px mit Abstand, 1.767 Zellen), Kenney RTS/Isometric
  (eigene Einzel-PNGs plus XML-Atlas) und LPC Revised (64.307 Sheets) sind noch
  nicht zerlegt. Für die Kenney-Atlanten liefert der Hersteller Rechtecke, dort
  reicht ein Adapter statt Erkennung.
