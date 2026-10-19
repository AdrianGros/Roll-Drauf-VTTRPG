-- Creation Engine = Eagle Homebrew (2026-10-19): documents written by Matt's editor.
-- Additive only. The Creation Engine G1 tables (ce_workspaces, ce_drafts, ...) stay untouched; their code is
-- archived under archive/creation-engine-g1/.
CREATE TABLE IF NOT EXISTS ce_eagle_documents (
    id SERIAL PRIMARY KEY,
    scope_kind VARCHAR(16) NOT NULL,
    scope_id INTEGER NOT NULL,
    pack VARCHAR(64) NOT NULL DEFAULT '',
    document_name VARCHAR(16) NOT NULL,
    document_id VARCHAR(64) NOT NULL,
    doc_type VARCHAR(32),
    name VARCHAR(200) NOT NULL,
    source JSON NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    created_by INTEGER NOT NULL REFERENCES users(id),
    updated_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    CONSTRAINT uq_ce_eagle_documents_identity UNIQUE (scope_kind, scope_id, pack, document_name, document_id)
);
CREATE INDEX IF NOT EXISTS ix_ce_eagle_documents_scope ON ce_eagle_documents (scope_kind, scope_id, document_name);
