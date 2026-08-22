# Roll-Drauf VTT — Stabilisierungs-Reifegradmatrix (2026-07-30)

## Zweck und Methode

Dieses Dokument ergänzt, ersetzt aber nicht, die bestehende
[`vtt_gap_analysis_2026_07_30.md`](vtt_gap_analysis_2026_07_30.md) (dritte
Edition, 1460 Zeilen, selbst bereits sehr gründlich: vollständiger Pytest-Lauf,
direkte Produktions-DB-Abfrage, echter End-to-End-HTTP-Test mit
Prozess-Neustart). Diese Matrix übernimmt deren Befunde als Tatsachenbasis und
ordnet sie — analog zum Goblin-Delve-Bot-Muster
(`STABILIZATION_ROADMAP_95_PERCENT.md`) — in eine Reifegrad-Tabelle pro
funktionalem Block ein, damit auf einen Blick sichtbar ist, wo Code, Tests und
tatsächlicher Produktionsbetrieb auseinanderlaufen.

**Warum keine komplett neue Analyse:** Die bestehende Gap-Analyse ist von
heute, bereits in der dritten Edition, und methodisch stärker als eine erneute
Ad-hoc-Prüfung es in vertretbarem Aufwand wäre (echter Prozess-Neustart-Test,
direkte Produktions-DB-Abfrage, vollständige Testsuite). Diese Matrix fügt die
fehlende Dimension hinzu: nicht nur *was* fehlt, sondern *wie reif* jeder
Funktionsbereich laut denselben Kriterien ist, die auch für den Goblin-Delve-
Bot verwendet wurden.

**Wichtiger Unterschied zu Goblin Delve:** Dort existiert ein einziger,
weitgehend aktueller Phasenplan (`PHASE_PLAN_CORRECTED.md`). Hier gibt es das
nicht — Teil I der Gap-Analyse dokumentiert vier bis fünf überlappende,
teils widersprüchliche Meilenstein-Nummerierungsschemata ohne eine einzige
Wahrheitsquelle. Diese Matrix verwendet deshalb **funktionale Blöcke aus dem
tatsächlichen Code/Testbestand** (Tabelle II.4 der Gap-Analyse) als Grundlage
statt eines der widersprüchlichen Meilenstein-Schemata — das ist die einzig
belastbare Basis, die heute existiert.

## Reifegrad-Kriterien (adaptiert aus dem Goblin-Delve-Rahmen)

Ein Funktionsbereich gilt als 95%-reif, wenn er:

1. fachlich eindeutig definiert ist, ohne konkurrierende Definitionen im Code;
2. für Spieler bzw. Staff sichtbar und verständlich ist;
3. normale, ungültige, Grenz- und Neustartfälle behandelt;
4. persistenzseitig atomar und idempotent arbeitet, ohne zwei unabhängige
   Schreibpfade auf denselben Zustand;
5. durch Unit-, Integrations- und mindestens einen Ende-zu-Ende-Test
   abgesichert ist;
6. dokumentiert, in Produktion tatsächlich ausgeliefert und live verifiziert
   ist — Code-grün allein zählt nicht, wenn die laufende Produktion einen
   älteren Stand ausführt.

## Reifegradmatrix

