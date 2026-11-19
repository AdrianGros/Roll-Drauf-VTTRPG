# W03 Apply: private calendar notes, reminders and One-Shots

18.11.2026 design / 19.11.2026 isolated verification · DAD-M standard · Status: implemented and verified in disposable testing environments; coordinator owns integration and live delivery. Retention: permanent. Input: owner authorization to orchestrate/implement review K02–K04 and research R03. Base:49e8b9944. No new dependencies, quotas, external messages or push delivery.

## Scope and ownership

Owned: `vtt/calendar_notes.py`, `vtt/models/calendar_note.py`, `vtt/static/js/session-calendar.js`, `vtt/static/css/session-calendar.css`, `tools/calendar_reminders.py`, focused API/browser tests and this evidence. Coordinator owns app/model registration and production delivery. Existing series/polls remain intact.

## Data and interfaces

`CalendarNote`: private user FK, UUID request key/input digest, ISO calendar day, title≤80/body≤2000, one of seven named colors, revision≥1, UTC reminder instant + IANA zone, optional fold selection, reminder state none/pending/ready/dismissed, timestamps and soft-deletion tombstone. Unique (user,request key); ≤20 live notes per day and ≤2000 per user, bounded input. Date identity never derives from UTC midnight. Creation retries return same row; different payload for same key→409. PUT requires revision and atomically compares it; DELETE is repeatable without resurrecting content. No other user ID accepted.

Authenticated+CSRF API prefix `/api/calendar`: GET/POST `/notes`; GET bounded start/end≤62 days with cursor, notes-only user projection and complete/pagination indicators; PUT/DELETE `/notes/<id>`; GET `/reminders` returns own ready reminders (bounded, cursor); POST `/notes/<id>/dismiss` checks current revision. Missing/foreign/deleted rows→404; invalid data400; stale writes409. Strict datetime+IANA conversion rejects spring gaps and requires explicit fold for ambiguous autumn time. Absolute reminder instant is stored UTC; past/new reminder and horizon bounds explicit (up to366 days ahead).

Worker `process_due(limit≤500)` claims pending due rows with FOR UPDATE SKIP LOCKED (ordinary limited selection on SQLite) and changes to ready atomically; no external side effects, so retries do not duplicate notifications. Read paths do not mutate reminder state. Rescheduling/deletion before worker execution prevents stale notifications; no stale payload copied to another table. CLI `tools/calendar_reminders.py --once` or bounded loop performs the transition. Coordinator deploys existing-host worker/timer; UI states that system/browser notifications are unavailable and provides durable in-app reminders after reload. No per-Gunicorn scheduler.

`CalendarOneShot`: unique campaign FK, user FK, UUID request key/input digest and real session FK. GET/POST `/oneshots` exposes only owner/active-member rounds. POST parses bounded name/max_players/date/time/duration and creates Campaign, active owner DM member, GameSession and marker in one transaction. Locks User, then uses existing `permissions.can_create_campaign`; count uses normal active campaign quota. Player capability may not create new privileged scope. Existing campaign rights apply to subsequent management. Idempotent identical retry returns same real round; different input409. UI explicitly states One-Shots occupy a campaign slot. Existing campaign APIs are not silently changed.

POST `/sessions` creates a one-off series in a selected managed existing campaign through `session_calendar.create_series` and its campaign lock/current-rights checks. Existing auth guard validates carried contexts before route processing. No session may be created by Player mode just because the account owns the campaign.

## UI and acceptance

Calendar toolbar offers Notes/Planning mode and One-Shots. Normal click/Enter/touch opens a titled native day dialog; day filtering remains. Notes show marker+named color, are separately editable/deletable and survive reload. Form uses plain text, labels, color select, optional local reminder+zone and ambiguity fold. Closing returns focus to the current day button. Planning offers only managed campaigns and date-prefilled session creation; One-Shot has visible create/list and hub links. Reminder area shows ready items across dates and dismiss, refreshes on visibility/poll; no closed-tab notification promise. DE/EN labels use literal UI adapter with coordinator catalog integration.

Tests: note isolation and direct-ID access; idempotent retry, revision conflict and tombstone; allowed fields and limits; UTC conversion/gap/ambiguous fold; cancellation/reschedule/dismiss, bounded worker and repeated execution; quotas, wrong tier, exact One-Shot retry, atomic ordinary models, campaign member projection and carried Player denial; normal sessions reuse service. Browser click→note→reload→edit/delete and DM planning/One-Shot journeys, keyboard/modal/touch-sized viewport. Existing calendar API/browser regressions remain relevant.

## Risks and handoff

