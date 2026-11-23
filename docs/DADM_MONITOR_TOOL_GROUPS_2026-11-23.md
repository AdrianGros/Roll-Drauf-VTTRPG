# Monitor: ausgewählte Playtable-Werkzeuggruppen

Status: geliefert, gepusht und live abgenommen am 23.11.2026. Der freigegebene Entwurf „Werkzeuggruppen“ ist unter https://vtt.roll-drauf.de über Kampagnen-Hub → Sitzung erreichbar. Grundlage sind das [Konzept](DADM_APPLY_PLAYTABLE_UX_2026-11-23.md), der [Liefervertrag](DADM_APPLY_TOOL_GROUPS_DELIVERY_2026-11-23.md), der [Deploy-Bericht](DADM_DEPLOY_TOOL_GROUPS_2026-11-23.md) und die [begrenzte Beschriftungsnacharbeit](DADM_DEPLOY_TOOL_GROUP_LABELS_2026-11-23.md). Die Umsetzung erfolgte ohne Agent-/Orchestrator-Aufrufe.

## Beobachtetes Ergebnis

Die untere Leiste hat drei feste Gruppen: Auswählen/Bewegen/Messen; Szenen/Figuren/Initiative/Karte & Sicht; Chat/Würfeln/Mehr. DM sehen zehn Hauptzugänge, Player neun. Einheitliche Symbole, sichtbare Namen, 52-Pixel-Höhe und definierte Werkzeug-/Fensterzustände ersetzen die bisherige Mischung. Auf schmalen Displays brechen die Gruppen um. Wand, Licht, Markierungen und Etagen sind über Karte & Sicht erreichbar; Token-Sichtbarkeit über Figuren. Mehr öffnet Journal, Beyond20, Einstellungen, Hilfe, Tischmenü und die durchsuchbare Befehlsübersicht. Die getrennte Player-Komposition lädt weiterhin keine DM-Befehlsdefinitionen.

Fenster bleiben unabhängig verschiebbar, ihre Inhalte scrollen einzeln und Positionen überstehen Schließen sowie Reload. Bestehende Felder und Formularentwürfe bleiben erhalten. Die Messoptionen liegen oberhalb der unteren Leisten und unter geöffneten Fenstern; Auswahlfelder, Menüs und Textboxen übernehmen die gewählte Palette. Mehr schließt beim Öffnen einer Funktion; Escape im Tischmenü gibt den Fokus an den sichtbaren Mehr-Zugang zurück.

## Lieferidentität und Betrieb

Aktuelle Funktionsquelle: `3fd012f4251e580a76e3f093ee143e13687e4480`. Laufendes Image: `sha256:4c87060242643b534394516c0a458974c716fd84bc742a84d587b7e72451e516`. Branch: `feat/playtable-tool-groups-20261123`; die Funktionscommits sind gepusht. Die elf geänderten Laufzeitdateien wurden nach der Live-Abnahme im tatsächlich laufenden Container erneut per Hash mit den Quellen verglichen: keine Abweichung.

Der erste Funktionsbuild `e29cd96f9` bestand drei funktionale Live-Reisen. Die anschließende Bildkontrolle zeigte eine alte Regel, die Beschriftungen verschobener Originalbuttons in Unterfenstern ausblendete. Die Nacharbeit öffnete dafür ausdrücklich erneut Deploy und änderte ausschließlich eine CSS-Regel. Vier erweiterte Browserfälle und alle drei Live-Reisen prüfen nun sichtbare Texte. Das aktuelle DM-Bild zeigt „Token-Sichtbarkeit“ vollständig beschriftet.

Beide Schritte verwendeten ein begrenztes App-only-Overlay auf dem jeweils tatsächlich laufenden unveränderlichen Image. Die letzte Bildprüfung kontrollierte 329 geerbte/geänderte Quelldateien; die erste 332 einschließlich der neu hinzugekommenen Katalog-/SVG-Dateien. Die übrigen VTT-Dienste behielten seit der Ausgangsversion ihre Identität und Startzeit. Der Reminder-Timer ist aktiv, sein zuletzt geprüfter Worker-Lauf meldet Erfolg und Exit 0. Keine Schemaänderung. Datenbanksicherungen sind als Archive lesbar; ein Restore wurde nicht ausgeführt.

Vollständiger Rückweg auf das Image vor den Werkzeuggruppen: `/srv/migration/2026-11-11/feedback-tool-groups-labels-20261123/3fd012f42/rollback-to-pre-tool-groups.sh`. Der abgesicherte Wrapper führt zuerst den CSS- und danach den UI-Rollback aus; er ist syntaktisch geprüft, wurde jedoch nicht ausgeführt. Lieferdetails: [delivery.json](proofs/tool-groups-2026-11-23/delivery.json), [Betriebsnachprüfung](proofs/tool-groups-2026-11-23/postcheck.json).

## Abnahme und Belege