| # | Funktionsbereich | Tests (Quelle: Tabelle II.4) | Reifegrad | Sichtbar | Größte 95%-Lücke |
|---|---|---|---|---|---|
| 1 | Zugriffskontrolle / Berechtigungen | 37, grün | **~40%** trotz grüner Tests | ja, plattformweit | Kriterium 6 verletzt auf die schwerstmögliche Art: der Fix (`3e7dbe6`) behebt einen aktiven Privilege-Escalation-Bug im Code, aber **die laufende Produktion führt seit 48+ Stunden noch das verwundbare Image aus** — direkte DB-Abfrage zeigt alle 4 realen Nutzerkonten weiterhin mit dem gefährlichen `platform_role='supporter'`-Default (Gap-Analyse §V.2). Das ist der wichtigste Einzelbefund des gesamten Berichts. |
| 2 | Kampagnen & Sessions | ~50, grün | **~70%** | ja | Kriterium 4 verletzt: zwei unabhängige Schreibpfade (`POST maps/activate` und `scene-stack/init`) auf denselben `SessionState.active_map_id` kennen sich nicht — live reproduziert, überschreibt eine bewusst gewählte Karte stillschweigend durch die älteste Kampagnenkarte (§III.3, §IV.5). Kriterium 5 ebenfalls verletzt: keiner der 414 Tests deckt genau diese Kombination ab. |
| 3 | Play-Runtime (Scene Stack, Bootstrap, Übergänge) | ~45, grün, inkl. 13 neue + echter Neustart-Test | **~85%** | ja | Teilt sich Kriterium 4 mit Block 2 (dieselbe Divergenz, siehe oben) — ansonsten der am gründlichsten verifizierte Block im gesamten Repository (einziger Bereich mit echtem Prozess-Neustart-Nachweis per Ad-hoc-HTTP-Test). |
| 4 | Kampf / Initiative / Tokens | ~20, grün | **~75%** | ja | Kriterium 1 leicht verletzt: `session_tokens`-Tabelle (tot, M43-naheliegend benannt) und die aktiven Initiative-Routen teilen sich einen irreführend ähnlichen Namensraum ohne Code-Beziehung — Verwechslungsrisiko für neue Mitwirkende, kein funktionaler Bug. |
| 5 | Charaktere & Fortschritt | ~150, größtenteils grün (1 bekannter trivialer Fehlschlag) | **~90%** | ja | Größter und reifste Testbereich der Anwendung (über ein Drittel aller 414 Tests). Einzige Lücke: ein veralteter String-Vergleich in einem Test, kein Produktcode-Fehler. |
| 6 | Community / Guilds / Chat / Moderation | ~25, 1 bekannter Fehlschlag | **~65%** | ja | Kriterium 1 verletzt: das duale `role_id`/`platform_role`-System ist ein seit langem als "90-Tage-Deprecation-Plan" geflaggtes, nie abgeschlossenes Übergangsmodell — Ursache des Testfehlschlags, kein Einzelfall. |
| 7 | Seiteninhalt / Dashboard / Ops | ~30, grün | **~75%** | ja | Kriterium 1 verletzt: das ausgelieferte M65-Feature (editierbarer Seiteninhalt) trägt dieselbe Meilenstein-Nummer wie ein anderes, im Session-Pipeline-Programm geplantes, nie gebautes Feature ("Drag-and-Drop Placement") — funktional kein Bug, aber jede Kommunikation über "M65" ist heute mehrdeutig. |
| 8 | Assets / Storage | ~10, grün nur für den `local`-Adapter | **~55%** | ja (nur lokaler Adapter live) | Kriterium 3 verletzt: der `S3StorageAdapter`-Codepfad hat keine eigene Testdatei und importiert `boto3`, das **nicht** in `requirements.txt` steht — inert heute, würde aber beim ersten echten Umstieg auf S3 sofort mit `ModuleNotFoundError` abstürzen statt kontrolliert zu scheitern. |
| 9 | Auth & Registrierung | ~40, grün | **~80%** | ja | Kriterium 6 teilweise offen: MFA-Codepfade sind mitgetestet, aber in keiner geprüften Umgebungsdatei standardmäßig aktiv — funktional vorhanden, aber nie live in Betrieb verifiziert. |
| 10 | UX-/Closeout-Härtung | ~20, 1 bekannter Fehlschlag | **~70%** | ja | Kriterium 6 verletzt: fast der gesamte Block trägt DAD-M-Meilenstein-Namen direkt im Dateinamen (`_closeout`, `_stabilization`, `_productization`) ohne ein einziges zugehöriges Dokument in `docs/` — dieselbe Papierspur-Lücke, die auch die neuesten echten Features (M0–M4, M5/M7) betrifft. |
| 11 | Release Engineering / Deployment-Betrieb | kein eigener Testbereich — betrifft alle Blöcke | **~25%** | teilweise (nur für Betreiber) | Mehrfachverletzung: Produktions-Image 48+ Stunden hinter einem Sicherheitsfix (Block 1); keine funktionierende Staging-Umgebung (`deploy_staging.sh` importiert weiterhin `vtt_app`, würde sofort mit `ModuleNotFoundError` scheitern, §V.3); Pytest-Collection-Bug seit vier Monaten unverändert offen; zwei verwaiste, ungenutzte Docker-Images; kein reproduzierbarer Regressionstest hätte den Block-2/3-Bug aufgefangen — genau das, wofür eine echte Staging-Umgebung da wäre. |
| 12 | Dokumentation & Planungsprozess | — | **~20%** | nein (nur intern) | Mehrfachverletzung von Kriterium 1: vier bis fünf überlappende, sich teils widersprechende Meilenstein-Schemata (§I.2), eine Namenskollision auf derselben Nummer (M65) für zwei verschiedene Features, kein einziges als "aktueller Stand" gültiges Dokument, die letzten beiden echten Feature-Arbeiten (M0–M4, M5/M7) komplett ohne die vom Projekt selbst vorgeschriebene DAD-M-Papierspur, 41 Dokumente verweisen noch auf den seit dem 22. Juli falschen Paketnamen `vtt_app`. |

## Was am dringendsten ist

Sortiert nach Wirkung, nicht nach Umsetzungsaufwand — deckt sich mit Teil VI
der Gap-Analyse, hier auf die Reifegrad-Perspektive verdichtet:

1. **Block 1 (Zugriffskontrolle) ist der einzige Block, bei dem "Code ist
   grün" aktiv in die Irre führt.** Alle 37 Tests bestehen, aber das
   entscheidende Kriterium — läuft der Fix tatsächlich in Produktion — ist
   verletzt, mit realem Impact auf alle 4 heutigen Nutzerkonten. Kein anderer
   Block in dieser Matrix hat eine so große Lücke zwischen Test-Ergebnis und
   Produktionsrealität.
2. **Block 11 (Release Engineering) ist strukturell der Grund, warum Block 1
   passieren konnte und wieso Block 2/3s Divergenz-Bug nicht vorher auffiel.**
   Ohne funktionierende Staging-Umgebung und mit einem Deploy-Prozess, der
   Fixes tagelang ungenutzt im Repository lässt, ist jeder einzelne Block
   strukturell gefährdet, unabhängig von seiner eigenen Testabdeckung.
3. **Block 12 (Dokumentation) ist die Ursache, warum es kein "gegen alle
   geplanten Features" im Sinne von Goblin Delve geben kann** — es gibt
   keine widerspruchsfreie Liste "geplanter Features", gegen die man prüfen
   könnte. Das ist selbst der wichtigste Dokumentationsbefund.
4. Blöcke 2/3 (Kampagnen/Sessions + Play-Runtime) teilen sich einen konkreten,
   live reproduzierten Bug (doppelter Schreibpfad auf `active_map_id`), der
   vor dem nächsten Deploy behoben oder zumindest sichtbar gemacht werden
   sollte (Teil VI, P0, Optionen a/b/c der Gap-Analyse).

## Empfohlene nächste Schritte

Identisch mit Teil VI der Gap-Analyse (P0–P3), hier nicht dupliziert. Diese
Matrix ergänzt nur die Reifegrad-Einordnung; die konkrete Handlungsliste
bleibt die bestehende Quelle.
