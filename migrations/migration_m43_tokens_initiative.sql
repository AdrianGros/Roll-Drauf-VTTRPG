-- M43 Migration: Session Tokens and Initiative
-- Date: 2026-03-27
-- Description: Add token placement and initiative tracking for sessions

-- ===== Step 1: Create session_tokens table =====

CREATE TABLE session_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    layer_id INTEGER NOT NULL,
    character_id INTEGER,

    name VARCHAR(100) NOT NULL,

    -- Position and dimensions
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    size INTEGER DEFAULT 70,

    -- Visual properties
    color VARCHAR(7) DEFAULT '#FF0000',
    rotation INTEGER DEFAULT 0,

    -- Visibility
    is_visible_to_players BOOLEAN DEFAULT TRUE,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES game_sessions(id),
    FOREIGN KEY (layer_id) REFERENCES session_map_layers(id),
    FOREIGN KEY (character_id) REFERENCES characters(id)
);

-- ===== Step 2: Create session_initiative table =====

CREATE TABLE session_initiative (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    character_id INTEGER,

    character_name VARCHAR(100) NOT NULL,
    initiative_roll INTEGER NOT NULL,
    turn_order INTEGER NOT NULL,

    is_current_turn BOOLEAN DEFAULT FALSE,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES game_sessions(id),
    FOREIGN KEY (character_id) REFERENCES characters(id)
);

-- ===== Step 3: Create indexes =====

CREATE INDEX idx_session_tokens_session_id ON session_tokens(session_id);
CREATE INDEX idx_session_tokens_layer_id ON session_tokens(layer_id);
CREATE INDEX idx_session_tokens_character_id ON session_tokens(character_id);
CREATE INDEX idx_session_tokens_location ON session_tokens(session_id, layer_id);

CREATE INDEX idx_session_initiative_session_id ON session_initiative(session_id);
CREATE INDEX idx_session_initiative_character_id ON session_initiative(character_id);
CREATE INDEX idx_session_initiative_order ON session_initiative(session_id, turn_order);

-- ===== Step 4: Verification =====

SELECT COUNT(*) as token_count FROM session_tokens;
SELECT COUNT(*) as initiative_count FROM session_initiative;

-- ===== Step 5: Initialize audit log for migration =====

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
    '{"migration": "m43_tokens_initiative", "status": "completed"}'
);

-- ===== Rollback (if needed) =====
/*
-- Uncomment to rollback:

DROP TABLE session_tokens;
DROP TABLE session_initiative;

DROP INDEX idx_session_tokens_session_id;
DROP INDEX idx_session_tokens_layer_id;
DROP INDEX idx_session_tokens_character_id;
DROP INDEX idx_session_tokens_location;

DROP INDEX idx_session_initiative_session_id;
DROP INDEX idx_session_initiative_character_id;
DROP INDEX idx_session_initiative_order;
*/
