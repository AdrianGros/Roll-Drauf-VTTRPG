# FV15 Deploy handoff: campaign-quota requests and explicit review

Status: implemented by Claude in the assigned worktree; **not run, not tested, not integrated, not delivered.** Permanent record. Codex owns test execution, catalog build, integration, commit/push, additive schema application, deployment and live acceptance. FV15 is not done until the root Monitor records live evidence and scoped cleanup.

- Contract: [DADM_APPLY_FV15_CAMPAIGN_QUOTA_2026-11-24.md](DADM_APPLY_FV15_CAMPAIGN_QUOTA_2026-11-24.md), [CLAUDE_HANDOFF_FV15_2026-11-24.md](CLAUDE_HANDOFF_FV15_2026-11-24.md)
- Integration base: `1f9179d5b5f4f747c1f6fa9ff4da2150956bafb0`
- Worktree/branch: `/home/admin/projects/roll-drauf-vtt-fv15-quota-20261124`, `feat/campaign-quota-fv15-20261124`
- Tools used: Read/Write/Edit/Grep/Glob only, on the existing Claude subscription. No execution, git mutation, network, production, bot/lane, artwork, credentials or nested agents.

## Changed paths

New (owned):

- `vtt/models/campaign_quota_request.py`: `CampaignQuotaRequest` model, self-contained so the additive schema helper can load it
- `vtt/campaign_quota.py`: blueprint `/api/campaign-quota`
- `vtt/static/js/campaign-quota-ui.js`: profile panel and owner/admin review
- `vtt/static/css/campaign-quota.css`: small stylesheet scoped to `.cq-*`, loaded on demand
- `tools/i18n/tasks/fv15-campaign-quota.json`: 56 DE/EN entries
- `tests/test_campaign_quota.py`: API tests plus PostgreSQL concurrency tests that skip unless enabled
- `tests/test_campaign_quota_browser.py`: Playwright journeys
- `docs/DADM_DEPLOY_FV15_CAMPAIGN_QUOTA_2026-11-24.md` (this file)

Minimal shared edits:

- `vtt/models/__init__.py`: one model import line
- `vtt/__init__.py`: import and register `campaign_quota_bp` (after `calendar_notes_bp`)
- `vtt/review_web.py`: the own-profile response gains only `user_id=user.id`
- `vtt/static/js/vtt-main-nav.js`: `mountQuota()` hook, called after the counts render in `openOwnProfile`

Not touched: User columns, permissions/auth/CSP/display preferences, creator/rules/sheet/inventory/progression/mapmaker, the generated catalog, templates, dependencies, the canonical plan/register and this assignment.

## Implementation summary

### Model `campaign_quota_requests`

Columns:

- `id`, `requester_id` (FK users, not null)
- `current_quota` (snapshot at submission, not null), `desired_total`
- `reason` String(500) not null
- `status` (pending/approved/rejected/cancelled)
- `pending_key` Integer UNIQUE nullable
- `created_at`, `reviewer_id` (FK users), `reviewer_note` String(500), `decided_at`, `approved_total`

Database constraints:

- `ck_campaign_quota_request_status`: status in the enum
- `ck_campaign_quota_request_pending_key`: `(pending AND pending_key = requester_id) OR (not pending AND pending_key IS NULL)`. One pending request per account on SQLite and PostgreSQL, because NULLs are not unique-conflicting; terminal history is kept.
- `ck_campaign_quota_request_totals`: `current_quota > 0 AND desired_total > current_quota`
- `ck_campaign_quota_request_approved_total`: approved_total only when approved
- Indexes on (requester_id, created_at) and (status, created_at)

### Eligibility

A usable account is eligible when:

- it has the existing creator condition (`profile_tier in {dm, headmaster}` or `platform_role in {admin, owner}`), mirroring `permissions.can_create_campaign` minus the capacity check, and
- its live quota is a finite positive integer below 2147483647.

