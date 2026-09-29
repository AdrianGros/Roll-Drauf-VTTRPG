-- Apply after M73-M79. Separate private test scopes; no campaign cutover.
CREATE TABLE IF NOT EXISTS ce_homebrew_sandboxes (
    id VARCHAR(128) PRIMARY KEY,
    workspace_id VARCHAR(128) NOT NULL REFERENCES ce_workspaces(id),
    version BIGINT NOT NULL CONSTRAINT ce_homebrew_version_positive CHECK (version >= 1),
    execution_lock BYTEA NOT NULL,
    state BYTEA NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ce_homebrew_sandboxes_workspace_id ON ce_homebrew_sandboxes(workspace_id);
CREATE TABLE IF NOT EXISTS ce_homebrew_events (
    workspace_id VARCHAR(128) NOT NULL REFERENCES ce_workspaces(id),
    principal_id INTEGER NOT NULL REFERENCES users(id),
    idempotency_key VARCHAR(128) NOT NULL,
    sandbox_id VARCHAR(128) NOT NULL REFERENCES ce_homebrew_sandboxes(id),
    version BIGINT NOT NULL,
    request_digest VARCHAR(71) NOT NULL,
    command BYTEA NOT NULL,
    result BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (workspace_id, principal_id, idempotency_key),
    CONSTRAINT ce_homebrew_event_sequence UNIQUE (sandbox_id, version)
);
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgname = 'ce_homebrew_events_immutable') THEN
        CREATE TRIGGER ce_homebrew_events_immutable BEFORE UPDATE OR DELETE ON ce_homebrew_events
            FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();
    END IF;
END $$;

-- Scope ownership and exact revision/runtime pins cannot be silently replaced.
CREATE OR REPLACE FUNCTION ce_homebrew_lock_immutable() RETURNS trigger AS $$
BEGIN
    IF NEW.id IS DISTINCT FROM OLD.id OR NEW.workspace_id IS DISTINCT FROM OLD.workspace_id
       OR NEW.execution_lock IS DISTINCT FROM OLD.execution_lock THEN
        RAISE EXCEPTION 'homebrew execution lock and ownership are immutable';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgname = 'ce_homebrew_lock_immutable') THEN
        CREATE TRIGGER ce_homebrew_lock_immutable BEFORE UPDATE ON ce_homebrew_sandboxes
            FOR EACH ROW EXECUTE FUNCTION ce_homebrew_lock_immutable();
    END IF;
END $$;
