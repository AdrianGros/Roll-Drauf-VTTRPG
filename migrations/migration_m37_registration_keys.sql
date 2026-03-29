-- M37 Migration: Registration Key System
-- Date: 2026-03-27
-- Description: Add registration keys table for bulk user provisioning and tier assignment

-- ===== Step 1: Create registration_keys table =====

CREATE TABLE registration_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_code VARCHAR(23) NOT NULL UNIQUE,
    key_name VARCHAR(255) NOT NULL,
    key_batch_id VARCHAR(50) NOT NULL,
    tier VARCHAR(20) NOT NULL DEFAULT 'player',
    max_uses INTEGER NOT NULL DEFAULT 1,
    uses_remaining INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    used_at DATETIME,
    expires_at DATETIME,
    used_by_id INTEGER,
    is_revoked BOOLEAN DEFAULT FALSE NOT NULL,
    FOREIGN KEY (used_by_id) REFERENCES users(id)
);

-- ===== Step 2: Create indexes for performance =====

CREATE INDEX idx_registration_keys_code ON registration_keys(key_code);
CREATE INDEX idx_registration_keys_batch_id ON registration_keys(key_batch_id);
CREATE INDEX idx_registration_keys_tier ON registration_keys(tier);
CREATE INDEX idx_registration_keys_used_at ON registration_keys(used_at);
CREATE INDEX idx_registration_keys_is_revoked ON registration_keys(is_revoked);
CREATE INDEX idx_registration_keys_created_at ON registration_keys(created_at);
CREATE INDEX idx_registration_keys_expires_at ON registration_keys(expires_at);
CREATE INDEX idx_registration_keys_used_by_id ON registration_keys(used_by_id);

-- ===== Step 3: Verification =====

-- Check table creation
SELECT COUNT(*) as registration_keys_count FROM registration_keys;

-- ===== Rollback (if needed) =====
/*
-- Uncomment to rollback:

DROP TABLE registration_keys;

DROP INDEX idx_registration_keys_code;
DROP INDEX idx_registration_keys_batch_id;
DROP INDEX idx_registration_keys_tier;
DROP INDEX idx_registration_keys_used_at;
DROP INDEX idx_registration_keys_is_revoked;
DROP INDEX idx_registration_keys_created_at;
DROP INDEX idx_registration_keys_expires_at;
DROP INDEX idx_registration_keys_used_by_id;
*/
