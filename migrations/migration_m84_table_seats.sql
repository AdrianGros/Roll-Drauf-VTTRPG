-- Table seats (2026-11-08): a DM or CO-DM can sit at one session's table as a player.
-- Additive only. Production runs with AUTO_CREATE_SCHEMA=true, so db.create_all() creates the table on start;
-- this file is the equivalent for databases without auto-create.
-- Rollback: the previous image ignores the table. Dropping it puts every operator back in their DM seat.
CREATE TABLE IF NOT EXISTS table_seats (
    id SERIAL PRIMARY KEY,
    game_session_id INTEGER NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    seat VARCHAR(16) NOT NULL DEFAULT 'player',
    created_at TIMESTAMP WITHOUT TIME ZONE,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT uq_table_seat_session_user UNIQUE (game_session_id, user_id)
);
CREATE INDEX IF NOT EXISTS ix_table_seats_game_session_id ON table_seats (game_session_id);
CREATE INDEX IF NOT EXISTS ix_table_seats_user_id ON table_seats (user_id);
