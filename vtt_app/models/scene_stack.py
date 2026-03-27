"""Scene stack model for layered session play spaces."""

from datetime import datetime

from vtt_app.extensions import db


class SceneStack(db.Model):
    """One scene stack per game session."""

    __tablename__ = "scene_stacks"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False, unique=True, index=True)
    name = db.Column(db.String(120), nullable=False, default="Default Scene Stack")
    active_layer_id = db.Column(db.Integer, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    campaign = db.relationship("Campaign")
    game_session = db.relationship("GameSession", backref=db.backref("scene_stack", uselist=False))
    creator = db.relationship("User")

    def __repr__(self):
        return f"<SceneStack {self.id} session={self.game_session_id}>"

    def serialize(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "game_session_id": self.game_session_id,
            "name": self.name,
            "active_layer_id": self.active_layer_id,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
