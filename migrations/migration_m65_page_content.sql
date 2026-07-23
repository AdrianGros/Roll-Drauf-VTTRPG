-- M65 Migration: Page Content (editable copy)
-- Date: 2026-07-23
-- Description: Table for externalized, admin-editable page text (button
-- labels, headings, copy) - separates content from code ahead of the
-- end-of-year test phase. Note: this deployment runs with
-- AUTO_CREATE_SCHEMA=true, so db.create_all() creates this table from the
-- PageContent model directly; this file documents the resulting shape for
-- environments applying migrations manually.

CREATE TABLE IF NOT EXISTS page_content (
    id              SERIAL PRIMARY KEY,
    page_key        VARCHAR(50)  NOT NULL,
    content_key     VARCHAR(150) NOT NULL,
    text            TEXT         NOT NULL,
    description     VARCHAR(255),
    updated_at      TIMESTAMP    NOT NULL,
    updated_by_id   INTEGER REFERENCES users(id),
    CONSTRAINT uq_page_content_page_key_content_key UNIQUE (page_key, content_key)
);

CREATE INDEX IF NOT EXISTS ix_page_content_page_key ON page_content (page_key);

-- Rows are seeded idempotently at app startup by
-- vtt/content_defaults.py:ensure_default_page_content() (insert-if-missing
-- only - never overwrites content an editor has already changed).