Other details:

- An exhausted capacity still allows a request.
- NULL means `quota_unassigned` (shown as "nicht zugewiesen", never as unlimited); 0 or negative means `quota_not_positive`.
- `User.can_create_campaign()` is unchanged.
- The active count uses canonical `User.get_active_campaigns_count()` (owner_id, status='active').

### API (all responses `Cache-Control: private, no-store`, structured `error` codes)

- **`GET /requests`**: usable actor only. Returns `accountId`, `quota{current, assigned, active_count}`, `eligible`, `ineligible_reason`, `can_review` (exact owner/admin), `limits{max_total, text_max, per_24h, used_24h}` and the own latest 20 requests. No other account's data.
- **`POST /requests`**: exactly `{desired_total, reason}`.
  - `desired_total` must be strict `type(...) is int`, so bool, string and float are rejected; range 1..2147483647 and above the live quota.
  - `reason` must be 1–500 characters after trim, with CR/LF normalised and control characters rejected.
  - Failure codes: 403 for ineligible or mismatched header, 409 `pending_request_exists`, 429 `request_rate_limited` (5 per rolling 24 h, counting every status).
  - Success returns 201 with `quota_changed:false`.
- **`POST /requests/<id>/cancel`**: empty body or `{}`.
  - Own pending requests only. Another account's ID and an unknown ID return the identical 404 `request_not_found`.
  - A terminal repeat returns 409 `request_not_pending` with `quota_changed:false`.
- **`GET /review-requests?view=pending|closed`**: exact owner/admin. Unknown parameters or values return 400.
  - At most 50 rows plus a `complete` flag.
  - Pending is sorted oldest first; closed is sorted by decision time, newest first.
  - Each row carries requester `{id, username}`, the snapshot, desired total, reason, any decision fields, and live `{current, assigned, active_count}` from one grouped count query.
  - No email and no campaign content.
- **`POST /review-requests/<id>/decision`**: `{decision, expected_current_quota}` plus optional `approved_total` and `reviewer_note`.
  - Approve requires a strict integer `approved_total` that is above the live finite quota and at least the active count.
  - Reject must not carry `approved_total`.
  - `expected_current_quota` is a strict integer ≥ 0 or null and must equal the live value.
  - Stale or non-pending requests return 409 (`quota_changed`, `request_not_pending`, `quota_not_finite`) with `mutated:false`.
  - No retry on the server or the client.

All mutations need `X-Quota-Account` to equal the cookie-JWT identity exactly, otherwise 403 `account_mismatch` before any DB lock. `@jwt_required()` keeps CSRF authoritative in production (`JWT_COOKIE_CSRF_PROTECT=True`). The mutations have modest per-route Flask-Limiter limits; the limiter is disabled in tests.

### Audit

`AuditLog` rows are added in the same transaction, before the single commit. `log_audit` is not used because it commits on its own.

- Actions: `campaign_quota_requested`, `campaign_quota_request_cancelled`, `campaign_quota_request_approved`, `campaign_quota_request_rejected`.
- `user_id` is the requester (subject); `performed_by_id` is the verified actor or reviewer.
- `details` holds `{request_id, old_quota, new_quota[, desired_total]}`. No reason text, email or credentials.

### UI

`openOwnProfile` renders the counts, then inserts a hidden `section.cq-panel` before the close button. It lazy-loads `/static/js/campaign-quota-ui.js` (no template edits) and calls `VTTCampaignQuota.mount(host, profile.user_id)`.

The module's own fetch:

- uses `Auth.buildHeaders` (CSRF) without the `X-VTT-Context`/`X-VTT-Tab` table context
- adds `X-Quota-Account` on mutations
- does one refresh retry on 401
- rejects any response whose `accountId` differs from the profile account

Rendering and state:

- It shows the current limit and active count, a request form when eligible with nothing pending, history with a cancel action for pending requests, and "Anfragen prüfen" only when the server returns `can_review`.
- Review shows requested, submitted, current and active values. The reviewer types the total into an empty field. "Genehmigen …" opens an inline confirmation ("Limit von X von A auf B setzen?") before the only approve request.
- On a stale or 404 response, the entry stays locked and shows "Liste neu laden". The decision is never replayed.
- Late responses are dropped after the dialog closes (`host.isConnected` plus sequence counters). An account mismatch replaces the panel with a notice and no controls. Any other load failure removes only the panel, so the counts stay.
- All authored reasons, notes and usernames are written with `textContent`, and authored text is never passed to `VTTUi`.
- Ineligible non-reviewers get text only: no `dl` and no buttons. This keeps the strict locators in `tests/test_review_ui_browser.py` (`#reviewOwnProfile button`, `#reviewOwnProfile dl`) unambiguous.

## Transaction and concurrency reasoning

Every mutation is one transaction. Lock order is the requester `User` row first (`with_for_update`, `populate_existing`), then the request row (`with_for_update().populate_existing()`). Live values are re-read after locking.

- **Submit.** The user-row lock serialises one account's submissions on PostgreSQL, so the pending check and the 24 h count are consistent. The unique `pending_key` is the final DB guard. An `IntegrityError` is mapped to 409 only if a pending row really exists; otherwise it is re-raised.
- **Cancel and review compare-and-set.** State changes run as conditional `UPDATE … WHERE id=? AND status='pending'`. The quota change runs as `UPDATE users … WHERE id=? AND active_campaigns_quota=<locked live value>`. Each update must affect exactly one row; anything else rolls back the whole transaction and returns 409. This keeps double approval, approve vs. cancel, and approve vs. an external quota edit exactly-once even where row locks are weaker (SQLite ignores `FOR UPDATE`).
- **Rollback scope.** If the request CAS fails after the quota CAS succeeded, the rollback reverts both.
- **Reviewer row.** The reviewer row is read without a lock (role and usability are checked at request time). When a reviewer reviews their own request, the same row is locked once.
- **Unchanged data.** Submit, cancel and reject never write `active_campaigns_quota`. No profile, platform or game role and no storage field is written.

## Proposed tests (NOT RUN)

`tests/test_campaign_quota.py` runs on in-memory SQLite:

- own state, privacy and NULL-as-unassigned
- own-only history with no email
- anonymous 401 on all five routes
- suspended, deactivated, inactive and marked-for-deletion accounts get 401
- profile `user_id`
- ineligibility matrix: player, moderator, NULL headmaster, zero quota
- eligible submission, including exhausted capacity: quota unchanged, audit subject/performer correct
- 18 strict payload variants
- non-object bodies
- INT_MAX accepted
- literal HTML/placeholder reason
- account-header variants
- duplicate pending → 409
- direct DB unique and check-constraint violations
- rolling 24 h limit including cancelled history, and expiry of the window
- cancel: own-only identical 404, terminal 409, audit, resubmission afterwards
- cancel needs the header and an empty body
- review list: forbidden for dm/player/moderator/headmaster; minimal live data for owner/admin; strict query; bounded to 50
- approval: once, with audit, roles/storage untouched, double review 409, note visible to the requester
- rejection keeps the quota
- stale expected quota → 409, then success with a fresh value
- quota NULLed after the request → approve 409 / reject allowed
- 14 strict decision payloads
- approved total below the active count
- non-reviewers 403
- reviewer header mismatch and unknown ID
- a cancelled request cannot be approved

PostgreSQL (skipped unless `VTT_FV15_PG_URL` points to an isolated throwaway DB on its own port; the fixture runs `drop_all`/`create_all` on it):

- 8 concurrent submissions → exactly one 201 and seven 409
- 6 concurrent approvals → one 200, quota 7, one audit row
- cancel vs. approve race → one 200 and one 409, with a consistent terminal state

