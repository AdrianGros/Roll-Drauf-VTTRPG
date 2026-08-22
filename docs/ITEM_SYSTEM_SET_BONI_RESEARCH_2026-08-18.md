
# Item-System und Set-Boni: Recherche, Lessons Learned und Zielarchitektur

**Projekt:** Roll Drauf VTT  
**Datum:** 2026-08-18  
**Status:** Discover / Apply – Forschungs- und Architekturbericht  
**Thema:** Größere Item-Vielfalt sowie echte Rüstungs-, Waffen-, Halsketten- und gemischte Item-Sets mit Set-Boni

## Executive Summary

Ein breiteres Item-System mit echten Set-Boni ist eine sehr gute nächste große Spielfunktion. Es kann Charaktere stärker individualisieren, Loot aufregender machen und Kampagnen mit langfristigen Zielen versehen.

Die großen Systeme zeigen aber auch die Risiken: Ein Set kann alle anderen Items verdrängen, ein fehlender Slot kann den gesamten Build blockieren, neue Sets können alte Ausrüstung überleben lassen und unklare Interaktionen können die Balance zerstören.

### Empfehlung für Roll Drauf

Wir sollten ein modulares, serverautoritäres Item-System bauen:

1. Item-Definition und konkrete Item-Instanz trennen.
2. Set-Boni über klare 2-/3-/4-Teil-Schwellen aktivieren.
3. Sets dürfen Spielweisen definieren, aber nicht die einzige sinnvolle Option sein.
4. Waffen und Halsketten dürfen echte Set-Teile sein, aber nicht jedes Rüstungsset blockieren.
5. Set-Teile über Sessions, Kampagnenziele, Quests, Crafting, Händler oder garantierten Fortschritt erreichbar machen.
6. Bad-Luck-Schutz von Anfang an einplanen.
7. Set-Effekte als kleine, kontrollierte Effect-DSL modellieren, nicht als beliebiges ausführbares JSON.
8. Im Character Sheet aktive Boni, fehlende Teile und den nächsten Erwerbsweg direkt erklären.
9. Zuerst ein kleines, gut testbares Set-System bauen – keine Diablo-III-Endgame-Multiplikatoren und keine WoW-ähnliche saisonale Item-Tretmühle.

Der empfohlene erste Content-Schnitt:

- 3 Core Sets mit jeweils 4 Teilen;
- 2 Signature Pairs aus Waffe + Halskette;
- 2-/3-/4-Teil-Boni;
- 9 echte Equipment-Slots;
- 3–5 kontrollierte Effekt-Typen;
- ein garantierter Set-Fortschritt;
- eine neue Gear-Ansicht im Character Sheet.

---

## 1. Lokaler Ist-Zustand

Aktuell existieren:

- [Equipment-Modell](/home/admin/projects/roll-drauf-vtt/vtt/models/equipment.py:7) als einfache, charaktergebundene Ausrüstung;
- [Inventory-Modell](/home/admin/projects/roll-drauf-vtt/vtt/models/inventory_item.py:7) für stapelbare Inventargegenstände;
- CRUD-Endpunkte in [den Character-Routen](/home/admin/projects/roll-drauf-vtt/vtt/characters/routes.py:1008);
- eine [einfache Equipment-/Inventory-Darstellung im Character Sheet](/home/admin/projects/roll-drauf-vtt/vtt/templates/character-sheet.html:1267);
- ein JSON-Feld für Special Properties;
- Rarity, AC-Bonus, Damage Dice, Damage Type, Equipped- und Cursed-Status.

Noch nicht vorhanden sind:

- feste Equipment-Slots;
- eine eindeutige Regel, wie viele Items je Slot ausgerüstet werden dürfen;
- globale Item-Definitionen;
- konkrete Item-Instanzen mit Herkunft, Rolls und Ownership;
- Set-Definitionen und Set-Teil-Zuordnungen;
- Set-Bonus-Schwellen;
- serverseitige Set-Berechnung;
- Derived-Stats-/Combat-Effect-Schicht;
- Set-Fortschritt und Bad-Luck-Schutz;
- Loadouts und belastbare Gear-Vergleiche.

Die aktuelle Struktur ist eine gute CRUD-Grundlage, aber noch kein echtes Loot-System. Deshalb sollten wir Sets nicht direkt in das bestehende Equipment-JSON hineinprogrammieren.

---

## 2. Diablo III: starke Identität, aber Set-Abhängigkeit

Diablo III nutzt klassenspezifische Sets mit mehreren Schwellen und sehr starken Skill-/Mechanik-Boni. Ein Set kann eine komplette Spielweise definieren:

- bestimmte Skills werden zum Build-Kern;
- Trigger erzeugen neue Rotationen;
- offensive und defensive Effekte werden zusammengeführt;
- andere Items werden als Set-Support gewählt.

