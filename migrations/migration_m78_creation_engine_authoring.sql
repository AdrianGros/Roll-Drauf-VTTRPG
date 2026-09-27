-- WP8: draft content, compiler decisions and receipts commit together.
-- Workspace commands share one key namespace, including non-runtime creation.
ALTER TABLE ce_workspace_commands ALTER COLUMN scope_id DROP NOT NULL;
CREATE TABLE IF NOT EXISTS ce_authoring_snapshots (
    draft_id VARCHAR(128) NOT NULL, version BIGINT NOT NULL, state BYTEA NOT NULL,
    PRIMARY KEY (draft_id, version),
    FOREIGN KEY (draft_id, version) REFERENCES ce_draft_versions(draft_id, version)
);
CREATE TABLE IF NOT EXISTS ce_draft_commands (
    draft_id VARCHAR(128) NOT NULL REFERENCES ce_drafts(id), principal_id INTEGER NOT NULL REFERENCES users(id),
    idempotency_key VARCHAR(128) NOT NULL, request_digest VARCHAR(71) NOT NULL,
    receipt BYTEA NOT NULL, result BYTEA NOT NULL,
    PRIMARY KEY (draft_id, principal_id, idempotency_key)
);
CREATE TABLE IF NOT EXISTS ce_workspace_results (
    workspace_id VARCHAR(128) NOT NULL, principal_id INTEGER NOT NULL, idempotency_key VARCHAR(128) NOT NULL,
    result BYTEA NOT NULL, PRIMARY KEY (workspace_id, principal_id, idempotency_key),
    FOREIGN KEY (workspace_id, principal_id, idempotency_key)
        REFERENCES ce_workspace_commands(workspace_id, principal_id, idempotency_key)
);
DO $$ DECLARE relation TEXT; BEGIN
    FOREACH relation IN ARRAY ARRAY['ce_authoring_snapshots','ce_draft_commands','ce_workspace_results'] LOOP
        IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgname = relation || '_immutable') THEN
            EXECUTE format('CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation()', relation || '_immutable', relation);
        END IF;
    END LOOP;
END $$;
