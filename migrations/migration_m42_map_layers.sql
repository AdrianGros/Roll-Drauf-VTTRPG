-- M42 Migration: Session Map Layers
-- Date: 2026-03-27
-- Description: Add support for layered maps in sessions with FOW support

-- ===== Step 1: Create session_map_layers table =====

CREATE TABLE session_map_layers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    layer_name VARCHAR(100) NOT NULL,
    layer_order INTEGER NOT NULL,

    -- Map asset reference (M44)
    asset_id INTEGER,

    -- Map dimensions and grid
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    grid_size INTEGER DEFAULT 70,

    -- Visibility and effects
    is_visible BOOLEAN DEFAULT TRUE,
    fog_of_war_enabled BOOLEAN DEFAULT FALSE,
    fog_of_war_data JSON,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES game_sessions(id),
    FOREIGN KEY (asset_id) REFERENCES assets(id)
);

-- ===== Step 2: Create indexes =====

CREATE INDEX idx_session_map_layers_session_id ON session_map_layers(session_id);
CREATE INDEX idx_session_map_layers_asset_id ON session_map_layers(asset_id);
CREATE INDEX idx_session_map_layer_order ON session_map_layers(session_id, layer_order);

-- ===== Step 3: Verification =====

SELECT COUNT(*) as layer_count FROM session_map_layers;

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
    '{"migration": "m42_map_layers", "status": "completed"}'
);

-- ===== Rollback (if needed) =====
/*
-- Uncomment to rollback:

DROP TABLE session_map_layers;

DROP INDEX idx_session_map_layers_session_id;
DROP INDEX idx_session_map_layers_asset_id;
DROP INDEX idx_session_map_layer_order;
*/
