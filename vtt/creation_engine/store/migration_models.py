"""Additive WP7 mapping, parity history, inputs and representation records."""

from vtt.extensions import db


class CeMigrationLedger(db.Model):
    __tablename__ = "ce_migration_ledger"
    source_type = db.Column(db.String(64), primary_key=True)
    source_id = db.Column(db.Integer, primary_key=True)
    migration_version = db.Column(db.BigInteger, primary_key=True)
    opaque_id = db.Column(db.String(128), nullable=False, unique=True)
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), nullable=False, index=True)


class CeLegacyScopeLink(db.Model):
    __tablename__ = "ce_legacy_scope_links"
    source_type = db.Column(db.String(16), primary_key=True)
    source_id = db.Column(db.Integer, primary_key=True)
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), nullable=False, unique=True)


class CeMigrationState(db.Model):
    __tablename__ = "ce_migration_states"
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), primary_key=True)
    report_id = db.Column(db.String(128))
    frozen_digest = db.Column(db.String(71))
    cutover_version = db.Column(db.BigInteger)


class CeParityReport(db.Model):
    __tablename__ = "ce_parity_reports"
    id = db.Column(db.String(128), primary_key=True)
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), nullable=False)
    source_digest = db.Column(db.String(71), nullable=False)
    digest = db.Column(db.String(71), nullable=False)
    canonical = db.Column(db.LargeBinary, nullable=False)
    snapshots = db.Column(db.LargeBinary, nullable=False)


class CeParityApproval(db.Model):
    __tablename__ = "ce_parity_approvals"
    report_id = db.Column(db.String(128), db.ForeignKey("ce_parity_reports.id"), primary_key=True)
    discrepancy_id = db.Column(db.String(128), primary_key=True)
    principal_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    capacity = db.Column(db.String(16), primary_key=True)
    resolution = db.Column(db.String(32), nullable=False)
    reason = db.Column(db.Text, nullable=False)


class CeLegacyInput(db.Model):
    __tablename__ = "ce_legacy_inputs"
    instance_id = db.Column(db.String(128), db.ForeignKey("ce_instances.id"), primary_key=True)
    bases = db.Column(db.LargeBinary, nullable=False)
    overrides = db.Column(db.LargeBinary, nullable=False)
    equipped = db.Column(db.Boolean)


class CeRepresentation(db.Model):
    __tablename__ = "ce_representations"
    source_type = db.Column(db.String(64), primary_key=True)
    source_id = db.Column(db.Integer, primary_key=True)
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"), nullable=False, index=True)
    instance_id = db.Column(db.String(128), db.ForeignKey("ce_instances.id"), nullable=False)


class CeLegacyGrant(db.Model):
    __tablename__ = "ce_grants"
    id = db.Column(db.String(128), primary_key=True)
    source_instance_id = db.Column(db.String(128), db.ForeignKey("ce_instances.id"), nullable=False)
    choice_id = db.Column(db.String(128), nullable=False)
    canonical = db.Column(db.LargeBinary, nullable=False)
    __table_args__ = (db.UniqueConstraint("source_instance_id", "choice_id"),)


class CeWorkspaceCommand(db.Model):
    __tablename__ = "ce_workspace_commands"
    workspace_id = db.Column(db.String(128), db.ForeignKey("ce_workspaces.id"), primary_key=True)
    principal_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    idempotency_key = db.Column(db.String(128), primary_key=True)
    scope_id = db.Column(db.String(128), db.ForeignKey("ce_runtime_scopes.id"))
    request_digest = db.Column(db.String(71), nullable=False)
    receipt = db.Column(db.LargeBinary, nullable=False)


MIGRATION_TABLES = tuple(c.__table__ for c in (CeWorkspaceCommand, CeLegacyGrant, CeLegacyScopeLink, CeMigrationLedger, CeMigrationState, CeParityReport,
                                              CeParityApproval, CeLegacyInput, CeRepresentation))
