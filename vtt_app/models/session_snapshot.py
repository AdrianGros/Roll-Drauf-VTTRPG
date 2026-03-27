"""Session snapshot model for start/end recap checkpoints."""

from datetime import datetime

from vtt_app.extensions import db


class SessionSnapshot(db.Model):
    """Checkpoint payload captured at key lifecycle transitions."""

    __tablename__ = "session_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False, index=True)
    snapshot_type = db.Column(db.String(20), nullable=False, index=True)  # start, end
    state_version = db.Column(db.Integer, nullable=False, default=1)
    payload_json = db.Column(db.JSON, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    game_session = db.relationship("GameSession", backref="snapshots")
    creator = db.relationship("User")

    def __repr__(self):
        return f"<SessionSnapshot {self.id} session={self.game_session_id} type={self.snapshot_type}>"

    def serialize(self):
        return {
            "id": self.id,
            "game_session_id": self.game_session_id,
            "snapshot_type": self.snapshot_type,
            "state_version": self.state_version,
            "payload_json": self.payload_json or {},
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
