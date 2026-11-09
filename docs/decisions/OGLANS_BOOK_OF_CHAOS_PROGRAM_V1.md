# DAD-M Programm: Oglans Book of Chaos

version: 1
status: **freigegeben** durch den Owner am 2026-11-09 („Der Plan klingt gut … go ahead“), mit dem Zusatz Clean Room
datum: 2026-11-09
phase: OC0 Deploy

## Ziel

Ein eigenes deutsches Erweiterungsbuch von Roll Drauf auf dem 2024er-Gerüst des
SRD 5.2.1. Es soll im Spielwert einem kommerziellen 5e-Erweiterungsbuch gleichkommen
und ist im Regelwerk lesbar, durchsuchbar und am Ende im Charakterbau spielbar.
Text, Namen und Welt stammen von Roll Drauf.

Die Vorlage, die Zuordnung ihrer Elemente und alle Lesezimmer-Unterlagen liegen
bewusst **nicht** im öffentlichen Repository, sondern privat auf dem Server
(Clean-Room-Ordner, siehe unten). Das Repository enthält nur das Verfahren und
die fertigen, eigenen Texte.

## Clean Room (Owner-Auftrag 2026-11-09)

Aufgebaut nach dem Muster des Clean-Room-Reverse-Engineerings: Ein Team liest das
Original und beschreibt nur die Funktion, ein getrenntes Team baut aus dieser
Beschreibung neu, und eine Schleuse dazwischen lässt nur Funktion durch. Der
Ablauf ist der Nachweis eigenständiger Schöpfung.

| Stufe | Wer | Sieht | Gibt weiter |
| --- | --- | --- | --- |
| Lesezimmer | eigener Agent; der Owner als Prüfer mit seinem gekauften Exemplar | Vorlage aus Wissen, offizielle kostenlose Playtest-PDFs des Verlags, SRD 5.2.1 | Mechanik-Karten (`oglan.spec.v1`): Werte und kurze Funktionsbeschreibungen in eigenen Worten, keine Namen, kein Text der Vorlage |
| Schleuse | Prüfskript plus Orchestrator | Karten, Spurliste der Originalnamen | nur bestandene Karten, ohne Prüffelder |
| Schreibstube | frischer Agent ohne Websuche und ohne Zugang zum Lesezimmer | nur Übergabe-Karten, Stilvorgabe, SRD 5.2.1 | eigene deutsche Texte mit eigenen Namen |
| Abnahme | Validator (Sperrliste, SRD-Namen), Endkontrolle gegen alle Originalnamen, Owner-Review | fertiges Paket | Live-Vorschau |

Regeln:

- **Keine Raubkopien:** keine inoffiziellen PDFs und keine Volltext-Fanseiten.
  Das Exemplar des Owners bleibt beim Owner: kein Scan, keine Fotos. Er gleicht
  nur Fakten ab (Zahlen, Stufen, Reichweiten).
- **Die Karte ist die einzige Brücke.** Das Paket weist mit `source.sha256` die
  versiegelte Übergabe aus, und `sourcePages` sind die Kartennummern.
- **Grenze:** Ein KI-Modell kennt veröffentlichte Bücher aus dem Training.
  Trennung, Schleuse, Sperrlisten und Owner-Prüfung senken das Risiko, schließen
  es aber nicht aus. Vor einem Bezahlangebot prüft eine Anwältin oder ein Anwalt
  für Urheber- und Wettbewerbsrecht.

## Feste Grenzen

- Eigenes Paket `oglans-book-of-chaos-de` (`kind: original`, Reader unter
  `/regelwerk/oglan`). Das SRD-Paket bleibt unverändert.
- 2024-Gerüst: Unterklassen ab Stufe 3 auf den SRD-Merkmalsstufen, Talente in
  2024-Kategorien, Zauber im 2024-Format, Fokus statt Ki.
- Keine Bezugnahme auf die Vorlage in Oberfläche, Suche, Metadaten oder
  Ankündigungen.
- Jede Phase geht als Vorschau live. „Veröffentlicht“ wird das Buch erst nach
  Owner-Freigabe und Rechtsblick (OC8).
