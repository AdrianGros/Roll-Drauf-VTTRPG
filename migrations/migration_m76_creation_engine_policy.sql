-- M76: G1 WP6. Additive after M75; no changes to legacy tables or live authority.
CREATE TABLE IF NOT EXISTS ce_policies (
    scope_id VARCHAR(128) NOT NULL REFERENCES ce_runtime_scopes(id),
    policy_id VARCHAR(128) NOT NULL,
    version BIGINT NOT NULL CHECK (version BETWEEN 1 AND 9007199254740991),
    canonical BYTEA NOT NULL,
    PRIMARY KEY (scope_id, policy_id, version)
);
CREATE TABLE IF NOT EXISTS ce_policy_epochs (
    scope_id VARCHAR(128) NOT NULL REFERENCES ce_runtime_scopes(id),
    principal_id INTEGER NOT NULL REFERENCES users(id),
    entitlement_epoch BIGINT NOT NULL DEFAULT 0 CHECK (entitlement_epoch BETWEEN 0 AND 9007199254740991),
    entitlements BYTEA NOT NULL DEFAULT '[]',
    valid_until TIMESTAMPTZ,
    PRIMARY KEY (scope_id, principal_id)
);
CREATE TABLE IF NOT EXISTS ce_view_as_sessions (
    id VARCHAR(128) PRIMARY KEY,
    scope_id VARCHAR(128) NOT NULL REFERENCES ce_runtime_scopes(id),
    operator_id INTEGER NOT NULL REFERENCES users(id),
    member_id INTEGER NOT NULL REFERENCES users(id),
    access_stamp VARCHAR(71) NOT NULL,
    policy_epoch BIGINT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    closed_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS ce_public_receipt_requests (
    scope_id VARCHAR(128) NOT NULL,
    principal_id INTEGER NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    request BYTEA NOT NULL,
    PRIMARY KEY (scope_id, principal_id, idempotency_key),
    FOREIGN KEY (scope_id, principal_id, idempotency_key) REFERENCES ce_receipts(scope_id, principal_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS ix_ce_view_as_sessions_scope_id ON ce_view_as_sessions(scope_id);
CREATE TABLE IF NOT EXISTS ce_public_subscriptions (
    id VARCHAR(128) PRIMARY KEY,
    scope_id VARCHAR(128) NOT NULL REFERENCES ce_runtime_scopes(id),
    principal_id INTEGER NOT NULL REFERENCES users(id),
    connection_id VARCHAR(128) NOT NULL,
    access_stamp VARCHAR(71) NOT NULL,
    policy_epoch BIGINT NOT NULL,
    authority_epoch BIGINT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_ce_public_subscriptions_scope_id ON ce_public_subscriptions(scope_id);
CREATE TABLE IF NOT EXISTS ce_delivery_cursors (
    id VARCHAR(128) PRIMARY KEY,
    subscription_id VARCHAR(128) NOT NULL REFERENCES ce_public_subscriptions(id),
    sequence BIGINT NOT NULL CHECK (sequence BETWEEN 0 AND 9007199254740991),
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ce_delivery_cursors_subscription_id ON ce_delivery_cursors(subscription_id);
CREATE TABLE IF NOT EXISTS ce_security_audit (
    id VARCHAR(128) PRIMARY KEY,
    scope_id VARCHAR(128) NOT NULL REFERENCES ce_runtime_scopes(id),
    principal_id INTEGER NOT NULL REFERENCES users(id),
    kind VARCHAR(128) NOT NULL,
    canonical BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ce_security_audit_scope_id ON ce_security_audit(scope_id);
-- M73's generic append-only guard also protects policy revisions and security history.
DROP TRIGGER IF EXISTS ce_policy_append_only ON ce_policies;
CREATE TRIGGER ce_policy_append_only BEFORE UPDATE OR DELETE ON ce_policies
    FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();
DROP TRIGGER IF EXISTS ce_security_audit_append_only ON ce_security_audit;
CREATE TRIGGER ce_security_audit_append_only BEFORE UPDATE OR DELETE ON ce_security_audit
    FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();
DROP TRIGGER IF EXISTS ce_receipt_request_append_only ON ce_public_receipt_requests;
CREATE TRIGGER ce_receipt_request_append_only BEFORE UPDATE OR DELETE ON ce_public_receipt_requests
    FOR EACH ROW EXECUTE FUNCTION ce_reject_mutation();
