# FV15 campaign-quota requests and explicit review

Status: Discover closed; Apply approved for isolated implementation by Claude after FV06 cleanup. Permanent. Owner instruction: finish the current step, then hand Claude independent work without interrupting Codex. Codex continues FV01 character language; FV15 owns the account/profile quota surfaces below. Codex retains test execution, integration, pushes, schema application, live delivery and acceptance.

## Facts and scope

`vtt/static/js/vtt-main-nav.js:openOwnProfile` provides the normal profile entry and fetches `/api/review-web/profile`. That response currently has username/counts but no actor ID or quota flow. User already has `profile_tier`, nullable integer `active_campaigns_quota`, `platform_role` and canonical active-campaign counting; preserve their existing meanings. The platform role decorator checks exact membership, so review must explicitly allow both owner and admin. The existing audit helper commits immediately; it must not split the new transaction. No campaign/table role or Player context is elevated by quota management.

Implement the request/approval workflow only. No automatic increase on submission, new billing, new donor/Donutarian tier, new default slot count, storage increase, external message or alteration of real users. Unavailable rules content is owner-deferred; Ducky artwork must never enter image generation/generative workflows. No artwork or bot/lane access is needed.

## Model and transaction contract

Add one table/model `CampaignQuotaRequest`, integer ID, requester user FK, submitted/current finite quota snapshot, desired total, reason(max500), status(pending/approved/rejected/cancelled), created time, optional reviewer FK/note(max500), decision time and approved total. Use repository UTC helpers. A nullable unique integer `pending_key` equals requester ID while pending and is NULL when terminal, with a DB check for that relationship. This provides one pending request per user on SQLite and PostgreSQL while retaining terminal history. Keep User's existing columns unchanged.

Eligible requesters are usable accounts satisfying the existing creator-role condition (DM/headmaster profile, or platform owner/admin) and a finite positive current campaign quota. Exhausted quotas must still allow a request: do not use can_create_campaign() as the request eligibility check, because it includes current capacity. Actual source User.can_create_campaign() returns False for zero/NULL; preserve that behavior, do not invent unlimited campaign access, and display a NULL quota as unassigned rather than unlimited. Existing tier/default/storage semantics and any older inconsistencies stay unchanged; report them rather than silently fixing them. Desired total must be a strict JSON integer (not bool/string), greater than the live finite quota and representable in the existing DB integer column (1..2147483647). This is a request, not an entitlement. At most5 submissions per rolling24h, counting terminal/cancelled requests; serialize per-user submissions. No bound becomes a new default allowance.

Lock order for submission/cancellation/review: requester User first, then existing Request row when applicable, refreshing live values. One DB transaction performs each action. Unique pending key handles duplicate concurrent submissions. Request/cancel/reject changes no quota. Approval is available only to usable platform owner/admin accounts, requires an explicit manually chosen final total greater than the live finite quota and at least the current active count, and compares an expected current quota supplied by the review form. Stale quota or nonpending status returns409 without mutation. Concurrent/double review must update quota once only. Never modify profile/platform/game roles or storage. Append AuditLog rows in the same transaction; do not call the commit-owning audit helper mid-transaction. Use requester as audit subject and verified reviewer/actor as performer, with old/new quota and request ID, no credentials/email.

## API

New blueprint `/api/campaign-quota`:

- GET `/requests`: authenticated usable actor only; own current quota/active count/eligibility/review capability and own latest20 requests, with `accountId`. No other user's records.
- POST `/requests`: desired_total/reason; derive requester from cookie JWT. Return pending receipt/current unchanged quota. Reject ineligible, invalid, duplicate pending or rate-limited requests explicitly.
- POST `/requests/<int:id>/cancel`: own pending request only; other/unknown IDs give the same404. Terminal repeats are a conflict or explicit unchanged receipt, never quota mutations.
- GET `/review-requests`: exact platform owner/admin only, bounded50 rows, pending by default with optional explicit closed-history view. Return minimal requester ID/username and live quota/count, never email or private campaign content.
- POST `/review-requests/<int:id>/decision`: approve/reject, expected_current_quota, optional approved_total/reviewer_note. Server enforces roles and atomic state/quota checks; no automatic retry of a stale mutation.

Cookie JWT/CSRF and authenticated usable-user checks stay authoritative. All responses private/no-store. Require `X-Quota-Account` matching the authenticated actor on mutations; mismatch/missing header rejects before changing anything. GET responses carry accountId. Add only `user_id` to the existing own-profile response so a late quota response cannot mount into another account's open profile. Strict payload/type/length validation and safe structured error codes; no user-text HTML or generic translation of authored reasons.

## UI

Mount a new `campaign-quota-ui.js` module below existing own-profile counts. Display actual current limit and active count. Eligible users can request a desired total/reason, see that submission does not change their limit, view own status/history and cancel a pending request. No fabricated donor entitlement or storage action. Owner/admin capability from the server exposes “Anfragen prüfen” in the same ordinary profile entry, with a bounded review list, requested/current/active counts and explicit approve/reject controls. The reviewer manually confirms final total; clear stale/conflict feedback requests refresh, without replaying approval. Keep existing profile counts/auth/navigation intact.

Use existing styles plus a small scoped stylesheet if needed, native controls, DE/EN task messages, safe textContent and normal Auth headers. Compare expected account IDs before rendering or mutating; never mount a late response after profile closes/account changes. A failed quota panel must not erase the existing profile counts. Layout works at390/1440. No outside emails/Discord posts or notifications are sent by this implementation.

## File ownership and handoff

Claude may create/edit only:

- New `vtt/models/campaign_quota_request.py`, `vtt/campaign_quota.py`, `vtt/static/js/campaign-quota-ui.js`, optional `vtt/static/css/campaign-quota.css`.
- Minimal registration imports/blueprint wiring in `vtt/models/__init__.py` and `vtt/__init__.py`.
- `vtt/review_web.py`: add own-profile user_id only. `vtt/static/js/vtt-main-nav.js`: quota-module mounting hook inside own profile only.
- `tools/i18n/tasks/fv15-campaign-quota.json`, new `tests/test_campaign_quota.py` and `tests/test_campaign_quota_browser.py`, `docs/DADM_DEPLOY_FV15_CAMPAIGN_QUOTA_2026-11-24.md`.

No creator/rules/sheet/progression/inventory, mapmaker, shared display-preferences/CSP/auth/permission logic, global generated catalog, canonical plan/register, bot files, production, private archives, credentials or image files. No dependencies. Codex avoids the owned files until handoff; other packets are not silently added. Exact branch/worktree/base are in the coordinator handoff.

Claude writes implementation/tests and a precise handoff, without running tests, building catalogs, committing/pushing, applying schema or accessing production. A medium/high implementation blocker is recorded for Codex, not bypassed with a changed architecture. No nested agents.

## Verification and rollout reserved to Codex

Meaningful API/browser cases cover own/other/anonymous/disabled accounts, exact review roles, no quota on request/cancel/reject, strict validation, pending uniqueness/rate, stale/double review, one successful manual increase/audit, account switch and literal user notes. SQLite fixtures are throwaway; concurrency requires isolated PostgreSQL on its own port, never a lane/live URL. Tests are not yet run or claimed green.

Provide the additive model path for the existing `release_committed_vtt.py schema --model` workflow; no migration is executed by Claude. Codex reviews, runs tests/catalog checks, commits/pushes, backs up real DB, applies only reviewed additive schema, protects prior image/config, deploys only app and verifies normal profile requests/review using isolated synthetic users (no real quota changes), then removes QA rows/credentials. Full FV15 completion belongs to that later Monitor.
