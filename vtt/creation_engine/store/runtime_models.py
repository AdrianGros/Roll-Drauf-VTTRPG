"""Additive PostgreSQL runtime tables (migration m74, G1 WP4).

There is one locked authority row per scope. History tables are append-only;
receipts may progress from accepted to a final outcome, but a final receipt
cannot change. Runtime tables are not imported by the live application yet.
"""

from vtt.extensions import db


class CeRuntimeScope(db.Model):
    __tablename__ = "ce_runtime_scopes"
    __table_args__ = (
        db.CheckConstraint("kind IN ('sandbox', 'campaign')", name="ce_scope_kind"),
        db.CheckConstraint("migration_state IN ('LEGACY','SHADOW','FROZEN_FOR_CUTOVER','ENGINE','ROLLBACK_REVIEW')",
                           name="ce_scope_authority_state"),
        db.CheckConstraint("state_version BETWEEN 0 AND 9007199254740991 AND authority_epoch BETWEEN 0 AND 9007199254740991",
                           name="ce_scope_versions"),
    )
    id = db.Column(db.String(128), primary_key=True)
    kind = db.Column(db.String(16), nullable=False)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"))
    fixture = db.Column(db.Boolean, nullable=False, default=False)
    migration_state = db.Column(db.String(32), nullable=False, default="LEGACY")
    lock_id = db.Column(db.String(128), db.ForeignKey("ce_execution_locks.lock_id"), nullable=False)
    state_version = db.Column(db.BigInteger, nullable=False, default=0)
    authority_epoch = db.Column(db.BigInteger, nullable=False, default=1)
    policy_version = db.Column(db.BigInteger, nullable=False, default=1)
    event_sequence = db.Column(db.BigInteger, nullable=False, default=0)
    active_action_id = db.Column(db.String(128))
    fence_epoch = db.Column(db.BigInteger, nullable=False, default=0)
    lease_owner = db.Column(db.String(128))
    lease_expires_at = db.Column(db.DateTime(timezone=True))
    time_watermark = db.Column(db.DateTime(timezone=True), nullable=False)
    deleted = db.Column(db.Boolean, nullable=False, default=False)


class CeInstance(db.Model):
    __tablename__ = "ce_instances"
    id = db.Column(db.String(128), primary_key=True)
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), nullable=False, index=True)
    revision_id = db.Column(db.String(128), db.ForeignKey("ce_revisions.id"), nullable=False)
    controller_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    holder_id = db.Column(db.String(128), db.ForeignKey("ce_instances.id"))


class CeResourceLedger(db.Model):
    __tablename__ = "ce_resource_ledger"
    __table_args__ = (
        db.CheckConstraint("adjust_bound_policy IN ('reject', 'clamp_report_delta')", name="ce_resource_adjust_policy"),
    )
    instance_id = db.Column(db.String(128), db.ForeignKey("ce_instances.id"), primary_key=True)
    resource_id = db.Column(db.String(128), primary_key=True)
    unit = db.Column(db.String(128), nullable=False)
    current = db.Column(db.LargeBinary, nullable=False)
    maximum = db.Column(db.LargeBinary, nullable=False)
    adjust_bound_policy = db.Column(db.String(32), nullable=False)


class CeAction(db.Model):
    __tablename__ = "ce_actions"
    __table_args__ = (
        db.CheckConstraint("depth BETWEEN 0 AND 16", name="ce_action_depth"),
        db.CheckConstraint("state IN ('PROPOSED','WAITING_PRECOMMIT','ACTIVE','WAITING_DECISION','SUSPENDED','COMPLETED','CANCELLED','FAILED_PRECOMMIT')",
                           name="ce_action_state"),
    )
    id = db.Column(db.String(128), primary_key=True)
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), nullable=False, index=True)
    principal_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    request = db.Column(db.LargeBinary, nullable=False)
    plan = db.Column(db.LargeBinary, nullable=False)
    state = db.Column(db.String(32), nullable=False)
    deadline = db.Column(db.DateTime(timezone=True), nullable=False)
    root_id = db.Column(db.String(128), nullable=False)
    parent_id = db.Column(db.String(128), db.ForeignKey("ce_actions.id"))
    depth = db.Column(db.Integer, nullable=False)
    next_window = db.Column(db.Integer, nullable=False)
    version = db.Column(db.BigInteger, nullable=False)
    last_checkpoint_id = db.Column(db.String(128))
    error_code = db.Column(db.String(128))
    budget = db.Column(db.LargeBinary, nullable=False)


