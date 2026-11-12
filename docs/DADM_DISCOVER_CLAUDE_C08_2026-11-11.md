# Discover C08 – Compendium und bestehende Charakterentscheidungen

Status: Faktenaufnahme abgeschlossen, Apply erforderlich. Profil standard,
dauerhaft. R22–R24: erlaubte Inhalte zu berechtigter Figur, offene Stufen-/
Zauberwahl erreichbar; keine ungeklärten neuen Regelquellen.

`rules.py` bietet öffentliches SRD-Compendium und Detailblöcke. Das Frontend
regelwerk-compendium.js zeigt diese über eine Listen-/Detailansicht, hat keinen
Charakteraktionsweg. Die verbleibenden UI-Literale werden ausdrücklich schon
in C01 bearbeitet; C08 übernimmt dessen integrierte Grundlage.

`characters/srd_inventory.py` hat einen typisierten Katalog aus vorhandenen
Waffen, Rüstungen und Ausrüstungsgegenständen, inklusive Gewichten/Kosten und
Packauflösung. add_catalog_item erhöht vorhandene Mengen oder legt eine
InventoryItem-Zeile an; es ist nicht von sich aus retry-idempotent. Magische
Compendiumeinträge sind dadurch nicht automatisch mit allen Regelwirkungen
unterstützt. Creator-Katalog und Compendium-IDs müssen tatsächlich übereinstimmen.

`characters/srd_creator.py` hält Inventarschreiben beim Charakterowner. Leserechte
für Kampagnenfiguren verleihen keine Inventarschreibrechte. Fortschritt verwendet
DM/Co-DM für XP/Meilensteine einer Kampagne und Owner für Stufenaufstieg; außerhalb
Kampagnen verwaltet der Owner beides. level-up/preview gibt die serverberechneten
Choices zurück, level_up evaluiert den vollständigen Kandidatenzustand und
speichert nur gültige vollständige Ergebnisse. Zauber-/Talentlisten sind keine
frei hinzufügbaren generischen Spell-Zeilen für SRD-Charaktere.

Draftversion/CAS gilt für Creatorentwürfe. Für Inventaraktionen gibt es keinen
allgemeinen Charakter-Receiptvertrag außerhalb eines Tischkontexts. Die vorhandene
TableRequestReceipt setzt TableContext voraus und ist deshalb kein universeller
Compendium-Idempotenzspeicher. `_apply_inventory_change` committet und pusht danach
berechtigt zu verknüpften Tokens. Keine vorhandene globale Zauber-Sofortaufnahme
als nachgewiesenen Mechanismus annehmen.

Medium: Compendium darf Kampagnenleser oder DM nicht zu fremdem Inventarowner
machen; Medium: doppeltes Retry erhöht Mengen; Medium: direkte Zauber-/Talent-
Änderung würde Creatorlimits, Ursprungs-Pins oder Fortschrittsregeln umgehen.
Low: Link in den richtigen Bogenbereich fehlt bisher; UI-Zustand/Filter erhalten.

Nächster Schritt Apply: unterstützte Kataloggegenstände mit dauerhafter begrenzter
Idempotenz und Ownerprüfung; andere Typen zum vorhandenen geprüften Entscheidungs-
weg führen. Kein erfundener Slotdeckel, kein neues Regelsystem und keine Quellen-
oder Lizenzergänzung ohne Input.
