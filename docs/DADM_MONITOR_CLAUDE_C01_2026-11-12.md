# Monitor C01/P4 – funktional live, Kontrastnacharbeit offen

Quelle f5790c240, Image sha256:86ac41ff39eb8deaedc7bc4836102a1427df0621a1201434175f797ff48cc270
auf https://vtt.roll-drauf.de. Normaler Weg: Hauptnavigation → Ansicht und Sprache;
Bogen/Creator/Karten/Compendium/Creation Engine. Kampagnen-Hub → ausdrücklich
DM oder Player → DM-Sessionpanel/Kartenmaßstab bzw. Player-Messen.

62 integrierte Prüfungen bestanden (Browser, Kartenmaßstab, Tischkontexte). Eine
zusätzlich verstärkte Messprüfung besteht: tatsächliche Bildschirmrasterweite
berücksichtigen, erstes festes Segment exakt prüfen statt Textteiltreffer oder
bewegliche Vorschau. Compiler2800 Quellen, negative DE/EN-/Platzhalter-/Duplicate-
Fälle verweigert; JS590 markierte Literale ohne fehlenden Katalogeintrag.
Separater Claude-Review03 gab den vorausgehenden Diff zur Integration frei.

Live mit echten Formularlogins eigener Testnutzer: Firefox390 EN/Nacht/ft am
Bogen (Name Speichern unverändert), Creator/Karten/Compendium/Eagle über normale
Navigation, beide Tischrollen, DM-Kalibrierung → Player5ft → Einheitswechsel1.5m
→ unkalibriert wieder1square. Keine DM-Komposition beim Player. Erster Live-
Prüfversuch verwendete beim Player nicht vorhandene DM-Hubselektoren; zweite
Messprüfung erfasste zusätzlich die Mausvorschau, dritte suchte einen verdeckten
Zoomresetbutton. Korrigiertes Skript leitet die Bildschirmrasterweite aus dem
aktuell gerenderten Zoom ab und prüft das erste feste Segment exakt. Alle drei
funktionalen Reisen bestehen. Diese Skriptkorrekturen ändern keine Anwendung.

**Offener Medium-Befund:** Screenshotprüfung zeigt schlechte PlayChrome-Kontraste
bei einigen Panelüberschriften/Labels (Pergament) und aktiven Controls (Nacht).
Die bisherige Selector-Matrix enthielt diese Flächen nicht. C01 ist daher noch
nicht vollständig geliefert; finales Apply-Addendum begrenzt CSS-/Browsernacharbeit,
Claude setzt diese um. Canvas-/Dokumentfarben und Tischrechte bleiben außerhalb.
Kein Gesamt-Readiness- oder menschlicher Abnahmeclaim.

Backup vor additiver Tabelle campaign_map_scales, reflektierte Spalten geprüft.
App-only Compose; andere VTT-Dienste unverändert. Vorimage und syntaktisch geprüftes
Rollbackskript erhalten; Rückrollen/DB-Wiederherstellung nicht ausgeführt.
Alle eigenen Live-Testnutzer, Kampagne, Sessions, Figur, Kontexte und Maßstabszeile
entfernt; Zugangsdaten in Container und Host gelöscht. Belege samt exaktem Source-,
Image-, Compose- und Rückwegverweis: [delivery.json](proofs/presentation-2026-11-12/delivery.json).
Nächster begrenzter Schritt: PlayChrome-Kontrast prüfen, unabhängiger Diffreview,
kleine Nachlieferung und Live-Sichtprüfung. C02/C04 separat, noch nicht live.