| Bereich | Ergebnis |
| --- | --- |
| Autorisierte API-/Rollenwege | 32 gezielte Prüfungen bestanden |
| Werkzeuggruppen und sichtbare Zeilenbeschriftungen | Vier finale Browserfälle bestanden: DE/EN, DM/Player/Owner im Spielerplatz, 320/390/1024/1440 |
| Fenster und Paletten | Alle fünf bestehenden Fälle bestanden über die dokumentierten Teilläufe; drei finale Live-Reisen bestätigen Bewegung, isoliertes Scrollen, Reload und sechs berechnete Farbproben |
| Token-Sichtbarkeit, persönliche Aktionen und Tischplatz | Acht Fälle im dokumentierten erfolgreichen Rollen-/Transport-Teillauf bestanden |
| Begleiter | Zwei finale Fälle bestanden: Identität und Schaden bleiben nach Reload erhalten; der Test wartet auf Socket-Präsenz und misst seine synthetische Layoutprobe atomar |
| Kalibrierung, Licht/Wand, Journal-Medien | Drei gezielte Reisen bestanden; der Kalibrierungstest aktiviert das von ihm vorausgesetzte Einrasten ausdrücklich |
| Mobile Zusatzwege | Frühere Zusatzläufe bestätigen unter anderem Chromium/WebKit-Touch und Rotation; die finale Live-Abnahme bestätigt Chromium-Touch auf 390 Pixeln |

Die finale normale Live-Reise nutzt Chromium-DM bei 1440/Nacht, Firefox-Player bei 1440/Pergament und Chromium-Player bei 390/Nacht. Sie prüft außerdem Messschalter, sichtbare Untermenütexte, Beyond20-Zugang, DM-Etagen-/Sichtbarkeitszugänge und das tatsächliche Speichern sowie Wiederladen einer Rastereinstellung. Die Player laden keine DM-Komposition. Prüfkonten, Kampagne, Sitzungen und temporäre Zugangsdaten wurden jeweils entfernt. Discord-OAuth wurde nicht ausgeübt; die Abnahme verwendete isolierte synthetische Kontositzungen.

Ein erster Versuch nach dem Nachfolge-Deployment scheiterte an der fünfsekündigen Bereitschaftserwartung vor der Tischkomposition. Seine QA-Daten wurden bereinigt. Der Wiederholungslauf mit ausdrücklich gesetzter 30-Sekunden-Erwartung bestand vollständig; Anwendungscode wurde dafür nicht geändert.

Belege: [finale Live-Reisen](proofs/tool-groups-2026-11-23/live/live.json), [QA-Bereinigung](proofs/tool-groups-2026-11-23/live/cleanup.json), [DM-Bild](proofs/tool-groups-2026-11-23/live/windows-dm-chromium-1440.png), [Player/Pergament](proofs/tool-groups-2026-11-23/live/windows-player-firefox-1440.png), [Player/Touch/Nacht](proofs/tool-groups-2026-11-23/live/windows-player-chromium-390.png), [Prüfprotokoll mit Befehlen und Vorbefunden](proofs/tool-groups-2026-11-23/verification.json).

## Offene Vorbefunde und Grenze

Niedrig für diesen UI-Schnitt: Acht ältere Quelltext-Stringtests scheitern mit identischen Test-IDs bereits auf der unveränderten Baseline. Ältere Mess-/Nebelreisen sind ebenfalls nicht grün; insbesondere bleiben Quadratmaß-Erwartungen und die weiterführende Zwei-Client-Nebelprüfung offen. Diese Lieferung änderte keine Mess-, Geometrie- oder Nebelberechnung.

Separater Prüfbedarf: Der ältere Vorlagen-Platzierungsweg scheitert in der Browser-Testumgebung auch nach Anpassung an Pixelmaße und die aktuelle direkte Platzierung. Derselbe aktuelle Test auf unverändertem Anwendungscode zeigt dieselbe Fehlermeldung, noch bevor er den neuen Mehr-Zugang verwendet. Dieser Weg wird ausdrücklich nicht als bestanden oder behoben bezeichnet. Die Produktionseigenschaft dieses Vorbefunds wurde mit diesem UI-Schnitt nicht abschließend bestimmt; dafür ist eine eigene Untersuchung der konkreten Antwort erforderlich.

Eine komplett grüne Repository-Gesamtsuite oder eine menschliche Usability-Vergleichsstudie wird nicht behauptet. Bereits geöffnete Seiten benötigen ein Neuladen. Empfehlung: diesen UI-Schnitt schließen; als nächsten begrenzten Schritt die vorhandenen Vorlagen-/Mess-/Nebel-Prüflücken abgleichen und die Gruppierung in einer echten DM-Spielsitzung beobachten.

Artefakte: Konzept-/Deploy-/Monitor-Dokumente, Quellen, Prüf-JSON und Screenshots bleiben permanent im Projekt; Sicherungen und Rückwege im zugriffsbeschränkten Release-Verzeichnis. Temporäre QA-Zugangsdaten wurden entfernt.