`tests/test_campaign_quota_browser.py` (Playwright, reuses `QuietHandler`):

- DM request and cancel: client validation, literal reason with no injected `img`/handler, quota unchanged
- ineligible player sees text only, with exactly one dialog button and one `dl`
- owner manual-total approval: empty input, inline confirmation, exactly one decision request with the exact payload and header, audit
- stale review shows the conflict, makes no replay, and reload shows the fresh value
- rejection with a literal note seen by the requester
- foreign-`accountId` response is not rendered
- late response after close does not mount
- 500 keeps the counts
- layout at 390/1440 has no dialog or page overflow

## Known limitations, blockers and decisions left to Codex/owner

1. **Existing test needs a one-line update (outside my ownership).** `tests/test_review_web.py:60` asserts exact equality of the profile JSON and will fail until `user_id=<id>` is added to the expected dict. Codex should update it during integration.
2. **Catalog.** The task fragment is not compiled into `vtt/static/js/ui-catalog.js`, so the UI shows German literals in both locales until Codex runs the build.
   - Before writing it I checked the main inventory and extras for collisions.
   - Four strings are reused from existing entries and deliberately left out of the fragment: "Ablehnen", "Ansicht", "Dafür fehlt dir die Berechtigung.", "Die Anfrage ist fehlgeschlagen. Bitte versuche es erneut."
   - If the builder reports a "Conflicting task translation", remove that entry from the fragment rather than changing the existing translation.
3. **Existing inconsistencies (reported, not fixed).**
   - New headmaster accounts get `active_campaigns_quota=None` (`vtt/auth/routes.py:186`), and `User.can_create_campaign()` treats that as "cannot create". FV15 therefore shows headmasters as "nicht zugewiesen" and they cannot request.
   - The `vtt/campaigns` creation routes have no quota check; only `vtt/calendar_notes.py` and the permission summary use `can_create_campaign`.
   - `get_active_campaigns_count` counts `status='active'` without excluding `deleted_at`, while the profile's "Eigene Kampagnen" excludes deleted campaigns but includes paused/archived ones. The two numbers can differ.
4. **Open owner question.** Self-review is allowed: an owner/admin can approve their own request, because the Apply only requires owner/admin. Approval also does not re-check whether the requester is still usable or eligible. Both are explicit decisions for the owner if a restriction is wanted.
5. **SQLite.** `FOR UPDATE` is ignored there. The unique key and CAS updates still give one pending request and exactly-once review. The 5-per-24 h count could be exceeded by at most an interleaved submit/cancel race on SQLite only; production PostgreSQL serialises on the user row.
6. **Client.** Native `type=number` inputs are additionally checked with a digit regex; server validation stays authoritative.
7. **Notifications.** None. Requesters see the outcome the next time they open their profile.

## Additive model path

For the existing workflow: `tools/release_committed_vtt.py schema <release-dir> --model vtt/models/campaign_quota_request.py`.

The file imports only `vtt.extensions.db` and `vtt.utils.time.utcnow`, so it runs against the prior image. It creates only `campaign_quota_requests` with its constraints and indexes. No User column changes. No migration was executed by Claude.

## Next action for Codex

1. Review the full diff against base `1f9179d5b`.
2. Update `tests/test_review_web.py:60` for `user_id`.
3. Run `tests/test_campaign_quota.py`, `tests/test_review_web.py`, `tests/test_review_ui_browser.py` and `tests/test_campaign_quota_browser.py`.
4. Run the PG tests with an isolated `VTT_FV15_PG_URL`.
5. Build/check the i18n catalog.
6. Integrate, commit and push.
7. Back up the DB, then apply the additive model above.
8. Deploy the app only.
9. Verify the DM request/cancel, Player text-only and owner/admin review journeys with synthetic actors (no real quota changes).
10. Remove the QA rows and credentials, and record the Monitor evidence.
