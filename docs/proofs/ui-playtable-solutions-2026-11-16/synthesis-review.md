# Koordinationsprüfung und Zusammenführung

Datum 16.11.2026. Status: abgeschlossen. Phase Discover; Aufbewahrung dauerhaft.
Claude lieferte den [unveränderten Teilbericht](claude-research.md) erfolgreich
über die vorhandene Abo-CLI. Die nachfolgenden Ergänzungen sind Codex-Prüfungen
und überschreiben den Originalbericht nicht. Kein unabhängiges zweites
Implementierungsreview oder erfolgreicher Browserlauf wird behauptet.

## Bestätigte zusätzliche Befunde

- `play.html:2759`: „Grid“ ist der englische Text des Mess-Snap-Buttons
  `btnMeasureSnap`, kein Rasterparameterdialog. Die Zuordnung zum im Gespräch
  geklickten Button bleibt bis zur Browserreproduktion eine Hypothese.
- `play-ui.js:1392–1412`: Punktsnap und Diagonalregel hängen am selben Zustand.
  Formen messen anders als die gesnappte Linie. Eine Änderung ist damit auch
  eine Messregelentscheidung, nicht bloß eine andere Cursorposition.
- `play.html` legt 12px für die Messbeschriftung innerhalb der gezoomten Ebene fest.
  Die geringe Bildschirmgröße bei starkem Herauszoomen folgt daraus rechnerisch;
  ein tatsächlicher visueller Lesbarkeitstest wurde nicht ausgeführt.
- `_cancelTokenPlacement` leert den Vorlagenzustand nicht. Das ist im Code bestätigt,
  eine konkrete fehlerhafte Übernahme in einer folgenden Nutzerreise aber noch nicht reproduziert.
- `SceneStack.game_session_id` ist eindeutig; die Seitenstruktur ist bisher
  sessiongebunden. Eine über Sessions fortbestehende Hierarchie ist keine
  automatische Folge von `parent_layer_id`.
- Eagle-Fenster werden außerhalb der Hauptseite montiert und haben festen
  oberen Abstand. Ein neuer Buchrahmen muss deren Platz und Lebenszyklus erhalten.

## Präzisierungen vor Übernahme in Apply

1. **Palette:** Claudes Aussage „Quelle/Farbwerte offen“ ist durch die zusätzliche
   Codex-Recherche ergänzt: Der direkte Herausgeber der passenden Palette liefert
   `#5E4A8C`, `#8A8A8A`, `#1C1C1C`, `#F8F4E9`. Die Identität mit der im Call
   geöffneten Website bleibt eine Schlussfolgerung. Die konkrete Kontrastrechnung
   ersetzt die bedingte Vermutung über Mouse Gray: auf Ink Black sind es 4,94:1.
2. **Kartenroute:** Aus dem Funktionskörper von `update_map` allein folgt kein
   bestehender Owner-as-Player-Bypass. `campaigns/routes.py::_is_dm` ruft bereits
   `restrict_campaign_role` auf; `play/contexts.py::install_http_guard` löst einen
   mitgelieferten Kontext auch für Kampagnenpfade auf und prüft die Ressourcenbindung.
   Bei gültigem getragenem Player-Kontext senkt der Helper die Kampagnenrechte.
   Ob ein vorhandener Weg erweitert oder ein eigener Tischendpunkt verwendet wird,
   bleibt Apply-Entscheidung. Tischkontext, Revision/Konkurrenz und Aktualisierung
   anderer Clients müssen dabei ausdrücklich abgedeckt sein.
3. **Hierarchiedaten:** `SceneLayer.campaign_map_id` ist bisher nicht nullable.
   Eine reine Elternreferenz ermöglicht Beziehungen zwischen vorhandenen Karten,
   aber nicht allein zusätzliche Gruppen ohne Karte. Die Entscheidung „Oberseite
   ist selbst Karte oder reiner Ordner“ muss vor Schemaarbeit fallen.
4. **Abnahme:** Vorgeschlagene Interaktionen (Ziehmodus, Select-Leerraum-Pan,
   Auf-/Zuklappen) und Zahlenwerte (1px, 12px, 40px, exakte HTTP-Codes) sind
   Abnahmekandidaten der Recherche, keine neu bestätigten Owner-Vorgaben.
   Fremdvorlagen-404 gilt nicht automatisch für einen Erstellweg, der bisher
   keine Vorlagen-ID transportiert. Ressourcen- und Fehlervertrag dafür erst bestimmen.
5. **Normative Quellen:** W3C Listbox/Treeview/Treegrid/Breadcrumb, Pointer Events,
   Foundry Measurement/Scenes und WCAG-Kontrast wurden für die Synthese direkt
   gegengeprüft. W3C Target Size 2.5.8 wurde zusätzlich gelesen: 24×24 CSS-Pixel
   sind das Grundkriterium mit dokumentierten Ausnahmen, keine pauschale Regel
   ohne Ausnahmen. Kein Messlauf der realen App wird daraus abgeleitet.

## Einordnung der Prüffavoriten

Als nächste Apply-Kandidaten bleiben besonders plausibel: vorhandene semantische
Farben und eine gemeinsame Dokument-Buchschale; Bibliotheksauswahl mit bewusstem
Kartenklick; lesbare Messlabels und entkoppelte Messregeln; ein klar benannter
Rasterparameterweg mit autorisiertem Kontext; Baum-/Breadcrumb-Vergleich nach
Klärung der Persistenzebene. Diese Bewertung folgt aus bestehendem Code und
Ownerzielen, nicht aus einer pauschalen technischen Freigabe.

Die Domänenpakete U02/U03/U04/U07/U08/U13 sind im
[Codex-Teilbericht](codex-domain-research.md) separat verglichen. Ihre Medium-Risiken
bleiben vor dem jeweiligen Deploy-Handoff zu bearbeiten. Es wurden keine
Rechteprüfungen geöffnet, Anwendungsdateien geändert oder Funktionen ausgeliefert.
