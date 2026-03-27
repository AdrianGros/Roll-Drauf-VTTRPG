-- M19 Migration: Add Asset model for file storage management
-- Date: 2026-03-27
-- Description: Create assets table for generic file storage (maps, tokens, handouts, images)

-- ===== Step 1: Create assets table =====

CREATE TABLE assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    uploaded_by INTEGER NOT NULL,

    -- File metadata
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(50) NOT NULL,
    size_bytes INTEGER NOT NULL,
    checksum_md5 VARCHAR(32),

    -- Storage location
    storage_key VARCHAR(255) UNIQUE,
    storage_provider VARCHAR(20) DEFAULT 'local',

    -- Versioning
    asset_version INTEGER DEFAULT 1,
    parent_asset_id INTEGER,

    -- Asset classification
    asset_type VARCHAR(50) NOT NULL,
    scope VARCHAR(20) DEFAULT 'campaign',
    is_public BOOLEAN DEFAULT FALSE,

    -- Optional thumbnail
    thumbnail_key VARCHAR(255),

    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME,

    -- Foreign keys
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY (uploaded_by) REFERENCES users(id),
    FOREIGN KEY (parent_asset_id) REFERENCES assets(id)
);

-- ===== Step 2: Create indexes for performance =====

CREATE INDEX idx_assets_campaign_id ON assets(campaign_id);
CREATE INDEX idx_assets_uploaded_by ON assets(uploaded_by);
CREATE INDEX idx_assets_mime_type ON assets(mime_type);
CREATE INDEX idx_assets_asset_type ON assets(asset_type);
CREATE INDEX idx_assets_scope ON assets(scope);
CREATE INDEX idx_assets_checksum ON assets(checksum_md5);
CREATE INDEX idx_assets_created_at ON assets(created_at);
CREATE INDEX idx_assets_deleted_at ON assets(deleted_at);

-- ===== Step 3: Verification =====

SELECT COUNT(*) as asset_count FROM assets;
SELECT COUNT(DISTINCT mime_type) as mime_types FROM assets;

-- ===== Step 4: Initialize audit log for migration =====

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
    '{"migration": "m19_add_assets", "status": "completed"}'
);

-- ===== Rollback (if needed) =====
/*
-- Uncomment to rollback:

DROP TABLE assets;

DROP INDEX idx_assets_campaign_id;
DROP INDEX idx_assets_uploaded_by;
DROP INDEX idx_assets_mime_type;
DROP INDEX idx_assets_asset_type;
DROP INDEX idx_assets_scope;
DROP INDEX idx_assets_checksum;
DROP INDEX idx_assets_created_at;
DROP INDEX idx_assets_deleted_at;
*/