- Lesen im Regelwerk schaltet keine Mechanik im Charakterbau frei.

## Phasen

| Phase | Inhalt | hängt ab von |
| --- | --- | --- |
| OC0 | Fundament: Paketart `original`, Sperrliste und SRD-Namensprüfung im Validator, Reader mit Buchwahl, eigener Lizenzseite und Suche, Ein-/Ausschalter, Clean-Room-Ablauf | – |
| OC1 | Durchstich: Vorwort, eine Druiden-Unterklasse, ein Signaturzauber, live als Vorschau | OC0 |
| OC2 | 11 Unterklassen (Barbar, Barde, Kleriker, Druide, Kämpfer); Kompendium-Anbindung des Buchs | OC1 |
| OC3 | 14 Unterklassen (Mönch bis Magier), restliche Klassenoptionen | OC2 |
| OC4 | Eine neue Klasse mit 4 Unterklassen und ihren Gegenstandsverbesserungen | OC1 |
| OC5 | Zauber, Talente, Kampfstil-Talente, erweiterte Zauberlisten, eine eigene Abstammung | OC1 |
| OC6 | Magische Tätowierungen, Gegenstände und Artefakte, Gruppen-Gönner | OC1 |
| OC7 | Werkzeuge für die Spielleitung | OC1 |
| OC8 | Spielbar im Charakterbau (Creator-Meilensteine C7/C8), Rechtsblick, Veröffentlichung | OC2–OC7 |

Jede Phase läuft Discover → Apply → Deploy → Monitor.

## Abnahme je Phase

- Jeder Eintrag hat eine Karte in der Übergabe, eigenen Text und stabile Regel-IDs.
- Validator grün. Endkontrolle gegen die Spurliste ohne Treffer.
- Balance-Notiz je Unterklasse und Klasse.
- Owner-Review je Bereich; danach werden die Kartennummern als geprüft
  (`reviewedPageRanges`) eingetragen.
- Live lesbar unter `/regelwerk/oglan`. SRD-Regelwerk und SRD-URLs unverändert.

## Rollen

- Owner (Donutarian): Product Owner, Abnahme, Faktenprüfer im Lesezimmer, Review.
- Orchestrator (KI): Ablauf, Schleuse, Technik. Er schreibt keine Buchtexte.
- Lesezimmer-Agent und Schreibstuben-Agent: getrennte KI-Agenten je Phase.

## Rollback

- Schalter `OGLAN_BOOK=0` (Umgebung) nimmt das Buch aus Reader und API. SRD,
  Charaktere und Kampagnen bleiben unberührt.
- Vorheriges Image bleibt lokal. Paketstände sind versioniert.

## Entscheidungslog

| Datum | Entscheidung | Grund | Wer |
| --- | --- | --- | --- |
| 2026-11-09 | Programm v1 freigegeben | „Der Plan klingt gut … go ahead“ | Owner |
| 2026-11-09 | Clean-Room-Ablauf mit Lesezimmer, Schleuse und Schreibstube | Owner-Auftrag; Nachweis eigenständiger Schöpfung | Owner |
| 2026-11-09 | Keine Gratis-/Raubkopie der Vorlage; das Exemplar des Owners bleibt beim Owner, er prüft Fakten | Rechtssicherheit; sonst wäre der Clean Room wertlos | Orchestrator, Owner informiert |
| 2026-11-09 | 2024-Basis; Oglan als chaotischer Gelehrter und Erzählstimme; frei lesbar als Vorschau; eigenes Urheberrecht an den Texten | Empfehlungen aus dem Discover, mit der Freigabe übernommen; jederzeit änderbar | Owner (Freigabe) |
| 2026-11-09 | Kompendium-Anbindung von OC0 nach OC2 | Der Kompendium-Builder liest die SRD-Struktur; mit nur zwei Einträgen lohnt die Anpassung erst ab OC2 | Orchestrator |
| 2026-11-09 | Lesezimmer-Unterlagen privat statt im öffentlichen Repo | Repo ist öffentlich; Zuordnungstabellen gehören zum privaten Nachweis | Orchestrator |
