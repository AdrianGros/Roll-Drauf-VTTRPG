-- M70 Migration: Loot Transfer
-- Date: 2026-08-27
-- Description: Slice S09 (playtable loot transfer). Adds a loot-container
-- concept distinct from character inventory (Lessons Learned in the
-- research doc explicitly warns against overloading InventoryItem or
-- metadata_json for this): TokenState.is_loot_source flags a token as a
-- lootable corpse/chest, token_loot holds the items sitting on it,
-- loot_transfers is the idempotency+audit record (one row per transfer
-- attempt, keyed so a network retry returns the cached result instead of
-- re-executing), and Character.is_party_stash marks a shared-recipient
-- character. NOTE: AUTO_CREATE_SCHEMA=true only creates missing TABLES
-- via db.create_all() and DOES create the two new tables automatically on
-- a fresh environment, but it does NOT add columns to the already-existing
-- token_states/characters tables -- the two ALTER TABLEs below must be
-- applied by hand against any environment that already has those tables.

-- ===== Step 1: Add columns to existing tables =====

ALTER TABLE token_states ADD COLUMN is_loot_source BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE characters ADD COLUMN is_party_stash BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX idx_token_states_is_loot_source ON token_states(is_loot_source);
CREATE INDEX idx_characters_is_party_stash ON characters(is_party_stash);

-- ===== Step 2: New tables (db.create_all() would also create these fresh,
-- included here so a hand-applied environment matches exactly) =====

CREATE TABLE IF NOT EXISTS token_loot (
    id INTEGER PRIMARY KEY,
    token_id INTEGER NOT NULL REFERENCES token_states(id),
    name VARCHAR(100) NOT NULL,
    item_type VARCHAR(50),
    quantity INTEGER NOT NULL DEFAULT 1,
    weight_per_unit FLOAT,
    cost VARCHAR(50),
    is_consumable BOOLEAN NOT NULL DEFAULT FALSE,
    is_cursed BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    effects JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_token_loot_token_id ON token_loot(token_id);

CREATE TABLE IF NOT EXISTS loot_transfers (
    id INTEGER PRIMARY KEY,
    idempotency_key VARCHAR(120) NOT NULL UNIQUE,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    game_session_id INTEGER NOT NULL REFERENCES game_sessions(id),
    actor_user_id INTEGER NOT NULL REFERENCES users(id),
    source_token_id INTEGER NOT NULL REFERENCES token_states(id),
    recipient_character_id INTEGER NOT NULL REFERENCES characters(id),
    items_transferred JSON NOT NULL,
    created_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_loot_transfers_session ON loot_transfers(game_session_id);

-- ===== Step 3: Verification =====

SELECT COUNT(*) AS loot_source_tokens FROM token_states WHERE is_loot_source = TRUE;
SELECT COUNT(*) AS party_stash_characters FROM characters WHERE is_party_stash = TRUE;

-- ===== Rollback (if needed) =====
/*
DROP TABLE IF EXISTS loot_transfers;
DROP TABLE IF EXISTS token_loot;
DROP INDEX IF EXISTS idx_characters_is_party_stash;
DROP INDEX IF EXISTS idx_token_states_is_loot_source;
ALTER TABLE characters DROP COLUMN is_party_stash;
ALTER TABLE token_states DROP COLUMN is_loot_source;
*/
