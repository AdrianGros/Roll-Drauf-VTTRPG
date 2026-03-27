"""Token runtime state model."""

from datetime import datetime

from vtt_app.extensions import db


class TokenState(db.Model):
    """Canonical token state scoped to one session/map."""

    __tablename__ = "token_states"

    id = db.Column(db.Integer, primary_key=True)
    session_state_id = db.Column(db.Integer, db.ForeignKey("session_states.id"), nullable=False, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False, index=True)
    map_id = db.Column(db.Integer, db.ForeignKey("campaign_maps.id"), nullable=False, index=True)

    character_id = db.Column(db.Integer, db.ForeignKey("characters.id"), index=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)

    name = db.Column(db.String(120), nullable=False)
    token_type = db.Column(db.String(20), default="player", nullable=False)
    x = db.Column(db.Integer, nullable=False)
    y = db.Column(db.Integer, nullable=False)
    size = db.Column(db.Integer, default=1, nullable=False)
    rotation = db.Column(db.Integer, default=0, nullable=False)

    hp_current = db.Column(db.Integer)
    hp_max = db.Column(db.Integer)
    initiative = db.Column(db.Integer)
    visibility = db.Column(db.String(20), default="public", nullable=False)
    metadata_json = db.Column(db.JSON)

    version = db.Column(db.Integer, default=1, nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, index=True)

    session_state = db.relationship("SessionState", backref="tokens")
    campaign = db.relationship("Campaign")
    game_session = db.relationship("GameSession")
    map = db.relationship("CampaignMap")
    character = db.relationship("Character")
    owner = db.relationship("User", foreign_keys=[owner_user_id])
    updater = db.relationship("User", foreign_keys=[updated_by])

    def __repr__(self):
        return f"<TokenState {self.id} session={self.game_session_id}>"

    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def serialize(self):
        return {
            "id": self.id,
            "session_state_id": self.session_state_id,
            "campaign_id": self.campaign_id,
            "game_session_id": self.game_session_id,
            "map_id": self.map_id,
            "character_id": self.character_id,
            "owner_user_id": self.owner_user_id,
            "name": self.name,
            "token_type": self.token_type,
            "x": self.x,
            "y": self.y,
            "size": self.size,
            "rotation": self.rotation,
            "hp_current": self.hp_current,
            "hp_max": self.hp_max,
            "initiative": self.initiative,
            "visibility": self.visibility,
            "metadata_json": self.metadata_json or {},
            "version": self.version,
            "updated_by": self.updated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
