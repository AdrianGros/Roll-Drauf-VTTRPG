# M4 Deploy Output: Campaign and Session Core Loop Implementation

```
artifact: deploy-output
milestone: M4
phase: DEPLOY
status: complete
date: 2026-03-26
```

---

## Input Summary

- Closed Apply baseline:
  - `milestone_m4_apply_output.md`
- Approved execution:
  - `APPROVED: M4 Deploy`
- Scope implemented:
  - Full campaign/session endpoint contract
  - Invite duplication guardrails
  - Campaign and lobby core UI action wiring
  - Backend test coverage expansion

---

## Implementation Artifacts

| Artifact | Purpose | State |
|---|---|---|
| `vtt_app/campaigns/routes.py` | Complete campaign/member/session API surface with auth + role guards | implemented |
| `vtt_app/templates/campaigns.html` | Real create/join/view/delete/invite/session lifecycle UI actions | implemented |
| `vtt_app/templates/lobby.html` | Real create/join/enter/delete lobby actions | implemented |
| `tests/test_campaigns.py` | Expanded endpoint coverage for M4 contract and negative paths | implemented |
| `milestone_m4_deploy_output.md` | Deploy execution and evidence record | implemented |

---

## Delivered Backend Surface

Implemented endpoints:

1. `GET /api/campaigns`
2. `POST /api/campaigns`
3. `GET /api/campaigns/<campaign_id>`
4. `GET /api/campaigns/mine`
5. `PUT /api/campaigns/<campaign_id>`
6. `DELETE /api/campaigns/<campaign_id>` (soft delete)
7. `POST /api/campaigns/<campaign_id>/invite`
8. `POST /api/campaigns/<campaign_id>/accept-invite`
9. `GET /api/campaigns/<campaign_id>/members`
10. `POST /api/campaigns/<campaign_id>/sessions`
11. `GET /api/campaigns/<campaign_id>/sessions`
12. `POST /api/campaigns/<campaign_id>/sessions/<session_id>/start`
13. `POST /api/campaigns/<campaign_id>/sessions/<session_id>/end`

Applied guardrails:

- Cookie-authenticated access using existing JWT cookie stack.
- Active-member checks for protected reads.
- DM/owner checks for campaign/session mutations.
- Owner-only soft delete.
- Duplicate invite/member handling with deterministic `409`.
- Session transition constraints:
  - `scheduled -> in_progress -> completed`
  - prevent parallel active sessions in one campaign.

---

## Frontend Wiring Delivered

`campaigns.html`:

- New campaign creation wired to `POST /api/campaigns`.
- Join flow wired to `POST /api/campaigns/<id>/accept-invite` (token prompt).
- View flow wired to `GET /api/campaigns/<id>` with in-page detail panel.
- Delete flow wired to `DELETE /api/campaigns/<id>`.
- DM controls wired:
  - invite player via `POST /invite`
  - create session via `POST /sessions`
  - start/end session via lifecycle endpoints.
- Query-param deep-link support:
  - `?campaign_id=<id>` auto-opens campaign detail.

`lobby.html`:

- Create campaign wired to `POST /api/campaigns`.
- Join by campaign ID + token wired to `POST /accept-invite`.
- Enter campaign navigates to `/campaigns?campaign_id=<id>`.
- Owner delete action wired to `DELETE /api/campaigns/<id>`.

---

## Verification Evidence

Executed:

- `.\.venv\Scripts\python.exe -m pytest -q tests\test_campaigns.py`
  - Result: `20 passed`
- `.\.venv\Scripts\python.exe -m pytest -q tests\test_auth.py tests\test_campaigns.py tests\test_characters.py`
  - Result: `50 passed`

Notes:

- Existing SQLAlchemy relationship overlap warnings remain (pre-existing technical debt).
- Existing `datetime.utcnow()` deprecation warnings remain across modules.
- Existing JWT test-key length warnings remain in testing config.

---

## Acceptance Criteria Check

- [x] AC-M4-01: Endpoint contract implemented with happy/negative path coverage.
- [x] AC-M4-02: DM/owner authorization enforced server-side on mutations.
- [x] AC-M4-03: Duplicate invite/membership path handled without integrity crash path.
- [x] AC-M4-04: Soft delete implemented (`deleted_at` set).
- [x] AC-M4-05: Session lifecycle start/end transitions implemented and tested.
- [x] AC-M4-06: Campaigns/lobby core actions no longer placeholder alerts.
- [x] AC-M4-07: Expanded M4 test coverage added and passing.
- [x] AC-M4-08: Realtime campaign/session events remain deferred to M5.

---

## Follow-up (Non-blocking)

- Replace legacy `Query.get()` with `db.session.get(...)`.
- Normalize UTC handling (`datetime.now(timezone.utc)` pattern).
- Clean relationship overlap warnings with explicit `overlaps=` or back_populates strategy.
