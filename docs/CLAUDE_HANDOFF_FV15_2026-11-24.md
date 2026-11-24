# Claude FV15 implementation handoff

Status: assigned Deploy implementation; not tested, integrated or delivered. Permanent. Owner explicitly requested independent Claude work after completing FV06. FV06 is live verified and its QA cleanup is complete. Codex continues FV01 and retains test execution, integration, commit/push, additive schema application, deployment and live acceptance.

Task: FV15 campaign-quota requests and explicit owner/admin review, exactly as defined in [the completed Apply](DADM_APPLY_FV15_CAMPAIGN_QUOTA_2026-11-24.md). Read AGENTS.md, CLAUDE.md and the smallest standard DAD-M Deploy runtime before edits. Later registers/this handoff supersede historical status sentences in CLAUDE.md.

Integration base: `1f9179d5b5f4f747c1f6fa9ff4da2150956bafb0`.
Worktree: `/home/admin/projects/roll-drauf-vtt-fv15-quota-20261124`.
Branch: `feat/campaign-quota-fv15-20261124`.
Coordinator: `/home/admin/projects/roll-drauf-vtt-feedback-harness-20261123`, branch `fix/feedback-harness-20261123`.

## Exclusive file ownership

New files permitted: `vtt/models/campaign_quota_request.py`, `vtt/campaign_quota.py`, `vtt/static/js/campaign-quota-ui.js`, optional `vtt/static/css/campaign-quota.css`, `tools/i18n/tasks/fv15-campaign-quota.json`, `tests/test_campaign_quota.py`, `tests/test_campaign_quota_browser.py`, `docs/DADM_DEPLOY_FV15_CAMPAIGN_QUOTA_2026-11-24.md`.

Minimal shared edits: `vtt/models/__init__.py` model import only; `vtt/__init__.py` blueprint import/register only; `vtt/review_web.py` own-profile user_id only; `vtt/static/js/vtt-main-nav.js` own-profile quota mounting hook only. Codex avoids these files during this assignment. Write all implementation, proposed tests and exact residual limitations in the Deploy handoff. Do not edit this assignment or the canonical register.

No creator/rules/sheet/inventory/progression/mapmaker edits, generated global catalog, display-preferences/CSP/auth/permissions changes, dependencies, artwork, private archives, environment/credential files, bot or production access. Never generate images or use Ducky art generatively. No nested agents or external messages. Read only relevant public repository source. No test execution, catalog building, git mutations, schema application, service changes, pushing or deployment. No Bash/code-running tools or MCP access are granted. Do not obtain more permissions or switch billing/provider. Use the existing claude.ai subscription only; record quota/access failure rather than enabling extra usage/API billing.

## Critical contract details

- Existing zero/NULL campaign quota does not mean unlimited; preserve actual User/permission semantics. Requests require an existing finite positive quota and eligible creator role, even when capacity is exhausted.
- One pending request per actor, DB-enforced; max5 requests per rolling24h including cancelled/history; strict integer totals, not bool/string, up to2147483647. Preserve default tiers/storage.
- Lock requester User before request; refresh values. Submit/cancel/reject never increase quota. Review exact owner/admin only; explicit manually chosen total and expected-current-quota compare, pending-only and exactly once. Audit in the same transaction: the existing log_audit helper commits and cannot be called midway.
- Own-only reads/cancel, server role enforcement, cookie JWT/CSRF, usable-user checks, private/no-store, strict payloads and mutation X-Quota-Account matching actor. Late profile/account-switched responses must not mount or mutate another account.
- Normal own-profile entry; truthful current/active values, request/history/cancel; server capability enables bounded owner/admin review, explicit approval/rejection, stale refresh. Authored reasons/notes use textContent and remain literal. DE/EN task fragment only; no global catalog rebuild by Claude.

## Root verification and completion gate

Codex reviews the complete diff and runs meaningful throwaway SQLite/browser checks and isolated PostgreSQL concurrent submission/review tests. Codex then builds the catalog, integrates, commits/pushes, uses the existing additive-model schema release helper, deploys only the app and verifies normal DM/Player/profile/admin journeys with synthetic actors; real users are not adjusted. No worker result is called done until root Monitor records live evidence and scoped cleanup.

Required worker return: implementation summary, changed paths, transaction/concurrency reasoning, proposed tests with explicit not-run status, additive model path, known limitations/blockers and next action for Codex. Do not stop after a proposal if the approved implementation is feasible with the permitted tools.
