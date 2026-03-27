# M16 Apply Output: Session Workspace and Asset Upload Delivery Plan

```
artifact: apply-output
milestone: M16
phase: APPLY
status: complete
date: 2026-03-27
```

---

## Chosen Implementation

1. Introduce an **Asset Library** backend foundation:
   - New DB entity for uploaded assets (owner, campaign scope, type, mime, size, dimensions, storage path, checksum).
   - Asset types: `map_background`, `token_image`.
   - Soft-delete + audit metadata.

2. Implement authenticated **multipart upload APIs** with strict validation:
   - `POST /api/assets/upload` (DM/member scoped by policy).
   - `GET /api/assets` (filtered by campaign/scope/type).
   - `POST /api/campaigns/<id>/maps` updated to accept either `background_asset_id` or legacy `background_url`.
   - Token creation/update to support `token_asset_id` metadata reference.

3. Add secure **asset serving route** with authorization:
   - `GET /api/assets/<asset_id>/content` validates membership/scope before file delivery.
   - Never expose raw filesystem paths in client payloads.

4. Add minimal **session workspace UX** in existing UI:
   - Campaign detail panel: map upload + map create from uploaded asset.
   - Play UI: token image upload/select flow for DM/operator.
   - Preserve current session state and realtime behavior; extend payloads with optional asset refs.

5. Ship full **test slice** for upload + session integration:
   - API tests: success paths, MIME/size rejection, authz boundaries, campaign isolation.
   - Session/play tests: uploaded map appears in bootstrap state and active layer flow.
   - Realtime tests: token events include consistent token image reference.

---

## Concrete Delivery Plan (Execution Order)

1. **Schema + Config**
   - Add `Asset` model and indexes.
   - Add upload config keys (`UPLOAD_ROOT`, size caps, allowed MIME lists).
   - Add migration strategy (or controlled bootstrap path for current auto-schema mode).

2. **Asset Service Layer**
   - Implement upload validation and deterministic filename generation.
   - Persist metadata + storage path.
   - Centralize authorization checks for campaign/user scope.

3. **API Integration**
   - Build `/api/assets/*` routes.
   - Extend map/token routes to accept asset references.
   - Keep `background_url` and `token_url` backward-compatible during transition.

4. **Frontend Integration**
   - Add upload controls in campaign detail and play runtime.
   - Add list/select assets by type.
   - Render map background/token image from authorized asset endpoints.

5. **Verification + Hardening**
   - Add tests for validation and scope leakage.
   - Add rate limits for upload and asset listing endpoints.
   - Add basic operational checks (disk path exists, max file size behavior).

---

## Acceptance Criteria

- DM can upload a map image and create/activate a session map without external URL hosting.
- DM (and policy-allowed player) can upload token images and attach them to tokens.
- Assets are only accessible to authorized campaign members.
- Session bootstrap/play state includes consistent asset references and remains realtime-stable.
- Existing campaigns using `background_url`/`token_url` continue to work.

---

## Out of Scope for M16

- CDN optimization and signed URL offloading.
- Image editing/cropping UI.
- Advanced asset tagging/search and cross-campaign marketplace features.
- Automated virus scanning pipeline (can be a follow-up milestone).

