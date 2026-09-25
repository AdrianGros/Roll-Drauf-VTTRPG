-- M74: Creation Engine command/checkpoint kernel (WP4, spec v1.1.4 §§8–9).
-- Apply after m73. Additive; no live application imports these tables yet.
-- PostgreSQL 14+;


CREATE TABLE IF NOT EXISTS ce_runtime_scopes (
    id VARCHAR(128) NOT NULL,
    kind VARCHAR(16) NOT NULL,
    owner_user_id INTEGER NOT NULL,
    campaign_id INTEGER,
    fixture BOOLEAN NOT NULL,
    migration_state VARCHAR(32) NOT NULL,
    lock_id VARCHAR(128) NOT NULL,
    state_version BIGINT NOT NULL,
    authority_epoch BIGINT NOT NULL,
    policy_version BIGINT NOT NULL,
    event_sequence BIGINT NOT NULL,
    active_action_id VARCHAR(128),
    fence_epoch BIGINT NOT NULL,
    lease_owner VARCHAR(128),
    lease_expires_at TIMESTAMP WITH TIME ZONE,
    time_watermark TIMESTAMP WITH TIME ZONE NOT NULL,
    deleted BOOLEAN NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ce_scope_kind CHECK (kind IN ('sandbox', 'campaign')),
    CONSTRAINT ce_scope_authority_state CHECK (migration_state IN ('LEGACY','SHADOW','FROZEN_FOR_CUTOVER','ENGINE','ROLLBACK_REVIEW')),
    CONSTRAINT ce_scope_versions CHECK (state_version BETWEEN 0 AND 9007199254740991 AND authority_epoch BETWEEN 0 AND 9007199254740991),
    FOREIGN KEY(owner_user_id) REFERENCES users (id),
    FOREIGN KEY(campaign_id) REFERENCES campaigns (id),
    FOREIGN KEY(lock_id) REFERENCES ce_execution_locks (lock_id)
)

;


CREATE TABLE IF NOT EXISTS ce_instances (
    id VARCHAR(128) NOT NULL,
    scope_id VARCHAR(128) NOT NULL,
    revision_id VARCHAR(128) NOT NULL,
    controller_user_id INTEGER NOT NULL,
    holder_id VARCHAR(128),
    PRIMARY KEY (id),
    FOREIGN KEY(scope_id) REFERENCES ce_runtime_scopes (id),
    FOREIGN KEY(revision_id) REFERENCES ce_revisions (id),
    FOREIGN KEY(controller_user_id) REFERENCES users (id),
    FOREIGN KEY(holder_id) REFERENCES ce_instances (id)
)

;

CREATE INDEX IF NOT EXISTS ix_ce_instances_scope_id ON ce_instances (scope_id);


CREATE TABLE IF NOT EXISTS ce_resource_ledger (
    instance_id VARCHAR(128) NOT NULL,
    resource_id VARCHAR(128) NOT NULL,
    unit VARCHAR(128) NOT NULL,
    current BYTEA NOT NULL,
    maximum BYTEA NOT NULL,
    adjust_bound_policy VARCHAR(32) NOT NULL,
    PRIMARY KEY (instance_id, resource_id),
    CONSTRAINT ce_resource_adjust_policy CHECK (adjust_bound_policy IN ('reject', 'clamp_report_delta')),
    FOREIGN KEY(instance_id) REFERENCES ce_instances (id)
)

;