Blizzard hat Sets mehrfach komplett neu entworfen und auch Waffen-/Schild- oder Schmuck-Sets ergänzt. In Patch 2.2 wird ausdrücklich erklärt, dass Set-Items besonders behandelt werden, weil eine Änderung an einem Set Spieler mit dem alten Set sonst zum Neustart zwingen kann. [Blizzard: Patch 2.2.0](https://news.blizzard.com/en-us/article/18642492/patch-2-2-0-now-live)

### Gute Ideen aus Diablo III

- Ein Set vermittelt eine starke Fantasy.
- Der Spieler versteht, welche Spielweise ein Set unterstützt.
- Zwischen-Schwellen machen Fortschritt sichtbar.
- Einzelne Nicht-Set-Items können gezielte Synergien ergänzen.
- Mehrere Builds rechtfertigen Build-Swapping und Loadouts.

### Die teuren Lektionen

#### Set-Abhängigkeit

Wenn der wesentliche Power-Schub erst am Ende eines 6-Teil-Sets kommt, fühlt sich ein Charakter ohne dieses Set unfertig an. Das Loot-System liefert dann nicht viele Optionen, sondern hauptsächlich Teile eines Pflichtsets.

#### Power-Creep

Sehr große multiplikative Set-Boni zwingen neue Inhalte dazu, immer stärker zu werden. Die gesamte Zahlenskala wächst und Balance wird zunehmend teuer.

Das Diablo-III-Team beschreibt seine datengetriebene Build-Balance und erklärt, dass eine immer weiter steigende Greater-Rift-Skala nicht die gesündeste Endgame-Lösung war. [Blizzard: Balancing & Class Set Design](https://news.blizzard.com/en-us/article/23290575/d3-developer-insights-balancing-class-set-design)

#### Unvorhersehbare Interaktionen

Sets, Skills, Animationen, Snapshotting und andere Item-Powers können sich unerwartet multiplizieren. Blizzard nennt selbst problematische Spielweisen, die Balanceänderungen erschwerten und bei Korrekturen ganze Klassen gefährden konnten. [Blizzard: Balancing & Class Set Design](https://news.blizzard.com/en-us/article/23290575/d3-developer-insights-balancing-class-set-design)

#### Nicht-Set-Builds sind notwendig

Legacy of Nightmares gab Spielern bewusst eine starke „No Set“-Alternative. Das war die Gegenbewegung zur wachsenden Set-Abhängigkeit. [Blizzard: Season 17 – Legacy of Nightmares](https://news.blizzard.com/en-gb/article/22976066/season-17-the-season-of-nightmares-is-now-live)

### Konsequenz für uns

Ein Set darf ein Build definieren. Es darf aber nicht die einzige plausible Form sein, eine Rolle oder einen Archetyp sinnvoll zu spielen.

---

## 3. Diablo IV: Item-Identität ohne Pflichtset

Diablo IV formulierte bewusst, dass Legendary-Items mindestens so mächtig wie Sets sein können sollen, damit Spieler nicht an ein bestimmtes Klassenset gebunden sind. [Blizzard: Diablo IV Feature Overview](https://news.blizzard.com/en-us/article/23189677/diablo-iv-feature-overview)

Die Build-Definition verteilt sich stärker auf:

- Legendary Aspects;
- Unique Items;
- Affixe;
- Tempering;
- Masterworking;
- Skill- und Paragon-Synergien.

Die Itemization-Überarbeitung reduzierte die Zahl der Affixe und verschob Komplexität in gezieltes Crafting. Dadurch sollten Drops leichter als Upgrades bewertet werden können. [Blizzard: Loot Reborn](https://news.blizzard.com/en-us/article/24077223/galvanize-your-legend-in-season-4-loot-reborn)

### Was wir übernehmen

Jeder Archetyp sollte drei valide Pfade haben:

1. Set-Build;
2. Relikt-/Unique-Build;
3. freie Einzelitem-Kombination.

Sets sollen vor allem Spielweisen verständlich machen. Sie sollten nicht automatisch die höchste mathematische Leistung liefern.

---

## 4. World of Warcraft: klare Schwellen, Erwerbsprobleme, Catalyst

WoW nutzt klassenspezifische Tier-Sets mit einfachen Schwellen. Die moderne Grundform ist häufig:

~~~
2 Teile -> Kernverstärkung oder Rotationserleichterung
4 Teile -> deutlicher Spielstil- oder Synergiebonus
~~~

Die offiziellen Dragonflight-Dokumente beschreiben Set-Erwerb über Raid, Great Vault und Catalyst. [Blizzard: Dragonflight Season 1](https://worldofwarcraft.blizzard.com/en-us/news/23892221)

### Gute Ideen aus WoW

- 2 Teile geben früh ein Erfolgserlebnis.
- 4 Teile bilden ein klares mittelfristiges Ziel.
- Boni sind auf konkrete Spielweisen fokussiert.
- Mehrere Content-Arten können auf dasselbe Set einzahlen.
- Set-Fortschritt ist im Charakter-UI sichtbar.

### Harte Lektion: ein fehlender Slot

Wenn ein Set nur aus bestimmten Bossen oder Slots kommt, kann ein Spieler lange an einem einzigen Teil scheitern. WoW hat deshalb mehrere Schutzmechanismen aufgebaut:

- Set-Teile aus mehreren Content-Arten;
- wöchentliche Auswahl über den Great Vault;
- Umwandlung passender Nicht-Set-Items über den Catalyst;
- Aufholmechaniken für spätere oder alternative Charaktere.

Blizzard nennt Raid, Great Vault und Catalyst ausdrücklich als parallele Wege. [Blizzard: Shadowlands Class Set Preview](https://worldofwarcraft.blizzard.com/en-gb/news/23778646/shadowlands-eternitys-end-class-set-preview)

Später wurde der Catalyst weiter angepasst, damit Set-Boni schneller oder mindestens gleich schnell erreichbar sind und Nicht-Raid-Spieler nicht unnötig zurückfallen. [Blizzard: Guardians of the Dream](https://worldofwarcraft.blizzard.com/en-gb/news/24020034/updated-8-november-dragonflight-guardians-of-the-dream-content-update-notes-now-live)

### Harte Lektion: alte Sets verdrängen neue Items

Ein neues Set muss nicht nur stärker sein. Es muss neue Entscheidungen eröffnen. Blizzard musste mehrfach alte Boni reduzieren, neue Boni verstärken oder Basisskills buffen, weil ältere Sets neue Gegenstände unattraktiv machten. [Blizzard: Hotfixes April 2025](https://worldofwarcraft.blizzard.com/en-us/news/24179333/hotfixes-april-28-2025)

### Harte Lektion: Synergien sind systemweit

WoW-Hotfixes zeigen Korrekturen für zu starke Set-Boni, Talentinteraktionen, AoE, Ressourcen- und Cooldown-Schleifen sowie PvP-Probleme. [Blizzard: WoW Hotfixes May 27, 2022](https://worldofwarcraft.blizzard.com/en-us/news/23770463)

### Konsequenz für uns

Set-Boni müssen zusammen mit Skills, Rollen, Encounter-Länge, Gruppe, Solo und PvP getestet werden. Eine einzelne Item-Tabelle reicht nicht.

---

## 5. Vergleich und übertragene Entscheidungen

| Thema | Diablo III | Diablo IV | WoW | Roll-Drauf-Entscheidung |
|---|---|---|---|---|
| Set-Stärke | stark build-definierend | Sets nicht als einzige Lösung | klare Klassen-/Spec-Synergien | Sets definieren Spielweisen, nicht den gesamten Power-Balken |
| Schwellen | mehrere, teils sehr große Boni | modulare Einzelitems | meist 2 und 4 Teile | MVP: 2/3/4 Teile |
| Erwerb | Farm-/RNG-orientiert | Crafting und gezielte Pflege | Raid, Vault, Catalyst | mehrere Quellen plus garantierter Fortschritt |
| Nicht-Set | Legacy of Nightmares | Legendary/Unique/Aspect | situativ relevant | freie Alternativen pro Archetyp |
| Komplexität | hohe Kombinationszahl | mehr Komplexität im Crafting | viele Spec-/Season-Interaktionen | kleine kontrollierte Effect-DSL |
| Balance | Multiplikatoren und Power-Creep | Einzelitem-Identität | Saisonübergänge | Power-Budget und Versionierung |
| Waffen/Schmuck | eigene Sets möglich | Unique-Items definieren Slots | Tier-Sets primär Rüstung | Waffen/Necklace als Signature-Sets |
| Verwaltung | Armory wichtig | Build-Anpassung zentral | Loadouts wertvoll | Loadout-Architektur früh vorsehen |

---

## 6. Ziel für Roll Drauf

Roll Drauf ist nicht einfach Diablo und nicht einfach WoW. Es hat:

- DM-geführte Sessions;
- kampagnenspezifische Geschichten;
- D&D-/VTT-Charaktere;
- potenziell eine MMO-Meta-Schicht;
- unterschiedliche Kampagnen- und Sitzungsrhythmen;
- DM-kontrollierte Belohnungen;
- Spieler, die nur gelegentlich teilnehmen.

Daraus folgt:

> Item-Sets müssen sowohl mechanische Build-Ziele als auch erzählerische Belohnungen sein.

Ein DM sollte ein Relikt-Set als Storyline vergeben können, ohne dass der Spieler einen anonymen Raid-Grind braucht. Gleichzeitig dürfen Kampagnen-Sets außerhalb einer Geschichte nicht wertlos werden.

---

## 7. Item-Taxonomie

| Kategorie | Zweck | Beispiel |
|---|---|---|
| Basic Gear | verlässliche Grundausrüstung | Eisenklinge, Reisemantel |
| Magic Item | einzelner nützlicher Effekt | Ring mit Feuerresistenz |
| Named Relic | starke individuelle Identität | Auge des Nebelwächters |
| Core Set Piece | Teil eines 3-/4-teiligen Builds | Brust des Sternenwächters |
| Signature Pair | 2-teilige Cross-Slot-Synergie | Mondklinge + Mondamulett |
| Campaign Reward | erzählerische Belohnung | Siegel von Solaris |
| Consumable/Material | Verbrauch und Crafting | Heiltrank, Runenstaub |

Inventory- und Equipment-Items sollten zunächst getrennt bleiben. Verbrauchs- und Stack-Regeln sind andere als bei ausrüstbaren Instanzen.

### Equipment-Slots

Ein sinnvolles Grundmodell:

~~~
head, shoulders, chest, hands, waist, legs, feet, cloak,
main_hand, off_hand, neck, ring_1, ring_2
~~~

Nicht jeder Slot muss sofort umfangreich befüllt werden. Wichtig ist die echte, serverseitig validierte Slot-Identität.

### Waffen und Halsketten

- **Signature Pair:** Waffe + Halskette bilden eine 2-teilige Synergie.
- **Weapon Anchor:** Waffe plus zwei Rüstungsteile bilden ein 3-teiliges Set.
- **Necklace Catalyst:** Halskette verändert einen Set-Effekt, ersetzt aber nicht alle anderen Boni.
- **Mixed Set:** Teile können aus Rüstung, Waffe und Necklace kommen.

### Regel gegen Slot-Zwang

- Core Sets: primär Rüstung, 3–4 Teile;
- Signature Sets: 2 Teile, häufig Waffe + Halskette oder Waffe + Offhand;
- Hybrid Sets: maximal 4 Teile über definierte Slotgruppen;
- keine 8- oder 10-teiligen Pflichtsets im ersten Release.

---

## 8. Set-Bonus-Design

### Empfohlene Schwellen

~~~
2 Teile -> Kernmechanik oder Qualitätsverbesserung
3 Teile -> Spielschleife / stärkere Synergie
4 Teile -> Set-Identität / Capstone-Effekt
~~~

Das ist für ein VTT sinnvoller als ein einziges großes 6-Teil-Ziel: Kampagnen laufen unregelmäßig, Zwischenfortschritt bleibt wertvoll und ein Charakter wirkt nicht erst mit dem letzten Teil fertig.

### Rollen der Boni

- **2 Teile:** Komfort oder Identität, zum Beispiel zuverlässigere Ressource, defensiver Trigger, andere Reichweite oder zusätzliche taktische Option.
- **3 Teile:** Spielschleife, zum Beispiel Markierung → Ladung → Folgeaktion oder Schutzaktion → Gruppenreaktion.
- **4 Teile:** klarer Capstone-Effekt, begrenzter Support-Effekt oder neuer taktischer Entscheidungspunkt.

### Was ein Set nicht alles können darf

Ein Set sollte nicht gleichzeitig maximalen Schaden, maximale Verteidigung, Ressourcenlösung, Mobilität, Gruppenunterstützung und einen neuen Skill liefern. Das wäre ein Ersatz für mehrere Systeme.

### Effect-DSL für den MVP

~~~
modify_stat
modify_skill
grant_trigger
grant_resource
grant_defense_window
modify_cooldown
modify_range
modify_targeting
grant_passive_tag
~~~

Jeder Effekt braucht:

- einen eindeutigen Typ;
- validierte Parameter;
- Serverberechnung;
- Tooltip-Text;
- Aktivierungsbedingung;
- Testfall;
- PvE-/PvP-Regel, falls relevant.

Keine freie Codeausführung, keine unbeschränkten Formeln und keine uneingeschränkte clientseitige JSON-Interpretation.

### Additiv vor multiplikativ

Im ersten Release sollten Effekte bevorzugt additive Werte, begrenzte Trigger, Cooldowns, feste Ladungen und kurze Buff-Fenster verwenden. Große Multiplikatoren wie „+1000 % Schaden“ sind schwer zu balancieren und ziehen weitere Multiplikatoren an.

---

## 9. Drei Set-Familien

### Archetype Sets

Sets unterstützen eine Spielweise, aber keine starre Klasse:

- Wächter des letzten Tores: Schutz, Reaktion, Position halten;
- Jäger des offenen Himmels: Bewegung, Markierung, Fernkampf;
- Chronist der hundert Wege: Vorbereitung, Wissen, flexible Skillwahl;
- Blutpakt: riskante Ressourcenverwaltung.

### Campaign Relic Sets

Diese Sets werden über eine Kampagne oder Questline aufgebaut:

~~~
Fragment 1 -> erster Story-Meilenstein
Fragment 2 -> Schlüssel-Session
Fragment 3 -> optionales schweres Ziel
~~~

Der Set-Bonus kann narrativ geprägt sein und muss nicht zufällig droppen.

### Signature Pairs

Diese Sets bestehen aus zwei verbundenen Items:

- Waffe + Halskette;
- Waffe + Offhand;
- Ring + Halskette;
- Relikt + Rüstungsteil.

Sie liefern die gewünschte Waffen-/Necklace-Identität, ohne sechs Slots zu blockieren.

---

## 10. Erwerb, Loot und Bad-Luck-Schutz

### Grundregel

Ein Set darf selten sein. Ein einzelnes benötigtes Teil darf aber nicht dauerhaft unkontrollierbar sein.

Spieler müssen wissen:

- wo ein Set grundsätzlich herkommt;
- welcher Slot fehlt;
- welche Aktivitäten Fortschritt geben;
- ob ein Teil gezielt verdient, hergestellt oder getauscht werden kann;
- wie ein realistischer Weg ungefähr aussieht.

### Mehrere Erwerbswege

Für jedes wichtige Set sollten mindestens zwei Wege existieren:

| Weg | Funktion |
|---|---|
| Session Reward | belohnt Teilnahme und DM-geführte Aktivität |
| Campaign Milestone | garantiert Story-Fortschritt |
| Quest/Encounter | optionales Ziel und Herausforderung |
| Crafting/Upgrade | schützt vor schlechtem RNG |
| Händler/Token | gezielter Slot nach Fortschritt |
| World-/Faction-Reward | bindet Sets an MMO-/Gildenebene |

Die Quellen dürfen thematisch und kampagnenspezifisch sein. Der Spieler braucht aber einen planbaren Ausweg.

### Set-Fortschrittswährung

Ein Fortschrittssystem ist besser als reines Drop-RNG:

~~~
Set-Essenz / Reliktfragmente / Siegel
~~~

Nach ausreichendem Fortschritt kann der Spieler:

- einen fehlenden Slot auswählen;
- ein passendes Basisitem umwandeln;
- ein Duplikat in einen fehlenden Set-Slot konvertieren;
- ein Set-Teil upgraden.

Spielzeit darf sich nicht wertlos anfühlen, nur weil der falsche Slot gefallen ist.

### VTT-spezifische Rewards

Ein Session-Reward sollte aus drei Schichten bestehen:

1. **Garantierter Fortschritt:** Essenz, Fragment oder Upgrade-Material;
2. **Themenloot:** Items aus Kampagne, Zone oder Begegnung;
3. **Chance auf besonderes Item:** Relikt, Signature Piece oder kosmetische Variante.

So fühlt sich jede Session lohnend an, ohne jeden Durchlauf mit einem starken Item zu überladen.

---

## 11. Item-Power und Progression

### Rarität ist nicht gleich Set-Stärke

Die bestehende Rarity-Liste sollte nicht automatisch bestimmen, ob ein Item in einem Set gut ist. Zu trennen sind:

- Rarity: Sichtbarkeit, Seltenheit und Fantasy;
- Item Power: numerische Stärke im Progressionsband;
- Set Role: Set-Teil oder freies Item;
- Upgrade State: Verbesserung und Qualität;
- Story Value: narrative Bedeutung.

### Keine frühe endlose Zahlen-Spirale

Roll Drauf sollte anfangs keine dauerhafte Diablo-/WoW-Item-Power-Spirale bauen. Das Spiel braucht zuerst:

- verständliches Charakter-Level;
- begrenzten Item-Power-Bereich;
- sinnvolle Upgrades;
- stabile Set-Identität;
- klare Beziehung zu Sessions und Kampagnen.

### Upgrade statt vollständiger Ersatz

Ein Item sollte seine Identität behalten können:

~~~
Mondklinge
Basis: 1d8
Upgrade I: zusätzliche Markierungsoption
Upgrade II: besserer Trigger
Upgrade III: Set-Signature aktiviert
~~~

Das ist für DM-geführte Kampagnen besser als viele ähnliche Schwerter, die nur anhand eines Power Scores sortiert werden.

---

## 12. Datenmodell

### Warum das bestehende JSON nicht reicht

Ein JSON-Feld kann flexible Effect-Payloads tragen. Es sollte aber nicht die komplette Semantik für Slots, Set-Zuordnung, Trigger, Upgrade-Level und Ownership tragen.

Sonst entstehen:

- schwer validierbare Daten;
- schwer abfragbare Set-Fortschritte;
- unklare Migrationen;
- keine gute Content-UI;
- unzuverlässige Balance-Reports;
- schwierige serverseitige Berechnung;
- fehleranfällige Berechtigungen.

### Empfohlene Schichten

~~~
ItemDefinition
  globale Vorlage: Name, Slot, Rarity, Basiswerte, Beschreibung

ItemInstance
  konkretes Exemplar: Owner, Campaign, Rolls, Upgrade, Binding, State

CharacterEquipment
  welcher ItemInstance-Slot ist ausgerüstet

ItemSetDefinition
  Set-Familie, Fantasy, Aktivierungsregeln

ItemSetPiece
  welches Item oder welche Definition gehört zum Set

ItemSetBonus
  Schwelle, Effekt-Typ, Parameter, Tooltip, Version

SetProgress
  Fragmente, Milestones, gezielter Fortschritt
~~~

### Möglicher Tabellenkern

~~~
item_definitions
  id, key, name, description, item_type, equipment_slot
  rarity, required_level, base_stats_json, effect_tags_json
  is_unique, is_tradeable, is_active

item_instances
  id, definition_id, character_id, campaign_id
  source_type, source_id, upgrade_level, rolled_stats_json
  binding_state, is_destroyed, created_at

item_set_definitions
  id, key, name, description, set_type
  max_active_pieces, active_from, active_until, version

item_set_pieces
  set_id, item_definition_id, slot_group, piece_role

item_set_bonuses
  id, set_id, pieces_required, effect_type
  effect_payload_json, display_text, version

character_equipment
  character_id, equipment_slot, item_instance_id, equipped_at
~~~

### Migration der bestehenden Equipment-Zeilen

Bestehende Equipment-Einträge sollten nicht gelöscht werden:

1. Für jeden bestehenden Equipment-Namen eine Legacy-Definition erzeugen.
2. Jede bestehende Zeile in eine ItemInstance überführen.
3. Equipped-Status über einen validierten Slotzustand ersetzen.
4. Special Properties als Legacy-/Effect-Payload übernehmen.
5. Alte API-Felder zunächst weiter serialisieren.
6. Neue Item-/Set-API schrittweise als kanonische Quelle etablieren.

Inventory-Items können zunächst separat bleiben, weil Verbrauchs- und Stack-Regeln andere sind.

### Slot-Validierung

Der Server muss erzwingen:

- maximal ein Item je Equipment-Slot;
- Zweihandwaffe und Offhand-Regeln;
- getrennte Ring-Slots, falls zwei Ringe erlaubt sind;
- Halskette als eigener Slot;
- kompatibler Item-Typ je Slot;
- Set-Zählung nur aus gültigen Equipped-Instanzen;
- Ownership und Campaign-Scope.

### Serverautoritäre Set-Berechnung

~~~
equipped item instances
  -> ownership and slot state validieren
  -> item definitions auflösen
  -> set memberships sammeln
  -> Teile pro Set zählen
  -> Schwellen auflösen
  -> Whitelist-Effekte anwenden
  -> Derived State erzeugen
  -> Boni und Erklärungen serialisieren
~~~

Die API sollte nicht nur Endwerte liefern, sondern auch die Herkunft:

~~~json
{
  "active_set_bonuses": [
    {
      "set_key": "moon_guardians",
      "pieces_equipped": 3,
      "threshold": 3,
      "name": "Lunarer Rhythmus",
      "description": "Markierte Ziele erzeugen beim Treffer eine Mondladung.",
      "source_item_ids": [101, 104, 109]
    }
  ]
}
~~~

Das ist für UI, Debugging, Support und Balance wichtig.

---

## 13. Character-Sheet-UI

Die aktuelle einfache Equipment-Liste reicht für Set-Boni nicht mehr. Ziel sollte ein Slot Grid mit aktivem Set-Panel sein:

~~~
┌──────────────────────────────────────────────┐
│ Charaktername · Level · aktiver Build        │
├───────────────┬──────────────────────────────┤
│ Slot Grid      │ Aktive Sets                  │
│ [Head]         │ Wächter des Tores 3/4        │
│ [Chest]        │ ✓ 2er-Bonus                  │
│ [Weapon]       │ ✓ 3er-Bonus                  │
│ [Neck]         │ □ 4er-Bonus – Brust fehlt   │
│ [Ring] [Ring]  │                              │
├───────────────┴──────────────────────────────┤
│ Item-Details / Vergleich / nächste Aktion    │
└──────────────────────────────────────────────┘
~~~

Bei jedem Set sichtbar:

- Name und Fantasy;
- 2/4, 3/4 oder 4/4 Fortschritt;
- aktive Boni;
- noch fehlende Teile;
- Quelle oder nächster Erwerbsweg;
- Vorher-/Nachher-Vorschau;
- Konflikte mit anderen aktiven Sets;
- Slot und Upgrade;
- Rollen-/Klassenkompatibilität, falls relevant.

### Item-Vergleich

Beim Auswählen eines Items:

- aktuelles und neues Item nebeneinander;
- Basiswerte;
- Setfortschritt vorher/nachher;
- aktive Boni vorher/nachher;
- Warnung bei Verlust eines höheren Set-Bonus;
- klare, aber nicht undurchsichtige Empfehlung.

### Loadouts

Sobald mehrere Setpfade existieren, werden Loadouts wichtig. Diablo III stellte dafür ein Armory-System bereit, weil vollständige Builds sonst zu mühsam manuell gewechselt werden. [Blizzard: Diablo III Armory](https://news.blizzard.com/en-gb/article/20597130/first-look-patch-2-5-0)

Für Roll Drauf:

- Loadout-Architektur früh berücksichtigen;
- automatische Wechsel erst nach stabilen Slot- und Set-Regeln;
- Instanz-Referenzen speichern, keine Item-Kopien;
- fehlende Items verständlich anzeigen.

---

## 14. Balance- und Content-Workflow

### Jedes Set braucht ein Design-Briefing

~~~
Setname:
Fantasy:
Ziel-Spielweise:
Zielgruppe:
Primäre Slots:
Alternative Slots:
2er-Bonus:
3er-Bonus:
4er-Bonus:
Nicht-Ziel:
Stärkste erwartete Synergie:
Bekannte Konter:
Erwerbswege:
PvE-Regel:
PvP-Regel:
Testfälle:
~~~

### Set-Budget

Jedes Set erhält ein Budget in drei Dimensionen:

- Base Power: Basiswerte der Items;
- Build Power: Mechanik und Skill-Synergie;
- Flexibility Cost: geopferte Slots und Alternativen.

Ein Set mit hoher Build Power muss Flexibility Cost besitzen. Ein Set über Waffe, Halskette und Rüstung darf nicht gleichzeitig in jedem Slot die besten Basiswerte besitzen.

### Testmatrix

Jedes Set muss geprüft werden gegen:

- Solo und Gruppe;
- Damage, Defense und Support;
- Single Target und Area of Effect;
- kurze und lange Kämpfe;
- niedrige und hohe Charakterstufen;
- frischen Charakter und optimiertes Endgame;
- Nicht-Set-Ausrüstung;
- anderes Set;
- Item-Upgrade;
- PvP, falls vorhanden;
- atypische, aber erlaubte Skill-Kombinationen.

### Telemetrie

Relevant sind:

- Nutzung eines Sets;
- Erreichen der 2er-, 3er- und 4er-Schwelle;
- Zeit bis zum ersten Fortschritt;
- am häufigsten fehlender Slot;
- Abbruchrate eines Setpfads;
- Nutzung von Nicht-Set-Alternativen;
- Gruppen-/Solo-Unterschiede;
- Verdrängung älterer Items.

---

## 15. Harte Lessons Learned als Regeln

| Harte Erfahrung | Smart Decision für Roll Drauf |
|---|---|
| Ein zu starkes Set wird Pflicht | Nicht-Set-Alternative pro Archetyp |
| Fehlender Slot blockiert den Build | 2-/3-Teil-Boni und garantierter Fortschritt |
| Alte Sets verdrängen neue Items | Upgrade-/Ablöseplan und Versionierung |
| Große Multiplikatoren erzeugen Power-Creep | additive/whitelistete Effekte |
| Set-Synergien brechen an Skills und AoE | Testmatrix vor Content-Release |
| Loot-RNG erzeugt Frust | mehrere Quellen, Tokens und Konversion |
| Drops sind schwer zu bewerten | klare Werte und Vorher-/Nachher-Vorschau |
| Viele Builds erzeugen Verwaltungsarbeit | Loadout-Architektur früh vorsehen |
| Neue Spieler und Alts fallen zurück | Catch-up und garantierter Fortschritt |
| Raid-Drop passt nicht zu allen Spielern | Session-, Quest-, Crafting- und Händlerpfade |
| Sonderlogik wird unwartbar | kleine Effect-DSL |
| Boni schaukeln sich mit Skills auf | zentrale Derived-Stats-Berechnung |

---

## 16. MVP und Rollout

### MVP

- 10–15 Item-Definitions;
- 3 Core Sets mit jeweils 4 Teilen;
- 2 Signature Pairs aus Waffe + Halskette;
- 9 Equipment-Slots;
- 2-/3-/4-Teil-Boni;
- 2–3 Effect-Typen;
- Equip/Unequip mit Slotvalidierung;
- aktive Set-Boni im Character Sheet;
- garantierter Session-Fortschritt;
- Set-Essenz oder Konversion;
- serverseitige Set-Berechnung;
- Tests für Slots, Sets und Ownership.

### Nicht in den MVP

- zufällige Rolls auf jedem Affix;
- komplettes Diablo-IV-Crafting;
- sechs oder mehr unabhängige Setfamilien pro Charakter;
- undurchsichtiger automatischer Buildscore;
- frei programmierbare DM-Scripts;
- globale Auktion;
- vierstellige Prozentmultiplikatoren;
- saisonal vollständig entwertete Items;
- komplette MMO-Loot-Tabellen vor Stabilisierung des Fundaments.

### Phasen

#### Phase 0 – Vertrag

Slots, Item-Typen, Ownership, PvE/PvP-Regeln, Effect-DSL und Migration festlegen.

#### Phase 1 – Fundament

ItemDefinition, ItemInstance, Slotvalidierung, equip/unequip, Migration und neue Gear-UI-Grundstruktur.

#### Phase 2 – Einzelitem-Identität

Named Items, Upgrade-Level, Herkunft, Campaign-Scope, Item-Vergleich und Derived Stats.

#### Phase 3 – Set-Engine

SetDefinition, SetPiece, SetBonus, 2-/3-/4-Teil-Zählung, Whitelist-Effekte und Tests.

#### Phase 4 – Erwerb

Session-Reward, Set-Essenz, fehlenden Slot auswählen, Milestones, später Händler-/Crafting-Konversion.

#### Phase 5 – UX

Slot Grid, active-set panel, fehlende Teile, Vorher-/Nachher-Vorschau, Filter und Loadouts.

#### Phase 6 – Content

Kampagnen-Relikte, Gilden-/Faction-Sets, MMO-/Encounter-Sets sowie weitere Waffen- und Halsketten-Signatures.

---

## 17. API- und Schnittstellenempfehlung

~~~
GET  /api/characters/{id}/equipment
GET  /api/characters/{id}/equipment/summary
POST /api/characters/{id}/equipment/{instance_id}/equip
POST /api/characters/{id}/equipment/{instance_id}/unequip
GET  /api/characters/{id}/loadouts
POST /api/characters/{id}/loadouts
PUT  /api/characters/{id}/loadouts/{loadout_id}

GET  /api/items/catalog
GET  /api/items/{definition_key}
GET  /api/item-sets
GET  /api/item-sets/{set_key}
GET  /api/characters/{id}/set-progress
POST /api/characters/{id}/set-progress/convert
~~~

Die Schnittstellen sollten klar zwischen Katalog/Definition, konkreter Instanz, Ausrüsten, Set-Status und Fortschritt/Konversion trennen.

---

## 18. Tests und Akzeptanzkriterien

### Backend

- nur gültige Slots können besetzt werden;
- Main-Hand-/Off-Hand-/Zweihand-Regeln sind serverseitig;
- eine Item-Instanz kann nicht zwei Charakteren gehören;
- Sets zählen nur gültige Equipped-Instanzen;
- 2-/3-/4-Teil-Schwellen funktionieren;
- Unequip entfernt nur betroffene Boni;
- Set-Quellen werden serialisiert;
- Ownership und Campaign-Scope werden geprüft;
- ungültige Effect-Payloads werden abgelehnt;
- Legacy-Equipment bleibt lesbar;
- falsche Drops liefern trotzdem Fortschritt.

### UI

- Slot Grid zeigt leer/belegt verständlich;
- aktive Boni sind ohne Hover auffindbar;
- fehlender nächster Slot ist sichtbar;
- Waffe + Halskette wird als Signature Pair erkannt;
- Anlege-Vorschau zeigt Gewinn und Verlust;
- Setkonflikte werden erklärt;
- Mobile und Tastatur funktionieren;
- Settext wird nicht nur über Farbe vermittelt.

### Balance

- mindestens eine spielbare Nicht-Set-Alternative pro Archetyp;
- kein Set ist in allen Content-Arten eindeutig optimal;
- kein einzelner zufälliger Slot ohne Schutzmechanismus;
- 2er-Bonus ist attraktiv, aber kein kompletter Build;
- 4er-Bonus verändert die Spielweise, nicht nur DPS;
- keine permanente Ressourcen-/Cooldown-Schleife;
- jede Session liefert Fortschritt;
- neue Sets verdrängen alte nicht nur über größere Zahlen.

---

## 19. Offene Produktentscheidungen

Vor dem ersten Schema-Migrationscode müssen wir entscheiden:

1. Sind Items global, kampagnenspezifisch oder beides?
2. Darf ein Item zwischen Charakteren oder Kampagnen gehandelt werden?
3. Sind Set-Boni klassen-, archetypen- oder frei definiert?
4. Gibt es PvP und braucht es separate Set-Skalierung?
5. Welche Slots existieren im ersten Release?
6. Wie funktionieren Zweihandwaffen und Offhand?
7. Wie stark darf ein 2-/3-/4-Teil-Bonus relativ zu Basiswerten sein?
8. Welche Session-Events erzeugen Set-Fortschritt?
9. Wer darf Campaign Relic Sets erstellen?
10. Wie werden Items nach Balanceänderungen versioniert?
11. Gibt es Bind-on-Pickup, Bind-on-Equip oder freie Übergabe?
12. Wie werden archivierte oder zurückgezogene Items behandelt?

---

## 20. Finale Empfehlung

Wir sollten das Item-System nicht als „mehr Items in die bestehende Equipment-Tabelle“ umsetzen. Das würde kurzfristig schnell aussehen, aber mittelfristig genau die Probleme erzeugen, die Diablo und WoW über Jahre nachbessern mussten.

Die sinnvolle Reihenfolge lautet:

~~~
Slots und Ownership
  -> ItemDefinition / ItemInstance
  -> serverseitige Derived Stats
  -> einzelne Named Items
  -> Set-Definitionen und 2/3/4-Schwellen
  -> garantierter Set-Fortschritt
  -> UI-Vergleich und Loadouts
  -> größere Content-Bibliothek
~~~

Die konkrete Designform sollte lauten:

- **WoW-Klarheit:** wenige, gut erkennbare Schwellen;
- **WoW-Erwerbsschutz:** mehrere Quellen, Conversion und Bad-Luck-Schutz;
- **Diablo-Identität:** Items und Sets verändern Spielweisen, nicht nur Zahlen;
- **Diablo-Freiheit:** Nicht-Set- und Relikt-Builds bleiben gültig;
- **Roll-Drauf-Fit:** DM-Sessions und Kampagnen liefern planbaren Fortschritt;
- **Roll-Drauf-Sicherheit:** Effekte sind serverautoritär, typisiert und testbar;
- **Roll-Drauf-UX:** Setstatus, fehlende Teile und Upgrade-Konsequenzen sind sofort sichtbar.

### Erster Content-Schnitt

~~~
3 Core Sets × 4 Teile
2 Signature Pairs aus Waffe + Halskette
2-/3-/4-Teil-Boni
1 Set-Fortschritts-/Konversionsmechanik
9 echte Equipment-Slots
3–5 Effect-Typen maximal
1 Character-Sheet-Gear-Ansicht
1 Session-Reward-Pipeline
~~~

So bekommen die Nutzer echte Waffen-/Rüstungs-/Halsketten-Sets, ohne sofort ein unkontrollierbares ARPG-Loot-System zu bauen.

---

## 21. Quellen

### Diablo

- [Blizzard – Diablo III Patch 2.2.0](https://news.blizzard.com/en-us/article/18642492/patch-2-2-0-now-live)
- [Blizzard – Diablo III Developer Insights: Balancing & Class Set Design](https://news.blizzard.com/en-us/article/23290575/d3-developer-insights-balancing-class-set-design)
- [Blizzard – Diablo III Season 17: Legacy of Nightmares](https://news.blizzard.com/en-gb/article/22976066/season-17-the-season-of-nightmares-is-now-live)
- [Blizzard – Diablo IV Feature Overview](https://news.blizzard.com/en-us/article/23189677/diablo-iv-feature-overview)
- [Blizzard – Diablo IV Loot Reborn](https://news.blizzard.com/en-us/article/24077223/galvanize-your-legend-in-season-4-loot-reborn)
- [Blizzard – Diablo III Armory](https://news.blizzard.com/en-gb/article/20597130/first-look-patch-2-5-0)

### World of Warcraft

- [Blizzard – Shadowlands Class Set Preview](https://worldofwarcraft.blizzard.com/en-gb/news/23778646/shadowlands-eternitys-end-class-set-preview)
- [Blizzard – Dragonflight Season 1 Class Sets](https://worldofwarcraft.blizzard.com/en-us/news/23892221)
- [Blizzard – Dragonflight: Guardians of the Dream](https://worldofwarcraft.blizzard.com/en-gb/news/24020034/updated-8-november-dragonflight-guardians-of-the-dream-content-update-notes-now-live)
- [Blizzard – Dragonflight: Fractures in Time](https://worldofwarcraft.blizzard.com/en-gb/news/23968772/updated-july-11-dragonflight-fractures-in-time-content-update-notes)
- [Blizzard – WoW Hotfixes April 2025](https://worldofwarcraft.blizzard.com/en-us/news/24179333/hotfixes-april-28-2025)
- [Blizzard – WoW Hotfixes May 27, 2022](https://worldofwarcraft.blizzard.com/en-us/news/23770463)

### Lokale Projektbasis

- [Equipment-Modell](/home/admin/projects/roll-drauf-vtt/vtt/models/equipment.py:7)
- [Inventory-Modell](/home/admin/projects/roll-drauf-vtt/vtt/models/inventory_item.py:7)
- [Character-Equipment-API](/home/admin/projects/roll-drauf-vtt/vtt/characters/routes.py:1008)
- [Character-Sheet-Equipment-UI](/home/admin/projects/roll-drauf-vtt/vtt/templates/character-sheet.html:1267)
- [MMO-Meta-Layer-Konzept](/home/admin/projects/roll-drauf-vtt/docs/DADM_DISCOVER_MMO_META_LAYER_CONCEPT_2026-07-21.md)

