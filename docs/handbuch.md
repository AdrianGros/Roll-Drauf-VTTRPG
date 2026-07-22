# Handbuch Aktuelle Version (Stand: 2026-03-27)

## 1. Versionsstand

- Projekt: `roll-drauf-vtt`
- Branch: `main`
- Zustand: Worktree mit uncommitted Änderungen
- Milestone-Stand: **M47-M54 abgeschlossen (Roll20-Copy-Workflow Baseline)**
- Durchgeführte technische Fixes in diesem Lauf:
  - ORM-Konflikt behoben: `SessionState` Backref heißt jetzt `runtime_state` statt `session_state`
  - Register-UI verdrahtet auf `/api/auth/register-with-key` mit Feld `registration_key`
  - Session-Asset-Upload hat jetzt echte Storage-Persistenz (statt TODO), inkl. Quota-Update
  - Socket-Konflikt entschärft: M45-V2-Handler nur optional via `USE_SESSION_SOCKET_V2=true`
- Validierung:
  - `tests/test_session_state_machine.py` + `tests/test_session_state.py`: **7 passed**

## 2. Impact-Skala User Journey

- `Niedrig`: kaum spürbar, kein Flow-Bruch
- `Mittel`: merkbarer Extra-Aufwand, aber Task gelingt
- `Hoch`: Abbruch-/Frustrisiko oder Fehlbedienung sehr wahrscheinlich

## 3. Feature-Liste mit Soll-Ablauf und UX-Prüfung

| # | Feature | Gedachter Ablauf (Soll) | Unangenehme Prozesse / Risiken | Journey-Impact |
|---|---|---|---|---|
| F1 | Registrierung mit Schlüssel | Nutzer öffnet `register.html`, gibt Key + Accountdaten ein, Backend validiert Key, Account wird mit Tier erstellt, Login-Cookies gesetzt, Redirect Dashboard | Vor dem Fix war UI auf falschem Endpoint. Jetzt korrigiert. Noch reibend: Key-Formatfehler zeigt thematisch falsche Meldung (`No uses remain`) statt klarer Format-Hinweis | Mittel |
| F2 | Login/Session/Auth | Login, Cookie/JWT-Session, `check/me/refresh/logout`, optional MFA | Wechsel zwischen Session/Cookie/JWT ist technisch robust, aber Fehlertexte sind teils technisch und nicht konsistent mit Spellbook-UX | Niedrig bis Mittel |
| F3 | Kampagnenverwaltung | Kampagne erstellen, Mitglieder einladen, Invite annehmen, Sessions + Maps verwalten | Viele Aktionen über getrennte Endpoints; ohne klaren UI-Wizard kann DM mehrfach Kontext wechseln | Mittel |
| F4 | Session Lifecycle (M41) | DM startet Session (`start`), pausiert/resumed, beendet, archiviert | State-Maschine ist vorhanden; Risiko bleibt bei fehlender UI-Leitlinie, wann alte (`campaigns/.../start`) vs neue (`/api/sessions/<id>/start`) Routen genutzt werden | Mittel |
| F5 | Map-Layer (M42) | DM legt Layer an, ordnet, aktiviert, blendet aus/ein | Layer-Management ist mächtig, aber potenziell komplex ohne visuelle Drag&Drop-Reihenfolgeanzeige | Mittel |
| F6 | Tokens & Initiative (M43) | DM setzt Tokens, bewegt/rotiert, pflegt Initiative, schaltet Runden weiter | Token/Initiative liegen teils in alten und neuen API-Schnitten; Bedienung kann inkonsistent wirken, wenn Frontend nicht klar auf ein Modell vereinheitlicht ist | Hoch |
| F7 | Session Assets (M44) | Upload pro Session (Maps/Handouts), Assets im Session-Kontext nutzen | In `sessions.py` ist Upload-Storage noch mit TODO markiert (Persistenzpfad/Storage-Backends), dadurch Risiko auf unklare Dateiablage im Betrieb | Mittel |
| F8 | Realtime Sync (M45) | Client joint Session-Room, bekommt Events (Map/Token/Initiative/Session), Resync bei Reconnect | Potenziell unangenehm: Eventnamen überschneiden sich zwischen `socket_handlers.py` und `socket_handlers_sessions.py` (z. B. `session:join`), kann zu schwer debuggbaren Echtzeit-Effekten führen | Hoch |
| F9 | Spellbook Theme (M46) | Theme laden, CSS-Variablen greifen global, Book-Animation bei Erfolg, Branding konsistent | Register-Flow ist stark thematisiert; Session-Workspace ist noch nicht vollständig spellbook-konsistent (`play.html` weiterhin stark Legacy-Look) | Mittel |
| F10 | Key-Admin Dashboard (M37-M40) | Admin generiert Batch, exportiert CSV/PDF, überwacht Stats, revoke/unrestrict | Funktionsumfang gut. Reibung: viele Einzelaktionen, Batch-UX kann ohne Filter-/Status-Defaults unübersichtlich werden | Mittel |
| F11 | Moderation & Community | Chat, Reports, Moderation Actions, Voice-Config pro Session | Für Nutzer solide; für Mods/Admins viele Endpoints und Rollenregeln, hoher kognitiver Kontextwechsel | Mittel |
| F12 | Character/Spells/Equipment/Inventory | Charakter erstellen, Sheet pflegen, Zauber/Gegenstände/Inventar verwalten | Umfang groß, aber klassische CRUD-Lastigkeit; bei längeren Formularen droht Form-Fatigue | Mittel |
| F13 | Profil-Lifecycle (M18) | Nutzer kann Deletion anstoßen/canceln/deaktivieren/reaktivieren, Admin kann Restores/Force-Delete | Gut für Compliance. UX-Risiko: irreversible Admin-Aktionen brauchen sehr klare Confirm-Schritte in UI | Mittel |
| F14 | Ops/Health/Monitoring | `/health/live`, `/health/ready`, `/health/release`, `/metrics` | Für Endnutzer unsichtbar; für Betrieb sehr wichtig, kaum Journey-Impact | Niedrig |

