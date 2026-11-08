-- Charakter-Makroleiste (2026-11-08): personal hotbar slots per person and character.
-- Additive only. Production runs with AUTO_CREATE_SCHEMA=true, so db.create_all() creates the table on start;
-- this file is the equivalent for databases without auto-create.
-- Rollback: the previous image ignores the table.
CREATE TABLE IF NOT EXISTS table_macro_bars (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    slots JSON NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT uq_table_macro_bar_user_character UNIQUE (user_id, character_id)
);
CREATE INDEX IF NOT EXISTS ix_table_macro_bars_user_id ON table_macro_bars (user_id);
CREATE INDEX IF NOT EXISTS ix_table_macro_bars_character_id ON table_macro_bars (character_id);
