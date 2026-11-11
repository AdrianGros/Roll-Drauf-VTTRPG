# Apply P3: Herkunftsprofile und erklärbare Spielwerte

status: abgeschlossen, Übergabe Deploy. input_summary: Discover P3 und
Autorisierung zur autonomen Programmlieferung. artifacts: Profile, Publikation,
Creator-/Bogenintegration, Tests und Lieferbelege; retention permanent.

## Festgelegter Umfang

Den bestehenden Eagle-Companion um einen beschrifteten visuellen Zusatz für
Background/Feat erweitern. Eagle bleibt editierbar; keine Rückkehr zum archivierten
G1 und kein neues freies Bogenformat. Quelle auswählen, Zusatz bearbeiten,
Vorschau/Prüfung, bewusst veröffentlichen. Quell-Digest muss seit Prüfung gleich
sein. Nicht unterstützte mechanische Eagle-Felder, Activities, Active Effects,
Advancements und Formeln blockieren; Beschreibungen bleiben sicherer Klartext.

`ce_rule_revisions`: additive unveränderliche Profile, Typ background/feat,
Quellrevision/-digest, Profil-Digest, Scope, Autor, Veröffentlichungsfassung.
Stabile IDs `homebrew.background.ID` / `homebrew.feat.ID`. Hintergrund: drei
Attribute, zwei Fertigkeiten, optional ein Werkzeug, genau ein erlaubtes
Origin-Talent; Startpaket bewusst Geld (50 GP), in Vorschau benannt.
Merkmal: Herkunfts- oder allgemeines Talent, Mindeststufe, optionale Attribut-
voraussetzung und ausgewählte typisierte Grants. Unterstützt werden feste
Fertigkeitsübung, feste RK-/Initiative-/Bewegungsboni, Initiative mit Übungsbonus,
HP je Charakterstufe und narrative Merkmale. Keine Skripte, beliebigen Formeln,
Stacking-Multiplikatoren oder Ressourcenautomatik. Maximal ein Grant je Ziel
pro Profil; verschiedene Talente addieren, Übung maximal einmal. Gleiche
Talent-ID wird nicht mehrfach angewendet. Origin-Talente verlangen Stufe 1 und
keine zusätzliche Voraussetzung. Allgemeine Talente mindestens Stufe 4.

Katalog/resolve prüft jede tatsächlich ausgewählte Homebrew-ID und transitive
Hintergrund-Talent-Verknüpfung. Personal nur Autor, campaign nur aktive Mitglieder/
Owner, global angemeldete Nutzer. Fertige Figuren kopieren Pins in `srd.rulePins`;
alle Regeln lesen dieselben Profile über `rules_data_for_block`. Neufassung ändert
bestehende Figuren nicht. Rebuild und Import prüfen erneut Auswahlrechte und exakten
Digest; keine Regelprofile aus hochgeladenen Dateien als Autorität. Kampagnenbindung
gilt für jeden Pin. Hintergrund-Talent wird per stabiler ID aufgelöst.

Bonuserklärungen entstehen während der bestehenden Auswertung: Basis, Beiträge,
Quellen-ID/-fassung, Stapelregel, Endwert. Attributswerte/-modifikatoren, Übungsbonus,
HP, RK (gewählte Formel), Bewegung, Initiative, Skills, Saves, passive Wahrnehmung,
Zauberangriff/-SG und Inventar-Angriffs-/Schadensboni. Overrides werden als explizite
letzte Änderung dokumentiert. Keine zweite Addition auf Anzeige oder Würfelpfad.
Bogen bietet aufklappbare Herleitungen und gepinnte Herkunftsangaben.

## Datenrückweg und Abnahme

Zuerst kompatibles Leser-Image liefern: Modell, Pin-Auflösung und unterstützte
Grants vorhanden, neue Veröffentlichung noch abgeschaltet. Backup vor additiver
Tabelle, gezielte Tests. Dieses Image wird der Rückweg des schreibenden P3-Release;
es kann bereits erzeugte neue Charaktere lesen. Erst danach Publikation/Creator-
Auswahl aktivieren. Kein blindes Zurückrollen neuer Figuren auf das alte P2-Image.
Bestehende Daten werden nicht umgeschrieben. Keine neue Dependency.

Medium-Risiken aus Discover sind damit im Entwurf behandelt; Testgates müssen
Zugriff, unbekannte Effekte, stale Digest, Pins nach Quelländerung, Import/Rebuild,
Kampagnenbindung, eindeutige Anwendung und Gleichheit von Herleitung/Spielwert prüfen.
Katalogaudit erfasst bekannte lizenzierte IDs ohne unbenannte Inhalte zu erfinden.
UI-Abnahme: Eagle → Beispiel-Merkmal/Hintergrund → prüfen/veröffentlichen → Creator
→ fertiger Bogen → erlaubte persönliche Aktion. Nächster Schritt: Deploy in den
beiden kompatiblen Schritten, anschließend Live-Nachweis und Monitor.

### Entwurfsbedienung im vorhandenen Eagle-Dokument

Der visuelle Zusatz speichert seinen typisierten Entwurf im vorhandenen Eagle-
Dokument unter `flags.rollDraufOrigins`, mit dessen Revision und einem vergleichenden
Quell-Digest. Ein gesonderter Entwurfsspeicher ist nicht erforderlich. Optionale
Namens-/Klartextänderungen sind ausdrücklich bezeichnet; andere Eagle-Felder
bleiben erhalten. Quelle/Zusatz müssen vor jeder Veröffentlichung erneut geprüft
sein. GET lädt den aktuellen gespeicherten Zusatz, PUT verweigert veraltete
Revision/Digest. Unvollständige typisierte Entwürfe können gespeichert werden,
blockierende mechanische Befunde verhindern weiterhin die Veröffentlichung.
Diese Konkretisierung gehört zum bestehenden P3-Entwurfsvertrag.