## 4. Handbuch (Bedienung der aktuellen Version)

## 4.1 Registrierung und erster Einstieg

1. Öffne `/register.html`.
2. Gib einen gültigen Registrierungsschlüssel im Format `SPELL-XXXX-XXXX-XXXX` ein.
3. Fülle Username, E-Mail, Passwort aus.
4. Nach Erfolg wird Account erzeugt und zur Übersicht weitergeleitet.

Hinweis:
- Schlüssel ist verpflichtend für den Key-Flow (`/api/auth/register-with-key`).

## 4.2 Login und Sicherheit

1. Login über `/login.html`.
2. Optional MFA aktivieren über Auth-Endpunkte.
3. Session prüfen mit `/api/auth/check` oder `/api/auth/me`.
4. Logout über `/api/auth/logout`.

## 4.3 Kampagnenarbeit für DM

1. Kampagne erstellen: `POST /api/campaigns`.
2. Mitglieder einladen: `POST /api/campaigns/<id>/invite`.
3. Session erstellen: `POST /api/campaigns/<id>/sessions`.
4. Karte(n) hochladen und verwalten.

## 4.4 Live-Session durchführen

1. Session starten (`/api/sessions/<id>/start` oder Campaign-Flow je UI).
2. Map-Layer vorbereiten (`/api/sessions/<id>/map-layers`).
3. Tokens setzen/bewegen (`/api/sessions/<id>/tokens`).
4. Initiative starten (`/api/sessions/<id>/initiative/...`).
5. Bei Pause/Unterbruch: `/pause` und `/resume`.
6. Session beenden mit `/end`, später ggf. `/archive`.

## 4.5 Realtime-Play

1. Client verbindet Socket.
2. Join Session-Room (`session:join`).
3. Bei Verbindungsproblemen Resync anfordern (`session:resync`).
4. Token-/Layer-/Initiative-Events werden in den Raum broadcastet.

## 4.6 Assets in Session

1. Session-spezifischer Upload: `POST /api/sessions/<id>/assets/upload`.
2. Assets für aktive Layer/State nutzen.

Achtung:
- Storage-Implementierung ist funktional angelegt, aber mit TODO markiert (Betrieb vor Livegang verifizieren).

## 4.7 Admin: Registrierungsschlüssel

1. Batch erzeugen: `POST /api/admin/keys/generate`.
2. Batches und Details prüfen: `/api/admin/keys/batches`, `/batch/<id>`.
3. Export: CSV oder PDF.
4. Governance: Schlüssel revoke/unrestrict, Stats prüfen.

## 4.8 Theme-Administration

1. Aktive Einstellungen abrufen: `GET /api/theme/settings`.
2. Theme aktualisieren: `POST /api/theme/admin/update`.
3. Preview-Anpassung: `POST /api/theme/admin/customize`.
4. Reset: `POST /api/theme/admin/reset`.

## 5. Kritische UX-Baustellen (priorisiert)

1. Legacy-/Neu-Flow bei Session/Token/Initiative API weiter vereinheitlichen (ein klarer Pfad im Frontend).
2. Session-Workspace-UI final auf Spellbook-Look angleichen (`play.html`/`session.html` Entscheidung + Umsetzung).
3. Fehlermeldung für Key-Format im Register-Formular präzisieren.
4. E2E-Browsertests für DM-Quickstart und Player-Join ergänzen.

## 6. Kurzfazit

Die Version ist funktionsreich und technisch deutlich weiter als der Ausgangspunkt. Der größte Hebel für eine glatte User Journey liegt jetzt in **Flow-Vereinheitlichung** (alte/neue Session-APIs + Socket-Event-Überlappungen) und in der **UI-Konsistenz** zwischen Spellbook-Onboarding und tatsächlichem Play-Workspace.
