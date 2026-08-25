# Spieltisch-Audit — Basis-Funktions-Kit

**Datum:** 2026-08-25 · **Auditor:** Claude (Hauptsession + Explore-Agent) · **Sicherheit:** ausschließlich lesend im Repo plus Robot-Läufe gegen den Wegwerf-Stack (§12); keine Änderung an Anwendungs- oder Arbeitsbaum-Dateien. **Baum-Stand:** Commit `ab18949` plus Codex' laufende, uncommittete Login-/Play-Änderungen — Login ist aktiv in Arbeit (Codex' Spur, hier nicht angefasst).

**Klartext-Fazit:** Der Tisch hat ein solides, getestetes Fundament (Szenen, Tokens, Echtzeit, Rechte-Schreibpfad — Robot-beweisbar grün), aber das „Basis-Funktions-Kit" hat vier Lücken, von denen eine ein **Sicherheitsleck** ist und eine ein **totes, fertig gebautes Feature**: Das komplette Kampf-Backend existiert getestet — der Tisch ruft es schlicht nie auf.


---

## Addendum (2026-08-25, später): P0 und der Seiten-Sackgassen-Fix sind gelandet

Beide Baustellen aus §3 sind implementiert und grün, verifiziert gegen den
vollen Wegwerf-Stack-Testlauf (465 Tests):

- **P0 (DM-Geheimnisse serverseitig filtern):** `is_token_visible_to`,
  `filter_tokens_for`, `is_serialized_token_visible_to` und
  `filter_combat_payload` in `vtt/play/service.py` — die Regel ist jetzt am
  Lesepfad erzwungen, nicht nur clientseitig kosmetisch. Regressionsszenario:
  `tests/test_playtable_audit_fixes.py`.
- **Die Seiten-Sackgasse (§2, Zeile 5, Kampf-Zeile war unabhängig davon):**
  `allow_copy` an `POST .../scene-stack/layers` (`vtt/play/service.py:406`,
  `vtt/play/routes.py:314`) plus das neue Zwei-Wege-Menü in
  `_renderLayerAddControl` (`play-ui.js`) — Hochladen ODER eine vorhandene
  Karte übernehmen, bereits verwendete werden kopiert statt zu blocken.
  Regressionsszenario: `tests/test_layer_add_flow.py`. Der alte, jetzt
  überholte Vertragstest wurde auf das neue, dokumentierte Verhalten
  umgeschrieben (`test_playtable_add_page_offers_upload_or_copy_never_a_dead_end`
  in `tests/test_public_surface_and_playtable_contract.py`) statt einfach
  gelöscht — §10 gilt auch rückwärts: das Zielverhalten bleibt ein Vertrag.
- **Die in §1 vermerkte Mobile-Regression** (`kulissen`, zweistufiger Login
  blockierte phone-portrait) ist gegenstandslos: `#passwordLoginContinueBtn`
  existiert nicht mehr, der Login-Flow ist inzwischen einstufig.

