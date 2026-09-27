-- G1 WP7: additive records; no legacy data is rewritten.
CREATE TABLE IF NOT EXISTS ce_migration_ledger (
    source_type VARCHAR(64) NOT NULL, source_id INTEGER NOT NULL, migration_version BIGINT NOT NULL,
    opaque_id VARCHAR(128) NOT NULL UNIQUE, scope_id VARCHAR(128) NOT NULL REFERENCES ce_runtime_scopes(id),
    PRIMARY KEY (source_type, source_id, migration_version), CHECK (source_id > 0 AND migration_version >= 0)
);
CREATE INDEX IF NOT EXISTS ix_ce_migration_ledger_scope_id ON ce_migration_ledger(scope_id);
CREATE TABLE IF NOT EXISTS ce_migration_states (
    scope_id VARCHAR(128) PRIMARY KEY REFERENCES ce_runtime_scopes(id), report_id VARCHAR(128),
    frozen_digest VARCHAR(71), cutover_version BIGINT
);
CREATE TABLE IF NOT EXISTS ce_parity_reports (
    id VARCHAR(128) PRIMARY KEY, scope_id VARCHAR(128) NOT NULL REFERENCES ce_runtime_scopes(id),
    source_digest VARCHAR(71) NOT NULL, digest VARCHAR(71) NOT NULL, canonical BYTEA NOT NULL, snapshots BYTEA NOT NULL
);
CREATE TABLE IF NOT EXISTS ce_parity_approvals (
    report_id VARCHAR(128) NOT NULL REFERENCES ce_parity_reports(id), discrepancy_id VARCHAR(128) NOT NULL,
    principal_id INTEGER NOT NULL REFERENCES users(id), capacity VARCHAR(16) NOT NULL,
    resolution VARCHAR(32) NOT NULL, reason TEXT NOT NULL,
    PRIMARY KEY (report_id, discrepancy_id, principal_id, capacity),
    CHECK (capacity IN ('controller', 'operator')),
    CHECK (resolution IN ('adopt_engine_value', 'keep_legacy_override'))
);
CREATE TABLE IF NOT EXISTS ce_legacy_inputs (
    instance_id VARCHAR(128) PRIMARY KEY REFERENCES ce_instances(id), bases BYTEA NOT NULL,
    overrides BYTEA NOT NULL, equipped BOOLEAN
);
CREATE TABLE IF NOT EXISTS ce_representations (
    source_type VARCHAR(64) NOT NULL, source_id INTEGER NOT NULL,
    scope_id VARCHAR(128) NOT NULL REFERENCES ce_runtime_scopes(id),
    instance_id VARCHAR(128) NOT NULL REFERENCES ce_instances(id), PRIMARY KEY (source_type, source_id)
);
CREATE INDEX IF NOT EXISTS ix_ce_representations_scope_id ON ce_representations(scope_id);
-- One canonical migration scope per campaign/personal workspace. Existing isolated
-- kernel fixtures are intentionally outside this host registration index.
CREATE TABLE IF NOT EXISTS ce_legacy_scope_links (
    source_type VARCHAR(16) NOT NULL, source_id INTEGER NOT NULL,
    scope_id VARCHAR(128) NOT NULL UNIQUE REFERENCES ce_runtime_scopes(id),
    PRIMARY KEY (source_type, source_id), CHECK (source_type IN ('campaign', 'sandbox'))
);
CREATE TABLE IF NOT EXISTS ce_grants (
    id VARCHAR(128) PRIMARY KEY, source_instance_id VARCHAR(128) NOT NULL REFERENCES ce_instances(id),
    choice_id VARCHAR(128) NOT NULL, canonical BYTEA NOT NULL, UNIQUE (source_instance_id, choice_id)
);
CREATE TABLE IF NOT EXISTS ce_workspace_commands (
    workspace_id VARCHAR(128) NOT NULL REFERENCES ce_workspaces(id), principal_id INTEGER NOT NULL REFERENCES users(id),
    idempotency_key VARCHAR(128) NOT NULL, scope_id VARCHAR(128) NOT NULL REFERENCES ce_runtime_scopes(id),
    request_digest VARCHAR(71) NOT NULL, receipt BYTEA NOT NULL,
    PRIMARY KEY (workspace_id, principal_id, idempotency_key)
);
DO $$ DECLARE relation TEXT; BEGIN
    FOREACH relation IN ARRAY ARRAY['ce_migration_ledger','ce_parity_reports','ce_parity_approvals','ce_representations','ce_legacy_scope_links','ce_grants','ce_workspace_commands'] LOOP
        IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgname = relation || '_immutable') THEN
            EXECUTE format('CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation()', relation || '_immutable', relation);
        END IF;
    END LOOP;
END $$;
