-- M64 Migration: Asset Library Core
-- Date: 2026-03-27
-- Description: Add composite indexes to support asset library search, scope filtering, and session scoping

-- ===== Step 1: Add composite indexes for library queries =====

CREATE INDEX idx_assets_campaign_scope_created_at ON assets(campaign_id, scope, created_at DESC);
CREATE INDEX idx_assets_campaign_type_created_at ON assets(campaign_id, asset_type, created_at DESC);
CREATE INDEX idx_assets_campaign_session_created_at ON assets(campaign_id, session_id, created_at DESC);
CREATE INDEX idx_assets_campaign_deleted_created_at ON assets(campaign_id, deleted_at, created_at DESC);

-- ===== Step 2: Verification =====

SELECT COUNT(*) as asset_count FROM assets;
SELECT COUNT(*) as campaign_assets FROM assets WHERE scope = 'campaign';
SELECT COUNT(*) as session_assets FROM assets WHERE session_id IS NOT NULL;

-- ===== Step 3: Audit trail =====

INSERT INTO audit_logs (
    user_id,
    action,
    resource_type,
    timestamp,
    details
) VALUES (
    1,
    'system_migration',
    'system',
    CURRENT_TIMESTAMP,
    '{"migration": "m64_asset_library", "status": "completed"}'
);

-- ===== Rollback (if needed) =====
/*
DROP INDEX idx_assets_campaign_scope_created_at;
DROP INDEX idx_assets_campaign_type_created_at;
DROP INDEX idx_assets_campaign_session_created_at;
DROP INDEX idx_assets_campaign_deleted_created_at;
*/
