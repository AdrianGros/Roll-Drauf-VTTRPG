-- M68 Migration: Campaign and Character Discoverability
-- Date: 2026-08-26
-- Description: Add is_discoverable flag to campaigns and characters (Finding
-- F2). Campaigns/characters are private by default; "discoverable" only
-- controls whether a campaign surfaces in the /api/campaigns browse listing
-- for users who do not already own or belong to it - joining still requires
-- an invite regardless of this flag. NOTE: AUTO_CREATE_SCHEMA=true only
-- creates missing TABLES via db.create_all(); it does NOT add columns to
-- already-existing tables, so this migration must be applied by hand against
-- any environment that already has campaigns/characters tables.

-- ===== Step 1: Add columns =====

ALTER TABLE campaigns ADD COLUMN is_discoverable BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE characters ADD COLUMN is_discoverable BOOLEAN NOT NULL DEFAULT FALSE;

-- ===== Step 2: Create indexes to support browse-listing filtering =====

CREATE INDEX idx_campaigns_is_discoverable ON campaigns(is_discoverable);
CREATE INDEX idx_characters_is_discoverable ON characters(is_discoverable);

-- ===== Step 3: Verification =====

SELECT COUNT(*) AS campaigns_total, SUM(CASE WHEN is_discoverable THEN 1 ELSE 0 END) AS campaigns_discoverable FROM campaigns;
SELECT COUNT(*) AS characters_total, SUM(CASE WHEN is_discoverable THEN 1 ELSE 0 END) AS characters_discoverable FROM characters;

-- ===== Rollback (if needed) =====
/*
DROP INDEX idx_campaigns_is_discoverable;
DROP INDEX idx_characters_is_discoverable;

ALTER TABLE campaigns DROP COLUMN is_discoverable;
ALTER TABLE characters DROP COLUMN is_discoverable;
*/
