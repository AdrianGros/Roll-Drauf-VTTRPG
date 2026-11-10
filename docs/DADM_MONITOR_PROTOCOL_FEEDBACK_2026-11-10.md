# Monitor: Protokollfeedback – veröffentlichter erster Funktionsumfang

Status: **Paket 1 live abgenommen**. Dauerhaft aufbewahren.
Gesamtauftrag bleibt hinsichtlich der ausdrücklich offenen Pakete in der
[40-Punkte-Matrix](PROTOCOL_FEEDBACK_SPECIFICATIONS_2026-11-10.md) unvollständig.

## Beobachtetes Ergebnis

Creator, kompakter SRD-Spielbogen, Kampagnensuche und Kartenbedienung sind über
die normale Hauptnavigation auf `https://vtt.roll-drauf.de` erreichbar. Die
Produktionsquelle wurde vor Umsetzung mit dem laufenden Image abgeglichen;
fremde Änderungen im ursprünglichen Arbeitsbaum wurden nicht übernommen.

| Rolle / Browser | Benutzerweg | Ergebnis |
| --- | --- | --- |
| Player / Chromium | Übersicht → Charaktere → Held anlegen → geführter Creator → Bogen | Paket C vorhanden; Rüstung mit Paketquelle; Bogenbereiche, Nacht, ft, Tastatur und Münzänderung erfolgreich. Uploadverwaltung erreichbar; Abmelden führt zum Login. |
| Player / Chromium | Charakterarchiv → eigener synthetischer Magier → Bogen → Zauber | Gradfilter zeigt passende Zauber. Der zusätzliche Testcharakter wurde über die normale eigene Draft-/Finalize-API vorbereitet, der Bogen über das Archiv geöffnet. |
| DM / Chromium | Übersicht → Karten → Leere Karte | Zeichnen, rechts verschieben, weiterzeichnen; Dokumentgeneration und Undo beim Pan unverändert. Aktive Ebene direkt erreichbar, Ebene hinzugefügt, Ort über Liste wieder bearbeitet. Bibliothek gespeichert, erneut geöffnet und gelöscht. |
| DM / Firefox | Derselbe Kartenweg | Ebenfalls bestanden; finale Kontokarte einschließlich Abmelden vollständig innerhalb der Navigationszeile. |

Der Player-Durchlauf erfolgte auf `b8f3b54ba`; die danach angepassten App-Regeln
betreffen ausschließlich die Karten-Navigationszeile. Der finale Karten-Durchlauf
prüft `32cc5bfee`, inklusive sichtbarer Kontokarte und gespeicherter Ortsänderung
nach tatsächlich abgeschlossenem Bibliotheksladen.

## Releaseidentität und Nachweise

- Funktionscommit: `32cc5bfee66419176d38248f68d5941144dad79f`.
- Branch `feat/protocol-feedback-20261110` auf GitHub gepusht;
  Remote-Referenz vor Abschluss geprüft.
- Image: `roll-drauf-vtt-app:protocol-feedback-20261110-32cc5bfee`.
- Image-ID: `sha256:f6bc1008f0bb03962fba266d3f3477e5edf7c81fcfe205586dab6bd2cc0b445a`.
- Finaler App-Neustart: 10.11.2026, 21:48 UTC. Öffentliche Healthchecks vor und
  nach Datenbereinigung `ok`; genaue Zeiten in `deployment.json`.
- 225 Datei-Hashes im fertigen Image und alle 13 öffentlich ausgelieferten
  geänderten Static-Dateien stimmen mit dem Manifest überein. 17 Overlaypfade;
  unveränderte Basis einschließlich neuerer Tischplatz-/Beyond20-/Buchfunktionen.
- 195 verschiedene automatisierte Fälle bestanden. Fokussierte Wiederholungen
  sind nicht mehrfach gezählt. Größte Regression 159 Fälle; danach gezielte
  Prüfungen für die zuletzt angepasste Karten-Navigation.
- Datenbank, Redis und Mail blieben anhand Container-ID/Startzeit unverändert.
  Es gab keine Schemaänderung und keine neue App-Abhängigkeit.
- Zwei synthetische Konten, vier Testcharaktere, vier Entwürfe und eine nach
  einem abgebrochenen Test verbliebene Karte entfernt. Erfolgreiche Kartenläufe
  entfernten ihre Karten bereits über die UI. Verbleibende synthetische Konten,
  Charaktere und Karten: **0**. Temporäre Token-Datei gelöscht.

