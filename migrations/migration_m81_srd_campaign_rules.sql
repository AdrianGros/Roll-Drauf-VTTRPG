-- P11: campaign-level limits for the SRD character creator (attribute methods).
CREATE TABLE IF NOT EXISTS campaign_srd_rules (
    campaign_id INTEGER PRIMARY KEY REFERENCES campaigns(id) ON DELETE CASCADE,
    ability_methods JSON NOT NULL,
    updated_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP NOT NULL
);
