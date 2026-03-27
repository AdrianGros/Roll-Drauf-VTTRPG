-- M18 Migration: Add user account lifecycle fields
-- Date: 2026-03-27
-- Description: Add deletion tracking, grace period, anonymization fields

-- ===== Step 1: Add lifecycle columns to users table =====

ALTER TABLE users ADD COLUMN account_state VARCHAR(20) DEFAULT 'active';
-- Values: active, deactivated, marked_for_deletion, permanently_deleted, suspended

ALTER TABLE users ADD COLUMN deleted_at DATETIME;
-- When deletion was requested

ALTER TABLE users ADD COLUMN deletion_reason TEXT;
-- Why user requested deletion

ALTER TABLE users ADD COLUMN deletion_requested_by INTEGER;
-- Who requested deletion (admin or self)

ALTER TABLE users ADD COLUMN last_active_at DATETIME;
-- For recovery email context

ALTER TABLE users ADD COLUMN hard_deleted_at DATETIME;
-- When hard-delete was executed

-- Add indexes for performance
CREATE INDEX idx_users_account_state ON users(account_state);
CREATE INDEX idx_users_deleted_at ON users(deleted_at);

-- Add foreign key for deletion_requested_by
ALTER TABLE users ADD CONSTRAINT fk_users_deletion_requested_by
  FOREIGN KEY (deletion_requested_by) REFERENCES users(id);

-- ===== Step 2: Verify migration =====

SELECT COUNT(*) as user_count FROM users;
SELECT COUNT(DISTINCT account_state) as unique_states FROM users;

-- ===== Step 3: Initialize audit log for migration =====

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
    '{"migration": "m18_add_user_lifecycle", "status": "completed"}'
);

-- ===== Rollback (if needed) =====
/*
-- Uncomment to rollback:

ALTER TABLE users DROP COLUMN account_state;
ALTER TABLE users DROP COLUMN deleted_at;
ALTER TABLE users DROP COLUMN deletion_reason;
ALTER TABLE users DROP COLUMN deletion_requested_by;
ALTER TABLE users DROP COLUMN last_active_at;
ALTER TABLE users DROP COLUMN hard_deleted_at;

DROP INDEX idx_users_account_state;
DROP INDEX idx_users_deleted_at;

ALTER TABLE users DROP CONSTRAINT fk_users_deletion_requested_by;
*/
