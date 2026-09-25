-- M73 Migration: Creation Engine content records (G1 work package WP3)
-- Date: 2026-09-24
-- Description: Personal workspaces, definitions, immutable revisions,
-- versioned drafts with an append-only decision log, and content-addressed
-- execution locks (spec docs/creation-engine/v1.1.4, §4, §6, §12-13, §15;
-- G1 plan dadm/artifacts/programs/milestone_program_creation_engine_g1.md
-- §7). Content is stored as canonical RFC 8785 bytes (BYTEA), not JSON/JSONB:
-- JSONB normalizes documents and the digests identify exact bytes.
--
-- All tables are new; nothing existing is altered. db.create_all() creates
-- the same tables once vtt.creation_engine.store.models is imported by the
-- app (WP4, behind feature flags). It never creates the triggers in Step 2,
-- so this file must still be applied (PostgreSQL 14+ for CREATE OR REPLACE
-- TRIGGER). Rollback: the tables are unused until the feature flags are on;
-- retain them (receipts and revisions must not be dropped once used).

-- ===== Step 1: Tables (identical to the SQLAlchemy models) =====

CREATE TABLE IF NOT EXISTS ce_workspaces (
    id VARCHAR(128) PRIMARY KEY,
    owner_user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS ce_definitions (
    id VARCHAR(128) PRIMARY KEY,
    workspace_id VARCHAR(128) NOT NULL REFERENCES ce_workspaces(id),
    name VARCHAR(200) NOT NULL,
    schema_type_id VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    tombstoned_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_ce_definitions_workspace_id ON ce_definitions (workspace_id);

CREATE TABLE IF NOT EXISTS ce_revisions (
    id VARCHAR(128) PRIMARY KEY,
    definition_id VARCHAR(128) NOT NULL REFERENCES ce_definitions(id),
    schema_type_id VARCHAR(128) NOT NULL,
    schema_version BIGINT NOT NULL,
    canonical BYTEA NOT NULL,
    digest VARCHAR(71) NOT NULL,
    provenance BYTEA NOT NULL,
    author_user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ce_revisions_definition_id ON ce_revisions (definition_id);
CREATE INDEX IF NOT EXISTS ix_ce_revisions_digest ON ce_revisions (digest);

CREATE TABLE IF NOT EXISTS ce_drafts (
    id VARCHAR(128) PRIMARY KEY,
    workspace_id VARCHAR(128) NOT NULL REFERENCES ce_workspaces(id),
    definition_id VARCHAR(128) REFERENCES ce_definitions(id),
    schema_type_id VARCHAR(128) NOT NULL,
    schema_version BIGINT NOT NULL,
    authoring_locale VARCHAR(8) NOT NULL,
    schema_bundle BYTEA NOT NULL,
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ce_drafts_workspace_id ON ce_drafts (workspace_id);

CREATE TABLE IF NOT EXISTS ce_draft_versions (
    draft_id VARCHAR(128) NOT NULL REFERENCES ce_drafts(id),
    version BIGINT NOT NULL,
    content BYTEA NOT NULL,
    author_user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (draft_id, version)
);

CREATE TABLE IF NOT EXISTS ce_draft_answers (
    id SERIAL PRIMARY KEY,
    draft_id VARCHAR(128) NOT NULL REFERENCES ce_drafts(id),
    draft_version BIGINT NOT NULL,
    question_id VARCHAR(128) NOT NULL,
    question_version BIGINT NOT NULL,
    answer BYTEA NOT NULL,
    prompt_locale VARCHAR(8) NOT NULL,
    author_user_id INTEGER NOT NULL REFERENCES users(id),
    mutations BYTEA NOT NULL,
    invalidated BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (draft_id, draft_version) REFERENCES ce_draft_versions(draft_id, version)
);
CREATE INDEX IF NOT EXISTS ix_ce_draft_answers_draft_id ON ce_draft_answers (draft_id);

CREATE TABLE IF NOT EXISTS ce_execution_locks (
    lock_id VARCHAR(128) PRIMARY KEY,
    digest VARCHAR(71) NOT NULL UNIQUE,
    canonical BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

-- ===== Step 2: Append-only enforcement (spec §4, §12, §15) =====

CREATE OR REPLACE FUNCTION ce_reject_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Creation Engine: % on % is not allowed (append-only record)', TG_OP, TG_TABLE_NAME
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER ce_revisions_append_only BEFORE UPDATE OR DELETE ON ce_revisions
    FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();
CREATE OR REPLACE TRIGGER ce_draft_versions_append_only BEFORE UPDATE OR DELETE ON ce_draft_versions
    FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();
CREATE OR REPLACE TRIGGER ce_draft_answers_append_only BEFORE UPDATE OR DELETE ON ce_draft_answers
    FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();
CREATE OR REPLACE TRIGGER ce_execution_locks_append_only BEFORE UPDATE OR DELETE ON ce_execution_locks
    FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();

-- ===== Step 3: Verification =====

SELECT table_name FROM information_schema.tables
WHERE table_name IN ('ce_workspaces', 'ce_definitions', 'ce_revisions', 'ce_drafts',
                     'ce_draft_versions', 'ce_draft_answers', 'ce_execution_locks')
ORDER BY table_name;
