"""Persisted runtime state per game session."""

from vtt_app.extensions import db
from vtt_app.utils.time import utcnow


class SessionState(db.Model):
    """Durable runtime state envelope for one game session."""

    __tablename__ = "session_states"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False, unique=True, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True)
    active_map_id = db.Column(db.Integer, db.ForeignKey("campaign_maps.id"), index=True)

    state_status = db.Column(db.String(20), default="preparing", nullable=False)
    snapshot_json = db.Column(db.JSON)
    version = db.Column(db.Integer, default=1, nullable=False)
    last_synced_at = db.Column(db.DateTime, default=utcnow, index=True)

    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Avoid collision with GameSession.session_state (string state column).
    game_session = db.relationship("GameSession", backref=db.backref("runtime_state", uselist=False))
    campaign = db.relationship("Campaign")
    active_map = db.relationship("CampaignMap")

    def __repr__(self):
        return f"<SessionState session={self.game_session_id} v={self.version}>"

    def bump_version(self):
        self.version += 1
        self.last_synced_at = utcnow()

    def serialize(self):
        return {
            "id": self.id,
            "game_session_id": self.game_session_id,
            "campaign_id": self.campaign_id,
            "active_map_id": self.active_map_id,
            "state_status": self.state_status,
            "snapshot_json": self.snapshot_json or {},
            "version": self.version,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
