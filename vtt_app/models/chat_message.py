"""Community chat message model."""

from datetime import datetime

from vtt_app.extensions import db


class ChatMessage(db.Model):
    """Persisted session-scoped chat message with moderation metadata."""

    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False, index=True)
    author_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    content = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.String(20), default="user", nullable=False)
    client_event_id = db.Column(db.String(120), index=True)
    moderation_state = db.Column(db.String(30), default="visible", nullable=False)

    edited_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime, index=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    campaign = db.relationship("Campaign")
    game_session = db.relationship("GameSession")
    author = db.relationship("User", foreign_keys=[author_user_id])
    deleter = db.relationship("User", foreign_keys=[deleted_by])

    __table_args__ = (
        db.UniqueConstraint(
            "author_user_id",
            "game_session_id",
            "client_event_id",
            name="uq_chat_message_author_session_event",
        ),
    )

    def __repr__(self):
        return f"<ChatMessage {self.id} session={self.game_session_id} author={self.author_user_id}>"

    def serialize(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "game_session_id": self.game_session_id,
            "author_user_id": self.author_user_id,
            "author_username": self.author.username if self.author else None,
            "content": self.content,
            "content_type": self.content_type,
            "client_event_id": self.client_event_id,
            "moderation_state": self.moderation_state,
            "edited_at": self.edited_at.isoformat() if self.edited_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "deleted_by": self.deleted_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
