# Discover P3: veröffentlichte Hintergründe/Merkmale und Regelherkunft

status: abgeschlossen, immutable. Profil standard. input_summary: autorisiertes
Programm P3, vorhandener Eagle-Arbeitsplatz, SRD-Creator und P1/P2.
artifacts: dieser Befund, retention permanent.

Aktueller Zustand: Eagle wird als ausgeliefertes Bundle eingebunden; die genannten
Vendor-/Frontend-Quellverzeichnisse sind in diesem Checkout nicht vorhanden.
`creation_engine/routes.py`, `species_routes.py`, `species.py` und
`static/js/ce-species-publish.js` bieten eine bestehende Companion-Schnittstelle.
`CeSpeciesRevision` veröffentlicht unveränderliche Profile in personal/campaign/global.
`characters/species_catalog.py` prüft Zugriff bei Entwurf/Evaluate/Finalize/Rebuild;
`species_profiles.rules_data_for_block` verwendet für fertige Figuren eigene Pins.

Inventar: Hintergründe/Feats in `creator_data.py`; Herkunftsbonus, gewählte Feats,
RK-Formeln, Bewegung, Initiative, Saves, Skills, HP und Zauberwerte in
`creator_rules.evaluate`. Waffenangriffe/-schaden in `srd_inventory.attack_rows`.
Die Bogenanzeige ist inline in `templates/character-sheet.html`. Creator-Start
lädt veröffentlichte Spezies zusätzlich. Import löst Pins erneut serverseitig auf;
Kampagnenwechsel prüft kampagnengebundene Spezies. Diese Pfade gelten auch für
weitere Herkunftsarten. Hintergründe referenzieren SRD-Talente bisher per Name.

Abhängigkeiten: vorhandenes Flask/SQLAlchemy, kanonische JSON-Digests, Eagle-
Dokumentspeicher; keine neue externe Laufzeit erforderlich. Aktuelle Tisch-
Ausführung verwendet dieselbe Charakterauswertung und Inventarberechnung.

Risiken: medium – alte Images kennen neue Charakter-Pins nicht; Rückweg muss neue
Figuren weiterhin lesen können. medium – Freitext, Foundry-Advancements und Active
Effects sind nicht automatisch VTT-Regeln. medium – Auswahlrechte, unveränderliche
Fassungen, Import und Kampagnenwechsel müssen durchgehend zusammenpassen.
medium – separate Bonusberechnung könnte Würfe und Anzeige auseinanderführen.
low – konkrete vermisste Talent-/Unterklassen-IDs sind weiterhin nicht benannt.
Keine personenbezogenen Produktionsdaten für Katalogvergleich erforderlich.

Recherche: Die offiziellen [Foundry-Advancements](https://github.com/foundryvtt/dnd5e/wiki/Advancement)
unterscheiden Herkunftsboni, Item-/Trait-Grants und Skalenwerte. Der
[Active-Effect-Vertrag](https://github.com/foundryvtt/dnd5e/wiki/Active-Effect-Guide)
kennt eigene Formeln/Operationen; er ist keine Spezifikation dieses VTT-Evaluators.
Eine vollständige kompatible Foundry-Ausführung ist nicht Teil dieses Pakets.

Offene Fragen: I01 konkrete Inhaltslücke; blockiert nur deren Ergänzung. Nächster
Schritt: Apply legt unterstützte typisierte Grants, Pin-/Importvertrag,
Bonusnachweise und kompatiblen Datenrückweg fest.
