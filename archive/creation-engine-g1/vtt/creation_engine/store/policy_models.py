"""M76: versioned policy, audience sessions/cursors and append-only security audit."""

from vtt.extensions import db


class CePolicy(db.Model):
    __tablename__ = "ce_policies"
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), primary_key=True)
    policy_id = db.Column(db.String(128), primary_key=True)
    version = db.Column(db.BigInteger, primary_key=True)
    canonical = db.Column(db.LargeBinary, nullable=False)


class CePolicyEpoch(db.Model):
    __tablename__ = "ce_policy_epochs"
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), primary_key=True)
    principal_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    entitlement_epoch = db.Column(db.BigInteger, nullable=False, default=0)
    entitlements = db.Column(db.LargeBinary, nullable=False, default=b"[]", server_default="[]")
    valid_until = db.Column(db.DateTime(timezone=True))


class CePublicReceiptRequest(db.Model):
    __tablename__ = "ce_public_receipt_requests"
    __table_args__ = (db.ForeignKeyConstraint(["scope_id", "principal_id", "idempotency_key"],
                         ["ce_receipts.scope_id", "ce_receipts.principal_id", "ce_receipts.idempotency_key"]),)
    scope_id = db.Column(db.String(128), primary_key=True)
    principal_id = db.Column(db.Integer, primary_key=True)
    idempotency_key = db.Column(db.String(128), primary_key=True)
    request = db.Column(db.LargeBinary, nullable=False)


class CeViewAsSession(db.Model):
    __tablename__ = "ce_view_as_sessions"
    id = db.Column(db.String(128), primary_key=True)
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), nullable=False, index=True)
    operator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    access_stamp = db.Column(db.String(71), nullable=False)
    policy_epoch = db.Column(db.BigInteger, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    closed_at = db.Column(db.DateTime(timezone=True))


class CeSubscription(db.Model):
    __tablename__ = "ce_public_subscriptions"
    id = db.Column(db.String(128), primary_key=True)
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), nullable=False, index=True)
    principal_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    connection_id = db.Column(db.String(128), nullable=False)
    access_stamp = db.Column(db.String(71), nullable=False)
    policy_epoch = db.Column(db.BigInteger, nullable=False)
    authority_epoch = db.Column(db.BigInteger, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True))


class CeDeliveryCursor(db.Model):
    __tablename__ = "ce_delivery_cursors"
    id = db.Column(db.String(128), primary_key=True)
    subscription_id = db.Column(db.String(128), db.ForeignKey("ce_public_subscriptions.id"), nullable=False, index=True)
    sequence = db.Column(db.BigInteger, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)


class CeSecurityAudit(db.Model):
    __tablename__ = "ce_security_audit"
    id = db.Column(db.String(128), primary_key=True)
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), nullable=False, index=True)
    principal_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    kind = db.Column(db.String(128), nullable=False)
    canonical = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)


POLICY_TABLES = tuple(c.__table__ for c in (CePolicy, CePolicyEpoch, CePublicReceiptRequest, CeViewAsSession, CeSubscription,
                                           CeDeliveryCursor, CeSecurityAudit))
