-- M46 Migration: Spellbook Theme Settings
-- Date: 2026-03-27
-- Description: Add app_theme_settings table for spellbook theme customization

-- ===== Step 1: Create app_theme_settings table =====

CREATE TABLE app_theme_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    theme_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    primary_color VARCHAR(7) NOT NULL DEFAULT '#4a235a',
    accent_color VARCHAR(7) NOT NULL DEFAULT '#d4af37',
    text_color VARCHAR(7) NOT NULL DEFAULT '#2a2a2a',
    background_color VARCHAR(7) NOT NULL DEFAULT '#f5e6d3',
    font_heading VARCHAR(100) NOT NULL DEFAULT "'Georgia', serif",
    font_body VARCHAR(100) NOT NULL DEFAULT "'Segoe UI', sans-serif",
    book_animation_speed REAL NOT NULL DEFAULT 2.5,
    key_code_prefix VARCHAR(10) NOT NULL DEFAULT 'SPELL',
    is_active BOOLEAN DEFAULT FALSE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ===== Step 2: Create indexes for performance =====

CREATE INDEX idx_app_theme_settings_theme_name ON app_theme_settings(theme_name);
CREATE INDEX idx_app_theme_settings_is_active ON app_theme_settings(is_active);
CREATE INDEX idx_app_theme_settings_created_at ON app_theme_settings(created_at);

-- ===== Step 3: Insert default theme =====

INSERT INTO app_theme_settings (
    theme_name,
    description,
    primary_color,
    accent_color,
    text_color,
    background_color,
    font_heading,
    font_body,
    book_animation_speed,
    key_code_prefix,
    is_active
) VALUES (
    'Default Spellbook',
    'Default spellbook theme with deep purple and gold',
    '#4a235a',
    '#d4af37',
    '#2a2a2a',
    '#f5e6d3',
    "'" || 'Georgia' || "'" || ', serif',
    "'" || 'Segoe UI' || "'" || ', sans-serif',
    2.5,
    'SPELL',
    TRUE
);

-- ===== Step 4: Verification =====

SELECT COUNT(*) as theme_settings_count FROM app_theme_settings;
SELECT * FROM app_theme_settings WHERE is_active = TRUE;

-- ===== Rollback (if needed) =====
/*
-- Uncomment to rollback:

DROP TABLE app_theme_settings;

DROP INDEX idx_app_theme_settings_theme_name;
DROP INDEX idx_app_theme_settings_is_active;
DROP INDEX idx_app_theme_settings_created_at;
*/