class CeCheckpoint(db.Model):
    __tablename__ = "ce_checkpoints"
    __table_args__ = (db.UniqueConstraint("action_id", "window_index"),)
    id = db.Column(db.String(128), primary_key=True)
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), nullable=False)
    action_id = db.Column(db.String(128), db.ForeignKey("ce_actions.id"), nullable=False)
    window_index = db.Column(db.Integer, nullable=False)
    state_version = db.Column(db.BigInteger, nullable=False)
    outcome = db.Column(db.LargeBinary, nullable=False)
    outcome_digest = db.Column(db.String(71), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)


class CeReceipt(db.Model):
    __tablename__ = "ce_receipts"
    __table_args__ = (db.CheckConstraint("status IN ('accepted','committed','rejected','suspended')", name="ce_receipt_status"),)
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), primary_key=True)
    principal_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    idempotency_key = db.Column(db.String(128), primary_key=True)
    operation_id = db.Column(db.String(128), nullable=False, unique=True)
    request_digest = db.Column(db.String(71), nullable=False)
    status = db.Column(db.String(16), nullable=False)
    canonical = db.Column(db.LargeBinary, nullable=False)


class CeResourceEntry(db.Model):
    __tablename__ = "ce_resource_entries"
    id = db.Column(db.String(128), primary_key=True)
    checkpoint_id = db.Column(db.String(128), db.ForeignKey("ce_checkpoints.id"), nullable=False)
    instance_id = db.Column(db.String(128), db.ForeignKey("ce_instances.id"), nullable=False)
    resource_id = db.Column(db.String(128), nullable=False)
    canonical = db.Column(db.LargeBinary, nullable=False)


class CeRandomRecord(db.Model):
    __tablename__ = "ce_random_records"
    checkpoint_id = db.Column(db.String(128), db.ForeignKey("ce_checkpoints.id"), primary_key=True)
    roll_id = db.Column(db.String(128), primary_key=True)
    canonical = db.Column(db.LargeBinary, nullable=False)


class CeEffectApplication(db.Model):
    __tablename__ = "ce_effect_applications"
    id = db.Column(db.String(128), primary_key=True)
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), nullable=False)
    checkpoint_id = db.Column(db.String(128), db.ForeignKey("ce_checkpoints.id"), nullable=False)
    target_id = db.Column(db.String(128), db.ForeignKey("ce_instances.id"), nullable=False, index=True)
    canonical = db.Column(db.LargeBinary, nullable=False)


class CeDomainEvent(db.Model):
    __tablename__ = "ce_domain_events"
    __table_args__ = (db.UniqueConstraint("scope_id", "sequence"),)
    id = db.Column(db.String(128), primary_key=True)
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), nullable=False)
    sequence = db.Column(db.BigInteger, nullable=False)
    action_id = db.Column(db.String(128), db.ForeignKey("ce_actions.id"), nullable=False)
    checkpoint_id = db.Column(db.String(128), db.ForeignKey("ce_checkpoints.id"))
    canonical = db.Column(db.LargeBinary, nullable=False)


class CeOutbox(db.Model):
    __tablename__ = "ce_outbox"
    event_id = db.Column(db.String(128), db.ForeignKey("ce_domain_events.id"), primary_key=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    delivered_at = db.Column(db.DateTime(timezone=True))


class CeEventConsumption(db.Model):
    __tablename__ = "ce_event_consumptions"
    consumer = db.Column(db.String(128), primary_key=True)
    event_id = db.Column(db.String(128), db.ForeignKey("ce_domain_events.id"), primary_key=True)


RUNTIME_TABLES = tuple(cls.__table__ for cls in (CeRuntimeScope, CeInstance, CeResourceLedger, CeAction, CeCheckpoint,
                       CeReceipt, CeResourceEntry, CeRandomRecord, CeEffectApplication, CeDomainEvent, CeOutbox, CeEventConsumption))
