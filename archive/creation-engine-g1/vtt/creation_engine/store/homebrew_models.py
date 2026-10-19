"""M80 private homebrew sandboxes and append-only command outcomes."""

from vtt.extensions import db


class CeHomebrewSandbox(db.Model):
    __tablename__ = "ce_homebrew_sandboxes"
    id = db.Column(db.String(128), primary_key=True)
    workspace_id = db.Column(db.String(128), db.ForeignKey("ce_workspaces.id"), nullable=False, index=True)
    version = db.Column(db.BigInteger, nullable=False)
    execution_lock = db.Column(db.LargeBinary, nullable=False)
    state = db.Column(db.LargeBinary, nullable=False)
    __table_args__ = (db.CheckConstraint("version >= 1", name="ce_homebrew_version_positive"),)


class CeHomebrewEvent(db.Model):
    __tablename__ = "ce_homebrew_events"
    workspace_id = db.Column(db.String(128), db.ForeignKey("ce_workspaces.id"), primary_key=True)
    principal_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    idempotency_key = db.Column(db.String(128), primary_key=True)
    sandbox_id = db.Column(db.String(128), db.ForeignKey("ce_homebrew_sandboxes.id"), nullable=False)
    version = db.Column(db.BigInteger, nullable=False)
    request_digest = db.Column(db.String(71), nullable=False)
    command = db.Column(db.LargeBinary, nullable=False)
    result = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    __table_args__ = (db.UniqueConstraint("sandbox_id", "version", name="ce_homebrew_event_sequence"),)


HOMEBREW_TABLES = (CeHomebrewSandbox.__table__, CeHomebrewEvent.__table__)
