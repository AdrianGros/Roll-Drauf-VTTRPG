# Klick-Verträge (Interaction Contracts)

Eine JSON-Datei pro Seite. Jedes interaktive Element bekommt einen Vertrag:
Selektor, Aktion, beobachtbare Nachbedingung. `tools/robots/crawler.py` setzt
die Verträge durch (Regelwerk §1–§3 in
`docs/ROBOT_FLEET_AND_RULEBOOK_2026-08-24.md`).

Schema pro Datei:

```json
{
  "page": "dashboard",              // Name (= Dateiname ohne .json)
  "path": "/dashboard",             // direkte Route (Reach-Path v1)
  "ready": "#book-dashboard-scene", // Selektor, der "Seite bereit" bedeutet
  "elements": [ { ... } ]
}
```

Schema pro Element:

- `id`: stabiler Vertragsname (kebab-case).
- `selector`: CSS-Selektor; MUSS (ggf. zusammen mit `text`) genau ein
  Element treffen. Bevorzugt `data-testid`, bis dahin echte IDs/Klassen
  (§13: neue GUI-Elemente liefern testid + Vertrag in derselben Phase mit).
- `text` (optional): Textfilter (Teilstring, case-insensitiv) zusätzlich zum
  Selektor — nötig, solange JS-gerenderte Knöpfe weder id noch testid haben.
- `label`: menschenlesbarer Name fürs Reporting.
- `kind`: `nav` | `auth` | `action` | `panel` | `destructive`.
- `engines`: Teilmenge von `["mouse", "keyboard"]`. Bei mehr als einer Engine
  prüft der Crawler die Ein-Engine-Invariante: beide müssen im selben
  Ergebnis landen (Designbrief §7).
- `expect`: mindestens eines von
  - `route`: URL enthält diesen Pfad nach der Aktion,
  - `visible`: Selektor wird sichtbar,
  - `hidden`: Selektor verschwindet,
  - `in_viewport`: Selektor liegt nach der Aktion im sichtbaren Bereich
    (für Scroll-Navigation wie die Home-Rail),
  - `effect: "any"`: irgendein beobachtbarer Effekt (DOM-Mutation,
    Navigation, Netzwerk-Request oder Scroll) — sonst „toter Knopf".
    Mindestvertrag; sobald das Verhalten bekannt ist, präzisieren.
- `expect_disabled: true` statt `expect`: das Element MUSS sichtbar und
  deaktiviert sein (z. B. „Aktuelle Gilde"); es wird nicht geklickt.
- `nth`: Index, wenn der Selektor absichtlich mehrere Elemente trifft.
- `text_exact: true`: `text` muss exakt (getrimmt, case-insensitiv)
  übereinstimmen statt als Teilstring.
- `severity`: `blocker` | `high` | `medium` | `low`.
- `resets_auth`: `true`, wenn die Aktion die Sitzung beendet (Crawler loggt
  sich danach neu ein).

Regeln aus der Feld-Recherche (§8.3 im Regelwerk): Reset zwischen Klicks =
Neuladen über den Reach-Path, nie Browser-Zurück; destruktive Verträge laufen
seriell und nur gegen den Wegwerf-Stack; jede randomisierte Reihenfolge ist
geseedet und der Seed steht im Report.
