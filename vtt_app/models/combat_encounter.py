"""Combat encounter model for session-scoped turn lifecycle."""

from datetime import datetime

from vtt_app.extensions import db


class CombatEncounter(db.Model):
    """Persisted encounter state for one game session."""

    __tablename__ = "combat_encounters"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False, index=True)
    session_state_id = db.Column(db.Integer, db.ForeignKey("session_states.id"), nullable=False, index=True)

    status = db.Column(db.String(20), default="preparing", nullable=False)
    round_number = db.Column(db.Integer, default=1, nullable=False)
    turn_index = db.Column(db.Integer, default=0, nullable=False)
    active_token_id = db.Column(db.Integer, db.ForeignKey("token_states.id"), index=True)
    initiative_order_json = db.Column(db.JSON, default=list)
    version = db.Column(db.Integer, default=1, nullable=False)

    started_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    ended_by = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    campaign = db.relationship("Campaign")
    game_session = db.relationship("GameSession")
    session_state = db.relationship("SessionState")
    active_token = db.relationship("TokenState", foreign_keys=[active_token_id])
    starter = db.relationship("User", foreign_keys=[started_by])
    ender = db.relationship("User", foreign_keys=[ended_by])

    def __repr__(self):
        return f"<CombatEncounter {self.id} session={self.game_session_id} status={self.status}>"

    def serialize(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "game_session_id": self.game_session_id,
            "session_state_id": self.session_state_id,
            "status": self.status,
            "round_number": self.round_number,
            "turn_index": self.turn_index,
            "active_token_id": self.active_token_id,
            "initiative_order": list(self.initiative_order_json or []),
            "version": self.version,
            "started_by": self.started_by,
            "ended_by": self.ended_by,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
