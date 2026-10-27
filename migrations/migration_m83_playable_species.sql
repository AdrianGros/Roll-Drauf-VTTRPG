-- Playable Eagle Species (2026-10-27): immutable published revisions of an Eagle Species as a 2024 origin.
-- Additive only. Characters pin the profile inside their own character_data (srd.speciesPin), so dropping the
-- CE_PLAYABLE_SPECIES flag (or this table's rows) never changes an existing character.
-- Rollback: set CE_PLAYABLE_SPECIES=false; do not drop the table while characters reference its revision ids.
CREATE TABLE IF NOT EXISTS ce_species_revisions (
    id SERIAL PRIMARY KEY,
    scope_kind VARCHAR(16) NOT NULL,
    scope_id INTEGER NOT NULL,
    lineage VARCHAR(240) NOT NULL,
    revision_number INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    edition VARCHAR(8) NOT NULL,
    source_uuid VARCHAR(200) NOT NULL,
    source_revision INTEGER NOT NULL,
    source_digest VARCHAR(80) NOT NULL,
    source JSON NOT NULL,
    supplement JSON NOT NULL,
    profile JSON NOT NULL,
    profile_digest VARCHAR(80) NOT NULL,
    report JSON NOT NULL,
    published_by INTEGER NOT NULL REFERENCES users(id),
    published_at TIMESTAMP NOT NULL,
    CONSTRAINT uq_ce_species_revisions_number UNIQUE (scope_kind, scope_id, lineage, revision_number)
);
CREATE INDEX IF NOT EXISTS ix_ce_species_revisions_scope ON ce_species_revisions (scope_kind, scope_id);
