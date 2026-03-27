-- M17 Migration: Add platform roles, profile tiers, quotas, and audit logging
-- Date: 2026-03-27
-- Description: Extend user model with multi-tier role system and add audit logging

-- ===== Step 1: Add new columns to users table =====

ALTER TABLE users ADD COLUMN platform_role VARCHAR(20) DEFAULT 'supporter';
ALTER TABLE users ADD COLUMN profile_tier VARCHAR(20) DEFAULT 'player';
ALTER TABLE users ADD COLUMN storage_quota_gb INTEGER;
ALTER TABLE users ADD COLUMN storage_used_gb FLOAT DEFAULT 0.0;
ALTER TABLE users ADD COLUMN active_campaigns_quota INTEGER;
ALTER TABLE users ADD COLUMN is_suspended BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN suspended_at DATETIME;
ALTER TABLE users ADD COLUMN suspended_reason TEXT;
ALTER TABLE users ADD COLUMN suspended_by INTEGER;

-- Add foreign key for suspension tracking
ALTER TABLE users ADD CONSTRAINT fk_users_suspended_by
  FOREIGN KEY (suspended_by) REFERENCES users(id);

-- Add indexes for performance
CREATE INDEX idx_users_platform_role ON users(platform_role);
CREATE INDEX idx_users_profile_tier ON users(profile_tier);
CREATE INDEX idx_users_is_suspended ON users(is_suspended);

-- ===== Step 2: Create audit_logs table =====

CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSON,
    ip_address VARCHAR(45),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    performed_by_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (performed_by_id) REFERENCES users(id)
);

-- Create indexes for audit queries
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);

-- ===== Step 3: Data migration - Map existing roles =====

-- Map existing role_id to new platform_role (requires role table with id)
-- Example: If Admin role has id=3, dm role has id=2, player role has id=1

-- Set Admin users to admin platform role
UPDATE users
SET platform_role = 'admin'
WHERE role_id = (SELECT id FROM roles WHERE name = 'Admin' LIMIT 1);

-- Set DM users to profile_tier='dm'
UPDATE users
SET platform_role = NULL,
    profile_tier = 'dm',
    storage_quota_gb = 1,
    active_campaigns_quota = 3
WHERE role_id = (SELECT id FROM roles WHERE name = 'DM' LIMIT 1);

-- Set Player users
UPDATE users
SET profile_tier = 'player'
WHERE role_id = (SELECT id FROM roles WHERE name = 'Player' LIMIT 1);

-- Default remaining users to 'supporter' if they have admin-like role
UPDATE users
SET platform_role = 'supporter'
WHERE platform_role IS NULL AND profile_tier = 'player';

-- ===== Step 4: Initialize first audit log entry =====

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
    '{"migration": "m17_add_platform_roles_and_audit", "status": "completed"}'
);

-- ===== Step 5: Verification =====

-- Check new columns
SELECT COUNT(*) as user_count, platform_role, profile_tier
FROM users
GROUP BY platform_role, profile_tier;

-- Check audit log creation
SELECT COUNT(*) as audit_log_count FROM audit_logs;

-- ===== Rollback (if needed) =====
/*
-- Uncomment to rollback:

ALTER TABLE users DROP COLUMN platform_role;
ALTER TABLE users DROP COLUMN profile_tier;
ALTER TABLE users DROP COLUMN storage_quota_gb;
ALTER TABLE users DROP COLUMN storage_used_gb;
ALTER TABLE users DROP COLUMN active_campaigns_quota;
ALTER TABLE users DROP COLUMN is_suspended;
ALTER TABLE users DROP COLUMN suspended_at;
ALTER TABLE users DROP COLUMN suspended_reason;
ALTER TABLE users DROP COLUMN suspended_by;

DROP TABLE audit_logs;

DROP INDEX idx_users_platform_role;
DROP INDEX idx_users_profile_tier;
DROP INDEX idx_users_is_suspended;
DROP INDEX idx_audit_logs_timestamp;
DROP INDEX idx_audit_logs_action;
DROP INDEX idx_audit_logs_resource;
DROP INDEX idx_audit_logs_user_id;
*/
