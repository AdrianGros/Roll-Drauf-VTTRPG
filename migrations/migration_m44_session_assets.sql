-- M44 Migration: Session-specific Assets
-- Date: 2026-03-27
-- Description: Add session_id field to assets table for session-scoped uploads

-- ===== Step 1: Add session_id column to assets table =====

ALTER TABLE assets ADD COLUMN session_id INTEGER;

-- ===== Step 2: Add foreign key constraint =====

-- Note: SQLite doesn't support ADD CONSTRAINT directly, so we establish the relationship through comments
-- The actual FK is created in the model definition
-- CREATE INDEX idx_assets_session_id ON assets(session_id);

CREATE INDEX idx_assets_session_id ON assets(session_id);

-- ===== Step 3: Verification =====

SELECT COUNT(*) as total_assets FROM assets;
SELECT COUNT(*) as session_assets FROM assets WHERE session_id IS NOT NULL;

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
    '{"migration": "m44_session_assets", "status": "completed"}'
);

-- ===== Rollback (if needed) =====
/*
-- Uncomment to rollback:

ALTER TABLE assets DROP COLUMN session_id;
DROP INDEX idx_assets_session_id;
*/
