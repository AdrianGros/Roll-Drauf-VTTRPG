-- M71 Migration: Vision, Walls, Lights, Fog of War
-- Date: 2026-08-28
-- Description: Slice S10 (playtable vision/lighting/Fog of War). Adds
-- SceneWall/SceneLight geometry keyed to campaign_maps (not scene_layers --
-- geometry belongs to the map asset, matching how TokenState already
-- anchors to map_id, not layer_id), FogOfWarState keyed to (user, map) for
-- persistence across scene switches, and TokenState.sight_range (NULL =
-- unlimited natural sight, still wall-blocked). NOTE: AUTO_CREATE_SCHEMA=
-- true only creates missing TABLES via db.create_all() and DOES create the
-- three new tables automatically on a fresh environment, but it does NOT
-- add columns to the already-existing token_states table -- that ALTER
-- TABLE below must be applied by hand against any environment that
-- already has it.

-- ===== Step 1: Add column to existing table =====

ALTER TABLE token_states ADD COLUMN sight_range INTEGER;

-- ===== Step 2: New tables (db.create_all() would also create these fresh,
-- included here so a hand-applied environment matches exactly) =====

CREATE TABLE IF NOT EXISTS scene_walls (
    id INTEGER PRIMARY KEY,
    campaign_map_id INTEGER NOT NULL REFERENCES campaign_maps(id),
    x0 INTEGER NOT NULL,
    y0 INTEGER NOT NULL,
    x1 INTEGER NOT NULL,
    y1 INTEGER NOT NULL,
    sight VARCHAR(20) NOT NULL DEFAULT 'normal',
    light VARCHAR(20) NOT NULL DEFAULT 'normal',
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_scene_walls_campaign_map_id ON scene_walls(campaign_map_id);

CREATE TABLE IF NOT EXISTS scene_lights (
    id INTEGER PRIMARY KEY,
    campaign_map_id INTEGER NOT NULL REFERENCES campaign_maps(id),
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    bright_radius INTEGER NOT NULL DEFAULT 0,
    dim_radius INTEGER NOT NULL DEFAULT 0,
    color VARCHAR(20) DEFAULT '#ffffff',
    provides_vision BOOLEAN NOT NULL DEFAULT TRUE,
    light_type VARCHAR(20) NOT NULL DEFAULT 'light',
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_scene_lights_campaign_map_id ON scene_lights(campaign_map_id);

CREATE TABLE IF NOT EXISTS fog_of_war_state (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    campaign_map_id INTEGER NOT NULL REFERENCES campaign_maps(id),
    explored_cells JSON,
    visible_cells JSON,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMP,
    CONSTRAINT uq_fog_user_map UNIQUE (user_id, campaign_map_id)
);
CREATE INDEX IF NOT EXISTS idx_fog_of_war_state_user_id ON fog_of_war_state(user_id);
CREATE INDEX IF NOT EXISTS idx_fog_of_war_state_campaign_map_id ON fog_of_war_state(campaign_map_id);

-- ===== Step 3: Verification =====

SELECT COUNT(*) AS walls FROM scene_walls;
SELECT COUNT(*) AS lights FROM scene_lights;
SELECT COUNT(*) AS fog_rows FROM fog_of_war_state;

-- ===== Rollback (if needed) =====
/*
DROP TABLE IF EXISTS fog_of_war_state;
DROP TABLE IF EXISTS scene_lights;
DROP TABLE IF EXISTS scene_walls;
ALTER TABLE token_states DROP COLUMN sight_range;
*/
