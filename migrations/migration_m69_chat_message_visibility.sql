-- M69 Migration: Chat/Roll Visibility
-- Date: 2026-08-27
-- Description: Add visibility to chat_messages (Slice S08, playtable
-- roll composer). Rolls (and, in principle, any message) can be public
-- (everyone), gm_only (DM/CO_DM only), blind (DM sees the result, players
-- see a generic placeholder), or self (DM sees the result, players see a
-- generic placeholder -- distinct label from blind purely for the DM's own
-- bookkeeping, both hide identically from players). Existing rows default
-- to "public" -- every message ever sent before this slice was, in effect,
-- fully public. NOTE: AUTO_CREATE_SCHEMA=true only creates missing TABLES
-- via db.create_all(); it does NOT add columns to already-existing tables,
-- so this migration must be applied by hand against any environment that
-- already has a chat_messages table.

-- ===== Step 1: Add column =====

ALTER TABLE chat_messages ADD COLUMN visibility VARCHAR(20) NOT NULL DEFAULT 'public';

-- ===== Step 2: Create index to support role-scoped history queries =====

CREATE INDEX idx_chat_messages_visibility ON chat_messages(visibility);

-- ===== Step 3: Verification =====

SELECT visibility, COUNT(*) FROM chat_messages GROUP BY visibility;

-- ===== Rollback (if needed) =====
/*
DROP INDEX idx_chat_messages_visibility;
ALTER TABLE chat_messages DROP COLUMN visibility;
*/