Kampf-Backend-Anschluss (P1 #3), interne Würfe im Chat (P2 #4) und
Präsenz-Roster/Whisper (P2 #5) bleiben offen — an dieser Session nicht
angefasst, keine Vorarbeit dazu im Baum gefunden.

---

## 1. Robot-Beweise (Ist-Zustand, Wegwerf-Stack, 2026-08-25)

| Lauf | Ergebnis | Bedeutung |
|---|---|---|
| `fullsession` (DM+Spieler, echte /play-Oberfläche: Kampagne→Session→Tisch, Tokens, Sichtbarkeit, Würfel) | **0 Findings** | Der Echtzeit-Kern des Tisches funktioniert nachweislich |
| `mobile` (Telefon-Gates am Tisch: Kartenanteil, Tap-Ziele, Daumenzone, Würfel im Viewport) | **0 Findings** | Die Mobile-Sofort-Fixes (Commit `ab67094`) wirken; der „unbenutzbar"-Stand des Mobile-Audits ist am Tisch behoben |
| `kulissen` (V1/V2 Scroll-Treppe) | Desktop grün (Purpur = `linear-gradient` auf `body`); **blocked auf Telefon**, weil der neue zweistufige Login (`#passwordLoginContinueBtn`) auf phone-portrait nie sichtbar wird | ⚠️ An Codex: mögliche Mobile-Regression der laufenden Login-Umbauten |
| Betriebs-Randnotiz | `flows`/`fullsession`/`mobile` schreiben nach fest kodierten Pfaden `/tmp/vtt-*.json`; die gehören dort teils `root` → `PermissionError`, Evidence geht verloren | Empfehlung: Ausgabepfade in `artifacts/` parametrisieren |

## 2. Funktions-Kit-Matrix

| # | Fähigkeit | Status | Beleg | Lücke |
|---|---|---|---|---|
| 1 | Karte/Szenen (Upload, Grid, Zoom/Pan, Layer) | ✅ stark | [play-ui.js:1898](../vtt/static/js/play-ui.js#L1898), [service.py:254](../vtt/play/service.py#L254) | Layer-„Spieler-sichtbar" ist nur DM-Kosmetik: [serialize_scene_stack](../vtt/play/service.py#L240-L251) sendet alle Layer an alle |
| 2 | Tokens (setzen/ziehen/syncen, Konflikte, Dedupe) | ✅ / 🔶 | [socket_handlers.py:577](../vtt/socket_handlers.py#L577), Tests tokens_realtime | **`dm_only` wird nur clientseitig gefiltert** ([play-ui.js:2096](../vtt/static/js/play-ui.js#L2096), im Code selbst zugegeben bei :1902) — Spieler bekommen versteckte NPCs über die Leitung |
| 3 | Würfel (intern + Beyond20) | ✅ / 🔶 | [socket_handlers.py:935](../vtt/socket_handlers.py#L935), test_external_rolls | Interne Würfe landen in einem 8-Zeilen-Ringpuffer statt im Chat, **nicht persistiert** (Reload = weg); Grammatik nur `NdM±k` |
| 4 | Chat | ✅ | [socket_handlers.py:989](../vtt/socket_handlers.py#L989) | Kein Whisper/DM-Privatkanal (Modell hat keine Empfänger-Spalte); Offline-Fallback verliert Nachrichten stumm |
| 5 | Initiative/Kampf | ⛔ **Stub am Tisch** | Backend komplett + getestet: [combat/service.py](../vtt/combat/service.py), Routen 1369–1739 | `/play` ruft **nichts** davon auf: clientseitiger `Math.random()`-d20 ([play-ui.js:1034](../vtt/static/js/play-ui.js#L1034)), kein Rundenwechsel-Knopf; zwei tote Socket-Emitter ohne Server-Handler ([play-socket.js:138,146](../vtt/static/js/play-socket.js#L138)) |
| 6 | Charakterbogen am Tisch | ⛔ fehlt | Bogen existiert getestet standalone (1905 Zeilen) | Kein Link/Panel in play.html; `TokenState.character_id` wird serialisiert und nie benutzt — Spieler müssen den Tisch **verlassen**, um ihre Werte zu sehen |
| 7 | Session-Lebenszyklus (Join/Rejoin, Zustandsmaschine, Resync) | ✅ | [play/service.py:25](../vtt/play/service.py#L25), rejoin-Tests | „Start-Check" ist DM-Validierung, kein Spieler-Ready-Check; **keinerlei Präsenz/Roster** — niemand sieht, wer am Tisch ist |
| 8 | Rechte am Tisch | ✅ Schreibpfad | [_reject_read_only](../vtt/socket_handlers.py#L1103), 37 Permissions-Tests | Lesepfad ist das Leck aus #1/#2 |
| 9 | Einstieg Dashboard→Tisch | ✅ | Umschlag-Choreografie + Tests | „Lobby" ist eine Kampagnen-Liste, kein Session-Warteraum |
| 10 | Fog of War / Messwerkzeug / Audio | ⛔ fehlt (bestätigt) | tote `fog_enabled`-Spalte; play.html:1244 dokumentiert den Abriss der No-op-Knöpfe | Laut Masterplan bewusst Arcs 2/3 (Phasen 21–40) — **nicht** Teil des Basis-Kits |
| — | Bonus: Aktionsleiste (Attack/Dash/Interact) | 🔶 hohl | [actions.py:47](../vtt/play/actions.py#L47) | würfelt nichts, ändert nichts — sendet nur eine Logzeile mit `suggested_roll` |

## 3. Empfehlungen (Reihenfolge = Vorschlag fürs „Basis-Kit asap")

**P0 — Sicherheit, vor dem nächsten Deploy:**
1. **DM-Geheimnisse serverseitig filtern.** `serialize_state_payload`/`serialize_scene_stack` nach `session_role` filtern (dm_only-Tokens, unsichtbare Layer). Regel §10: erst das Robot-Szenario (Spieler-Socket empfängt dm_only-Token → Finding), dann der Fix. Der Test passt in `fullsession` als neue Phase.

**P1 — die zwei Basis-Kit-Lücken mit dem besten Aufwand/Nutzen:**
2. **Charakterbogen als Tisch-Panel.** `character_id` liegt schon am Token; ein Drawer/Overlay, das den bestehenden Bogen lädt, macht den Tisch spielbar, ohne die Seite zu verlassen. Billigster High-Value-Fix der Liste.
3. **Kampf-Backend anschließen statt neu bauen.** Der Tisch braucht: Encounter starten/beenden, echte Initiative (Server statt `Math.random()`), „Nächster Zug"-Knopf, Runden-Zähler — alles vorhanden hinter den `/combat`-Routen; fehlend sind nur UI-Aufrufe und die zwei nie geschriebenen Server-Handler zu den toten Emittern. Masterplan-Korrektur nötig: die Reife-Angabe „Kampf ~75 %, kein funktionales Gap" ist widerlegt.

**P2 — Rundung des Basis-Kits:**
4. **Interne Würfe in den Chat** persistieren (gleiches Muster wie Beyond20-Würfe, die es schon richtig machen); Würfel-Grammatik später erweitern (Adv/Dis, `2d6+1d4`).
5. **Präsenz-Roster + Whisper.** Wer sitzt am Tisch (Socket-Join/Leave existiert ja schon als Event) + Empfänger-Spalte im Chat-Modell.
6. **Kein Fog/Ruler/Audio jetzt.** Bewusst hinter das Basis-Kit (Masterplan Arcs 2/3); höchstens ein simples Distanz-Lineal wäre ein Kandidat, wenn Kampf am Tisch live geht.

**Robot-Anschluss (nach P0/P1):** `contracts/play.json` für die Tisch-Werkzeuge schreiben (Crawler-Muster steht), `fullsession` bleibt das Regressionsnetz; die hohle Aktionsleiste bekommt entweder echte Verträge oder folgt dem Vorbild der abgerissenen No-op-Knöpfe (§2: kein Knopf ohne Wirkung).

---

*Verfahren: Explore-Agent-Kartierung (Code+Tests+Docs, Belege als file:line), Robot-Läufe gegen Wegwerf-Stack, Abgleich mit MASTERPLAN_1_100, vtt_gap_analysis und MOBILE_AUDIT. Beratend; Priorisierung liegt bei Adrian.*
