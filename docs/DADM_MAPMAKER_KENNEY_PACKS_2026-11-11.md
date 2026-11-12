---
date: 2026-11-11
profile: standard
phases: discover, apply, deploy, monitor
status: deployed and live-verified
---

# Kartenwerkstatt: Kenney Roguelike, Medieval RTS und Isometric Buildings

## Auftrag

Owner, 11.11.2026 („Jo“): die verbleibenden Pakete zerlegen, also Kenney
Roguelike, Kenney RTS/Isometric und LPC Revised. Dieser Bericht deckt die drei
Kenney-Pakete ab. LPC Revised folgt als eigener Schritt, weil dafür mehrere
Sheets pro Paket nötig sind (siehe unten).

## Discover

- **Medieval RTS:** 126 Herstellereinzelbilder in Standardgröße (64 px) und 126
  in HD (128 px); dazu je ein Spritesheet, ein Tilesheet und eine Vektordatei
  mit denselben Motiven. Bisher hießen alle „PNG · Default size · medievalTile_01“,
  Boden und Gebäude standen gemischt. **HD ist anders nummeriert:** 45 der 126
  HD-Dateien tragen eine andere Nummer als ihr Standardgegenstück.
- **Isometric Buildings:** 129 Einzelbilder modularer Stadtgebäude (Blöcke,
  Ladenfronten, Dächer, Flachdächer) und ein Atlas mit denselben Motiven.
- **Roguelike:** nur ein Sheet mit 57×31 Zellen zu 16 px und 1 px Abstand,
  1.704 davon belegt. Die Grafik hat keine einheitliche Umrisslinie und reicht bis
  an die Zellkanten. Die automatische Gruppierung schlug 160 Mehrzellgruppen vor;
  die Sichtprüfung zeigte viele Fehlverbindungen (zwei Betten nebeneinander, Baum
  mit Busch, Leuchter mit Kaktus, ganze Gegenstandsreihen).

## Apply

1. **Neuer Modus singles-v1** für Pakete mit Herstellereinzelbildern: Das Profil
   benennt und kategorisiert die Originale, markiert Bodenkacheln als Kacheln und
   blendet geprüfte Doppel aus. Es entstehen keine neuen IDs und keine neuen
   Pixel.
2. **RTS-HD-Doppel:** Jedes HD-Bild wurde per Bildvergleich (verkleinert gegen
   alle Standardbilder) genau einem Standardbild zugeordnet; alle 126 eindeutig.
   Angeboten wird die Standardgröße, die HD-Doppel sind ausgeblendet und bleiben
   gültig. Der Test `test_rts_hd_twins_match_their_standard_images` sichert die
   Zuordnung.
3. **Roguelike** im Rastermodus mit Abstand 1. Kenney hat das Paket als
   16×16-Einzelkachelsatz gebaut, deshalb bleibt jede Zelle eine Einheit.
   Übernommen werden nur sichtgeprüfte Mehrzellobjekte: sieben Banner, zwei Zelte,
   Standspiegel, hoher Schrank, Denkmal, Rosette, Holzrahmen und sechs zwei Kacheln
   hohe Bäume. Dazu kommen 24 Flächen-Sets (Becken, Erd-, Gras-, Stein- und
   Sandflächen, Teppiche). Module wie Betten-, Marktstand- und Mauerteile bleiben
   Einzelteile. Gelände, Becken, Mauern, Dächer, Wandflächen und Teppiche sind
   Kacheln; Möbel, Türen, Fenster, Bäume, Hausrat, Grabsteine und Markierungen
   sind Stempel.
4. **Isometric:** nur Stempel, benannt nach Typ und Farbe („Ladenblock mit
   Markise“, „Dach (rot)“, „Flachdach mit Lüftern“).

## Ergebnis

| Paket | Stempel | Kacheln | ausgeblendet | neue IDs |
| --- | ---: | ---: | ---: | ---: |
| Medieval RTS | 68 (Bäume, Felsen, Erze, Häuser, Burg, Zelte, 24 Figuren) | 58 | 126 HD-Doppel | 0 |
| Isometric Buildings | 129 | 0 | 0 | 0 |
| Roguelike | 768 | 914 | 65 (Objektteile, 13 Kachel-Doppel) | 1.747 |

Der Katalog wächst von 73.626 auf 75.373 Einträge.

## Deploy

Commit `447774d57` auf `feat/creation-engine-g1`, gepusht. Der Slicer
unterstützt seitdem mehrere Sheets pro Profil (für LPC Revised); alle
bestehenden Pakete bauen damit byteidentisch. Checks: Unit-Tests 47 grün, darunter
die Zuordnung aller 126 RTS-HD-Doppel per Bildvergleich. Der vollständige Lauf
brachte 102 grün, 3 übersprungen und 2 rot. Die roten Fälle betrafen den
bestehenden Ausschnitt-Test: Das ganze Roguelike-Sheet liegt jetzt hinter
768 Stempeln. Der Test sucht es nun über das Suchfeld; danach liefen er und die
neuen Pakettests grün.

Release: Overlay aus `git archive` (1.742 Dateien, im Image per Hash geprüft) auf
das damals laufende eigene Image. Image `roll-drauf-vtt-app:kenney-packs-20261111-447774d5`,
live ab 2026-11-11 13:38 UTC; Rollback
`/srv/migration/2026-11-11/kenney-packs/rollback.sh`.

## Monitor

- Health ok. Alle geänderten Nicht-PNG-Dateien und 25 Stichproben-PNGs sind
  öffentlich hashgleich. Der Server kennt 75.369 Symbol-IDs.
- Live über **Hauptnavigation → Karten**, Chromium 1440 und 390 px
  ([`live-journey.json`](proofs/mapmaker-kenney-packs-2026-11-11/live-journey.json)):
  Hohe Tanne und Zelt (Roguelike), Burg (RTS) und Ladenblock (Isometric) wurden
  ohne Ausschnittdialog gesetzt. Roguelike- und RTS-Kacheln wurden gemalt. Die
  Kachelauswahl zeigt 1.689 Kacheln. Keine Konsolen- oder CSP-Fehler. Die
  Abnahme lief als Gast, angemeldete Player-/DM-Läufe gab es nicht.
- **Nachtrag 12.11.:** Andere Releases haben die Kartenwerkstatt-Commits per
  Cherry-Pick in `feat/protocol-feedback-20261110` übernommen. Das laufende
  `feedback-catalog-actions-20261111-8fb56ccc3` liefert alle Katalogdaten
  byteidentisch zu `447774d57`, das Kachelwerkzeug ist erhalten. Die dort von
  Hand in `credits.html` ergänzten Anzeige-Einstellungen sind jetzt in
  `tools/mapmaker_catalog.py` übernommen; der Generator erzeugt die Live-Datei
  byteidentisch und entfernt sie bei künftigen Builds nicht mehr.
