-- Explicit D&D race-to-sheet handoff; no legacy data or runtime cutover.
CREATE TABLE IF NOT EXISTS ce_character_origins (
    character_id INTEGER PRIMARY KEY REFERENCES characters(id),
    revision_id VARCHAR(128) NOT NULL REFERENCES ce_revisions(id),
    version BIGINT NOT NULL
);
CREATE TABLE IF NOT EXISTS ce_sheet_commands (
    principal_id INTEGER NOT NULL REFERENCES users(id),
    idempotency_key VARCHAR(128) NOT NULL,
    request_digest VARCHAR(71) NOT NULL,
    result BYTEA NOT NULL,
    PRIMARY KEY (principal_id, idempotency_key)
);
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgname = 'ce_sheet_commands_immutable') THEN
        CREATE TRIGGER ce_sheet_commands_immutable BEFORE UPDATE OR DELETE ON ce_sheet_commands
            FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();
    END IF;
END $$;