Maschinenlesbare Belege und Screenshots:
[Nachweisverzeichnis](proofs/protocol-feedback-2026-11-10/README.md).

Rollback bleibt serverseitig vorbereitet:
`/srv/migration/2026-11-10/protocol-feedback/rollback.sh`.
Er prüft die erwartete aktuelle Imagebezeichnung, stellt die ursprüngliche
Compose-Override-Datei wieder her und startet ausschließlich `app` neu.
Das vorherige Image bleibt zusätzlich unter
`roll-drauf-vtt-app:feedback-rollback-20261110-496595790afb` erhalten.
Rollback wurde syntaktisch geprüft, nicht als zusätzliche Produktionsunterbrechung
ausgeführt. Es sind keine Datenbankrückmigrationen nötig.

## Abweichungen während der Abnahme

Die visuelle Prüfung fand den abgeschnittenen Abmeldebutton. Ein größerer
Navigationsbereich allein genügte wegen eines geerbten Buch-Abstands nicht.
Der finale Fix setzt Höhe und Abstand ausdrücklich für den Editor und wurde
mit vollständiger dreizeiliger Kontokarte bei 1440/390 px und live geprüft.
Der Gastzustand hatte die zusätzliche Sessionzahl ausgeblendet.

Zwei Korrekturen betrafen die Live-Prüfung selbst: der erste Karten-Kaltstart
überschritt die voreingestellten fünf Sekunden der Browserassertion; danach
wurde auf den sichtbaren fertigen Zustand gewartet. Beim erneuten Öffnen einer
bereits unverändert angezeigten Karte genügte der vorhandene Ortstext nicht als
Ladenachweis. Der finale Test wartet deshalb auf die tatsächliche GET-Antwort
und das erneute Aktivieren des Speicherbuttons vor dem Löschen.

## Restumfang und nächste begrenzte Arbeit

| Einstufung | Offen / Grenze | Nächster Schritt |
| --- | --- | --- |
| Mittel – Anforderungs-/Abnahmegap | Vollständige Player-/DM-Kontexte und persönliche Hotbar sind nicht umgesetzt. Globale Tischplätze erfüllen die Owner-Entscheidung vom 01.11. nicht vollständig. Aus diesem Bericht wird kein pauschaler bestehender Rechtebypass abgeleitet. | Eigener Discover-/Apply-Vertrag für getrennte Komposition, tabgebundene Autorität, HTTP/Socket/Bootstrap/Resync/Sheet-/Legacy-Pfade; erst danach Hotbar. |
| Mittel – fehlende End-to-End-Abnahme | Firefox-Würfelübertragung zwischen echten Teilnehmenden und ein vollständiger menschlicher Spielabend sind nicht durch die Bogen-/Kartenprüfungen belegt. | Mit Tischkontext-Paket und realer Runde abnehmen. |
| Weiterer Funktionsumfang | Homebrew-Typen, globale Themes/Einheiten und vollständige Übersetzungen sind nicht geliefert. Nacht/Einheiten gelten hier für SRD-Bögen; Ausrüstungsquellen sind noch keine vollständige Bonus-Provenienz. | Jeweils eigene Daten-/Oberflächenverträge gemäß Matrix. |
| Fehlender konkreter Bezug | Gespräch nennt keine eindeutigen fehlenden Talent-/Unterklassen-IDs; die 200-%-Einstellung bleibt unzugeordnet. | Konkrete Einträge bzw. Bedienelement/Reproduktion ergänzen; keine willkürlichen Inhalte oder Grenzen einbauen. |
| Produkt-/Inhaltsentscheidung | Weltatlas, Landmassengenerator, visuelles Sheet-Authoring, zusätzliche Assetdateien/Lizenzen und Partner-Streaming bleiben offen. | Begrenzten Nutzen und Daten-/Inhaltsumfang definieren; keine Streamingfreigabe aus diesem Release ableiten. |

Empfehlung: den beschriebenen ersten Funktionsumfang schließen; als nächstes
den eigenständigen Discover-/Apply-Durchgang für Tischkontexte und Spieleraktionen
beginnen. Diese Empfehlung ist kein Abschluss aller 40 Kanbankarten.
