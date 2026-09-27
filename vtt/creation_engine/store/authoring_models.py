"""Append-only draft compilation snapshots and command results (M78)."""

from vtt.extensions import db


class CeAuthoringSnapshot(db.Model):
    __tablename__ = "ce_authoring_snapshots"
    draft_id = db.Column(db.String(128), primary_key=True)
    version = db.Column(db.BigInteger, primary_key=True)
    state = db.Column(db.LargeBinary, nullable=False)
    __table_args__ = (db.ForeignKeyConstraint(["draft_id", "version"],
                                              ["ce_draft_versions.draft_id", "ce_draft_versions.version"]),)


class CeDraftCommand(db.Model):
    __tablename__ = "ce_draft_commands"
    draft_id = db.Column(db.String(128), db.ForeignKey("ce_drafts.id"), primary_key=True)
    principal_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    idempotency_key = db.Column(db.String(128), primary_key=True)
    request_digest = db.Column(db.String(71), nullable=False)
    receipt = db.Column(db.LargeBinary, nullable=False)
    result = db.Column(db.LargeBinary, nullable=False)


class CeWorkspaceResult(db.Model):
    __tablename__ = "ce_workspace_results"
    workspace_id = db.Column(db.String(128), primary_key=True)
    principal_id = db.Column(db.Integer, primary_key=True)
    idempotency_key = db.Column(db.String(128), primary_key=True)
    result = db.Column(db.LargeBinary, nullable=False)
    __table_args__ = (db.ForeignKeyConstraint(["workspace_id", "principal_id", "idempotency_key"],
        ["ce_workspace_commands.workspace_id", "ce_workspace_commands.principal_id", "ce_workspace_commands.idempotency_key"]),)


AUTHORING_TABLES = tuple(c.__table__ for c in (CeAuthoringSnapshot, CeDraftCommand, CeWorkspaceResult))