CREATE TABLE IF NOT EXISTS ce_actions (
    id VARCHAR(128) NOT NULL,
    scope_id VARCHAR(128) NOT NULL,
    principal_id INTEGER NOT NULL,
    request BYTEA NOT NULL,
    plan BYTEA NOT NULL,
    state VARCHAR(32) NOT NULL,
    deadline TIMESTAMP WITH TIME ZONE NOT NULL,
    root_id VARCHAR(128) NOT NULL,
    parent_id VARCHAR(128),
    depth INTEGER NOT NULL,
    next_window INTEGER NOT NULL,
    version BIGINT NOT NULL,
    last_checkpoint_id VARCHAR(128),
    error_code VARCHAR(128),
    budget BYTEA NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ce_action_depth CHECK (depth BETWEEN 0 AND 16),
    CONSTRAINT ce_action_state CHECK (state IN ('PROPOSED','WAITING_PRECOMMIT','ACTIVE','WAITING_DECISION','SUSPENDED','COMPLETED','CANCELLED','FAILED_PRECOMMIT')),
    FOREIGN KEY(scope_id) REFERENCES ce_runtime_scopes (id),
    FOREIGN KEY(principal_id) REFERENCES users (id),
    FOREIGN KEY(parent_id) REFERENCES ce_actions (id)
)

;

CREATE INDEX IF NOT EXISTS ix_ce_actions_scope_id ON ce_actions (scope_id);


CREATE TABLE IF NOT EXISTS ce_checkpoints (
    id VARCHAR(128) NOT NULL,
    scope_id VARCHAR(128) NOT NULL,
    action_id VARCHAR(128) NOT NULL,
    window_index INTEGER NOT NULL,
    state_version BIGINT NOT NULL,
    outcome BYTEA NOT NULL,
    outcome_digest VARCHAR(71) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (action_id, window_index),
    FOREIGN KEY(scope_id) REFERENCES ce_runtime_scopes (id),
    FOREIGN KEY(action_id) REFERENCES ce_actions (id)
)

;


CREATE TABLE IF NOT EXISTS ce_receipts (
    scope_id VARCHAR(128) NOT NULL,
    principal_id INTEGER NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    operation_id VARCHAR(128) NOT NULL,
    request_digest VARCHAR(71) NOT NULL,
    status VARCHAR(16) NOT NULL,
    canonical BYTEA NOT NULL,
    PRIMARY KEY (scope_id, principal_id, idempotency_key),
    CONSTRAINT ce_receipt_status CHECK (status IN ('accepted','committed','rejected','suspended')),
    FOREIGN KEY(scope_id) REFERENCES ce_runtime_scopes (id),
    FOREIGN KEY(principal_id) REFERENCES users (id),
    UNIQUE (operation_id)
)

;


CREATE TABLE IF NOT EXISTS ce_resource_entries (
    id VARCHAR(128) NOT NULL,
    checkpoint_id VARCHAR(128) NOT NULL,
    instance_id VARCHAR(128) NOT NULL,
    resource_id VARCHAR(128) NOT NULL,
    canonical BYTEA NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(checkpoint_id) REFERENCES ce_checkpoints (id),
    FOREIGN KEY(instance_id) REFERENCES ce_instances (id)
)

;


CREATE TABLE IF NOT EXISTS ce_random_records (
    checkpoint_id VARCHAR(128) NOT NULL,
    roll_id VARCHAR(128) NOT NULL,
    canonical BYTEA NOT NULL,
    PRIMARY KEY (checkpoint_id, roll_id),
    FOREIGN KEY(checkpoint_id) REFERENCES ce_checkpoints (id)
)

;


CREATE TABLE IF NOT EXISTS ce_effect_applications (
    id VARCHAR(128) NOT NULL,
    scope_id VARCHAR(128) NOT NULL,
    checkpoint_id VARCHAR(128) NOT NULL,
    target_id VARCHAR(128) NOT NULL,
    canonical BYTEA NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(scope_id) REFERENCES ce_runtime_scopes (id),
    FOREIGN KEY(checkpoint_id) REFERENCES ce_checkpoints (id),
    FOREIGN KEY(target_id) REFERENCES ce_instances (id)
)

;

CREATE INDEX IF NOT EXISTS ix_ce_effect_applications_target_id ON ce_effect_applications (target_id);


CREATE TABLE IF NOT EXISTS ce_domain_events (
    id VARCHAR(128) NOT NULL,
    scope_id VARCHAR(128) NOT NULL,
    sequence BIGINT NOT NULL,
    action_id VARCHAR(128) NOT NULL,
    checkpoint_id VARCHAR(128),
    canonical BYTEA NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (scope_id, sequence),
    FOREIGN KEY(scope_id) REFERENCES ce_runtime_scopes (id),
    FOREIGN KEY(action_id) REFERENCES ce_actions (id),
    FOREIGN KEY(checkpoint_id) REFERENCES ce_checkpoints (id)
)

