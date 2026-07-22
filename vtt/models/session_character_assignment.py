"""Persistent character-to-session assignment for pre-table prep."""

from vtt.extensions import db
from vtt.utils.time import utcnow


class SessionCharacterAssignment(db.Model):
    """Assign a campaign-linked character to a specific session."""

    __tablename__ = "session_character_assignments"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False, index=True)
    character_id = db.Column(db.Integer, db.ForeignKey("characters.id"), nullable=False, index=True)
    assigned_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    game_session = db.relationship(
        "GameSession",
        backref=db.backref("character_assignments", cascade="all, delete-orphan", lazy=True),
    )
    character = db.relationship(
        "Character",
        backref=db.backref("session_assignments", cascade="all, delete-orphan", lazy=True),
    )
    assigned_by = db.relationship("User", foreign_keys=[assigned_by_user_id])

    __table_args__ = (
        db.UniqueConstraint("game_session_id", "character_id", name="uq_session_character_assignment"),
    )

    def serialize(self):
        return {
            "id": self.id,
            "session_id": self.game_session_id,
            "character_id": self.character_id,
            "assigned_by_user_id": self.assigned_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
