-- M75: Pending decisions and immutable answer/version history (G1 WP5, §10).
-- Additive after M74. No production integration or data migration.
ALTER TABLE ce_runtime_scopes ADD COLUMN IF NOT EXISTS decision_timeout_seconds INTEGER NOT NULL DEFAULT 120;
ALTER TABLE ce_runtime_scopes ADD COLUMN IF NOT EXISTS clock_tolerance_seconds INTEGER NOT NULL DEFAULT 30;
ALTER TABLE ce_runtime_scopes ADD COLUMN IF NOT EXISTS decision_heartbeat_at TIMESTAMPTZ;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ce_decision_time_policy') THEN
        ALTER TABLE ce_runtime_scopes ADD CONSTRAINT ce_decision_time_policy
            CHECK (decision_timeout_seconds BETWEEN 30 AND 600 AND clock_tolerance_seconds BETWEEN 0 AND 600);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS ce_pending_decisions (
    id VARCHAR(128) NOT NULL,
    version BIGINT NOT NULL,
    scope_id VARCHAR(128) NOT NULL REFERENCES ce_runtime_scopes(id),
    action_id VARCHAR(128) NOT NULL REFERENCES ce_actions(id),
    checkpoint_id VARCHAR(128) NOT NULL REFERENCES ce_checkpoints(id),
    status VARCHAR(16) NOT NULL,
    canonical BYTEA NOT NULL,
    context_digest VARCHAR(71) NOT NULL,
    created_scope_version BIGINT NOT NULL,
    question BYTEA NOT NULL,
    timeout_seconds INTEGER NOT NULL,
    answer BYTEA,
    responder_id INTEGER REFERENCES users(id),
    closed_at TIMESTAMPTZ,
    PRIMARY KEY (id, version),
    CONSTRAINT ce_decision_versions CHECK (version BETWEEN 0 AND 9007199254740991 AND created_scope_version BETWEEN 0 AND 9007199254740991),
    CONSTRAINT ce_decision_timeout CHECK (timeout_seconds BETWEEN 30 AND 600),
    CONSTRAINT ce_decision_status CHECK (status IN ('open','answered','expired','invalidated')),
    CONSTRAINT ce_decision_closed CHECK ((status = 'open') = (closed_at IS NULL))
);
CREATE INDEX IF NOT EXISTS ix_ce_pending_decisions_scope_id ON ce_pending_decisions(scope_id);
CREATE UNIQUE INDEX IF NOT EXISTS ce_one_open_decision_per_action ON ce_pending_decisions(action_id) WHERE status = 'open';

CREATE OR REPLACE FUNCTION ce_guard_decision() RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE previous ce_pending_decisions%ROWTYPE;
DECLARE payload JSONB;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Decision history cannot be deleted' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    payload := convert_from(NEW.canonical, 'UTF8')::jsonb;
    IF payload->>'decisionId' IS DISTINCT FROM NEW.id
        OR (payload->>'decisionVersion')::bigint IS DISTINCT FROM NEW.version
        OR payload->>'actionId' IS DISTINCT FROM NEW.action_id
        OR payload->>'checkpointId' IS DISTINCT FROM NEW.checkpoint_id
        OR payload->>'status' IS DISTINCT FROM NEW.status THEN
        RAISE EXCEPTION 'Decision wire/record mismatch' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF TG_OP = 'INSERT' THEN
        SELECT * INTO previous FROM ce_pending_decisions WHERE id = NEW.id ORDER BY version DESC LIMIT 1;
        IF NEW.status <> 'open' OR NEW.answer IS NOT NULL OR NEW.responder_id IS NOT NULL
            OR NEW.version <> COALESCE(previous.version + 1, 0)
            OR (previous.id IS NOT NULL AND (previous.status IN ('open','answered') OR previous.answer IS NOT NULL
                OR previous.scope_id <> NEW.scope_id OR previous.action_id <> NEW.action_id)) THEN
            RAISE EXCEPTION 'Invalid decision version' USING ERRCODE = 'integrity_constraint_violation';
        END IF;
    ELSE
        IF OLD.status <> 'open' OR NEW.status = 'open'
            OR (to_jsonb(NEW) - ARRAY['status','canonical','answer','responder_id','closed_at'])
                IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['status','canonical','answer','responder_id','closed_at'])
            OR (payload - 'status') IS DISTINCT FROM (convert_from(OLD.canonical, 'UTF8')::jsonb - 'status')
            OR (NEW.status = 'answered' AND (NEW.answer IS NULL OR NEW.responder_id IS NULL))
            OR (NEW.status = 'invalidated' AND (NEW.answer IS NOT NULL OR NEW.responder_id IS NOT NULL)) THEN
            RAISE EXCEPTION 'Decision version/outcome is immutable' USING ERRCODE = 'integrity_constraint_violation';
        END IF;
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS ce_decision_guard ON ce_pending_decisions;
CREATE TRIGGER ce_decision_guard BEFORE INSERT OR UPDATE OR DELETE ON ce_pending_decisions
    FOR EACH ROW EXECUTE FUNCTION ce_guard_decision();