;


CREATE TABLE IF NOT EXISTS ce_outbox (
    event_id VARCHAR(128) NOT NULL,
    attempts INTEGER NOT NULL,
    delivered_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (event_id),
    FOREIGN KEY(event_id) REFERENCES ce_domain_events (id)
)

;


CREATE TABLE IF NOT EXISTS ce_event_consumptions (
    consumer VARCHAR(128) NOT NULL,
    event_id VARCHAR(128) NOT NULL,
    PRIMARY KEY (consumer, event_id),
    FOREIGN KEY(event_id) REFERENCES ce_domain_events (id)
)

;

CREATE OR REPLACE TRIGGER ce_checkpoints_append_only BEFORE UPDATE OR DELETE ON ce_checkpoints
FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();

CREATE OR REPLACE TRIGGER ce_resource_entries_append_only BEFORE UPDATE OR DELETE ON ce_resource_entries
FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();

CREATE OR REPLACE TRIGGER ce_random_records_append_only BEFORE UPDATE OR DELETE ON ce_random_records
FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();

CREATE OR REPLACE TRIGGER ce_effect_applications_append_only BEFORE UPDATE OR DELETE ON ce_effect_applications
FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();

CREATE OR REPLACE TRIGGER ce_domain_events_append_only BEFORE UPDATE OR DELETE ON ce_domain_events
FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();

CREATE OR REPLACE TRIGGER ce_event_consumptions_append_only BEFORE UPDATE OR DELETE ON ce_event_consumptions
FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();

CREATE OR REPLACE FUNCTION ce_guard_receipt() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Creation Engine receipt retention forbids deletion' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF OLD.status <> 'accepted' OR NEW.scope_id <> OLD.scope_id OR NEW.principal_id <> OLD.principal_id
       OR NEW.idempotency_key <> OLD.idempotency_key OR NEW.operation_id <> OLD.operation_id
       OR NEW.request_digest <> OLD.request_digest THEN
        RAISE EXCEPTION 'Creation Engine terminal receipt or identity is immutable' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER ce_receipts_guard BEFORE UPDATE OR DELETE ON ce_receipts
FOR EACH ROW EXECUTE FUNCTION ce_guard_receipt();

CREATE OR REPLACE FUNCTION ce_check_resource_bounds() RETURNS trigger AS $$
DECLARE
    amount jsonb := convert_from(NEW.current, 'UTF8')::jsonb;
    maximum jsonb := convert_from(NEW.maximum, 'UTF8')::jsonb;
    n numeric := (amount->>'numerator')::numeric;
    d numeric := (amount->>'denominator')::numeric;
    mn numeric := (maximum->>'numerator')::numeric;
    md numeric := (maximum->>'denominator')::numeric;
BEGIN
    IF jsonb_typeof(amount->'numerator') <> 'number' OR jsonb_typeof(amount->'denominator') <> 'number'
       OR jsonb_typeof(maximum->'numerator') <> 'number' OR jsonb_typeof(maximum->'denominator') <> 'number'
       OR n <> trunc(n) OR d <> trunc(d) OR mn <> trunc(mn) OR md <> trunc(md)
       OR abs(n) > 9007199254740991 OR d > 9007199254740991
       OR abs(mn) > 9007199254740991 OR md > 9007199254740991
       OR n IS NULL OR d IS NULL OR mn IS NULL OR md IS NULL OR d <= 0 OR md <= 0
       OR n < 0 OR mn < 0 OR n * md > mn * d THEN
        RAISE EXCEPTION 'Creation Engine resource bound violation' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER ce_resource_bounds BEFORE INSERT OR UPDATE ON ce_resource_ledger
FOR EACH ROW EXECUTE FUNCTION ce_check_resource_bounds();
