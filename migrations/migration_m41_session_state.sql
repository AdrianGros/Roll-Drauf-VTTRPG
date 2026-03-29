-- M41 Migration: Session State Machine
-- Date: 2026-03-27
-- Description: Add session state machine, player management, and archival support

-- ===== Step 1: Add columns to game_sessions table =====

ALTER TABLE game_sessions ADD COLUMN session_state VARCHAR(20) DEFAULT 'preparing' CHECK(session_state IN ('preparing', 'active', 'paused', 'ended', 'archived'));
ALTER TABLE game_sessions ADD COLUMN player_limit INTEGER DEFAULT 6;
ALTER TABLE game_sessions ADD COLUMN current_players_count INTEGER DEFAULT 0;
ALTER TABLE game_sessions ADD COLUMN session_password VARCHAR(100);
ALTER TABLE game_sessions ADD COLUMN paused_at DATETIME;
ALTER TABLE game_sessions ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;

-- ===== Step 2: Create indexes for new fields =====

CREATE INDEX idx_game_sessions_session_state ON game_sessions(session_state);
CREATE INDEX idx_game_sessions_is_archived ON game_sessions(is_archived);

-- ===== Step 3: Migrate existing data =====

-- Map old status values to new session_state
UPDATE game_sessions
SET session_state = CASE
    WHEN status = 'in_progress' THEN 'active'
    WHEN status = 'paused' THEN 'paused'
    WHEN status = 'completed' OR status = 'ended' THEN 'ended'
    ELSE 'preparing'
END
WHERE session_state = 'preparing';

-- Set started_at for sessions transitioning from other states
UPDATE game_sessions
SET started_at = CASE
    WHEN started_at IS NULL AND session_state IN ('active', 'paused', 'ended') THEN created_at
    ELSE started_at
END
WHERE session_state IN ('active', 'paused', 'ended');

-- ===== Step 4: Verification =====

SELECT COUNT(*) as session_count FROM game_sessions;
SELECT session_state, COUNT(*) as count FROM game_sessions GROUP BY session_state;

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
    '{"migration": "m41_session_state", "status": "completed"}'
);

-- ===== Rollback (if needed) =====
/*
-- Uncomment to rollback:

ALTER TABLE game_sessions DROP COLUMN session_state;
ALTER TABLE game_sessions DROP COLUMN player_limit;
ALTER TABLE game_sessions DROP COLUMN current_players_count;
ALTER TABLE game_sessions DROP COLUMN session_password;
ALTER TABLE game_sessions DROP COLUMN paused_at;
ALTER TABLE game_sessions DROP COLUMN is_archived;

DROP INDEX idx_game_sessions_session_state;
DROP INDEX idx_game_sessions_is_archived;
*/