Medium concurrency/privacy concerns addressed by private predicate on every query, explicit revision CAS, user/campaign locks, existing permission helpers, bounded queries and worker transitions with no external side effects. No new high-severity defect is asserted. Additive tables permit old image rollback; no existing rows/schema columns changed. Foreign key deletion ordering must be included in synthetic cleanup. Coordinator imports `CalendarNote, CalendarOneShot` into model registry and registers `calendar_notes_bp`; migration creates only these two tables before activation and preserves database backup. Production live journey and rollback are coordinator-owned and remain unclaimed by this slice.

## Verification and integration evidence (19.11.2026)

All commands used the pre-existing `roll-drauf-vtt-mobile-tests:20261115` image with this worktree mounted at `/app`, no production environment and no production database. SQLite/API/CLI/browser containers used `--network none`. PostgreSQL tests used a separate temporary `postgres:16-alpine` container with `--network none`, a tmpfs database named `calendar_review_test`, a fresh random schema per test and test-container networking shared only with that disposable server. The temporary database container was stopped after verification.

- `python -m pytest -q --disable-warnings tests/test_review_calendar.py`: **27 passed in 36.69s**. Private owner predicates/direct IDs, exact retries and tombstones, update/dismiss CAS, CSRF, real issued Player capability and forged capability rejection, strict date/time and both autumn folds, spring gap, day/total limits, pagination, worker cancel/rearm/retry, ordinary-model One-Shots, quota/tier, injected late commit failure rollback, existing-service session planning.
- `python -m pytest -q --disable-warnings tests/test_review_calendar_postgres.py`: **2 passed in 28.05s**. Four simultaneous identical note/One-Shot requests produce one row; competing note edits produce one success/one conflict; concurrent final day/campaign slot claims enforce limits; parallel SKIP LOCKED workers transition 40 reminders exactly once; an editor-held cancelled reminder is skipped and remains unannounced.
- `python -m pytest -q --disable-warnings tests/test_review_calendar_browser.py`: **2 passed in 173.96s**. Firefox desktop 1440/paper/DE and Chromium mobile 390/night/EN with touch enabled, through ordinary `/campaigns`: durable ready reminder → reload → dismiss; Enter day dialog → note create → Escape while successful response is delayed → dialog stays closed after response → reopen/focus → reload → edit/delete; planning creates a real session; One-Shot creates a real campaign/member/session; Escape returns focus to One-Shots; no page errors or horizontal overflow. Late form success/error cannot reopen a closed dialog or overwrite a later dialog. The English preference exercises the existing adapter; the new authored translations are supplied in `tools/i18n/tasks/review-calendar.json`, with generated catalog activation owned by the coordinator.
- Existing calendar regression `python -m pytest -q --disable-warnings tests/test_session_calendar.py`: **33 passed in 34.32s**.
- `python tools/calendar_reminders.py --once --config testing --limit 20`: exit 0, **`{"ready": 0}`**, isolated empty testing database. Python compilation and `git diff --check` pass. JavaScript is exercised in both browser engines; no new JS dependencies.

Browser screenshots are retained in `docs/proofs/review-calendar-20261119/`. Synthetic users/content only. They supplement behavioral assertions; they are not a live production claim. Day-dialog controls and personal toolbar buttons have minimum 44px height. Refreshing a visible tab updates the durable reminder panel; readers never advance the worker state.

The task catalog adds 74 authored DE/EN messages and overrides no existing source. The shared compiler validates catalog conflicts, completeness and placeholder parity with generated-output writes intercepted; generated bundles remain unchanged in this worktree.

Coordinator integration is exactly:

```python
# vtt/models/__init__.py
from .calendar_note import CalendarNote, CalendarOneShot

# vtt/__init__.py, alongside other registrations
from vtt.calendar_notes import calendar_notes_bp
app.register_blueprint(calendar_notes_bp)
```

Create only additive tables **`calendar_notes`** and **`calendar_one_shots`** before activation. Existing tables are not changed. Synthetic cleanup must delete `calendar_one_shots` before associated sessions/campaigns/users and `calendar_notes` before users. Existing campaign deletion is soft deletion, so its behavior remains compatible.

Worker invocation is **`python tools/calendar_reminders.py --once --limit 200`** (production configuration by default), suitable for a single host timer approximately once per minute. `--interval 60` is an optional process loop; no scheduler runs inside Gunicorn workers. The repository Dockerfile already copies the entire source tree. If the coordinator uses a different image build context, include this CLI explicitly. Callable seam: **`vtt.calendar_notes.process_due(limit=200, now=None) -> int`** inside an app context, followed by scoped-session removal in the caller. The CLI removes its session after every batch. Coordinator plans a host systemd timer invoking this function via `docker exec` instead of the CLI.

Expected product limitations are explicit: durable in-app delivery only, no closed-tab system notification. Existing campaign series represent the first autumn occurrence; the day-planning route rejects an explicit second occurrence with a clear error rather than changing it silently. Private reminders and direct One-Shots support both occurrences. Coordinator deployment, timer activation, combined integration verification and real live acceptance remain outstanding and are not claimed by this slice.
