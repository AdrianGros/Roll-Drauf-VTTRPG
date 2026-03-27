"""Moderation action model."""

from datetime import datetime

from vtt_app.extensions import db


class ModerationAction(db.Model):
    """Append-only moderation action record."""

    __tablename__ = "moderation_actions"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), index=True)

    action_type = db.Column(db.String(30), nullable=False)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subject_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    subject_message_id = db.Column(db.Integer, db.ForeignKey("chat_messages.id"), index=True)
    source_report_id = db.Column(db.Integer, db.ForeignKey("moderation_reports.id"), index=True)

    reason = db.Column(db.Text)
    starts_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ends_at = db.Column(db.DateTime, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)

    revoked_at = db.Column(db.DateTime, index=True)
    revoked_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    campaign = db.relationship("Campaign")
    game_session = db.relationship("GameSession")
    actor = db.relationship("User", foreign_keys=[actor_user_id])
    subject_user = db.relationship("User", foreign_keys=[subject_user_id])
    subject_message = db.relationship("ChatMessage", foreign_keys=[subject_message_id])
    source_report = db.relationship("ModerationReport", foreign_keys=[source_report_id])
    revoked_by = db.relationship("User", foreign_keys=[revoked_by_user_id])

    def __repr__(self):
        return f"<ModerationAction {self.id} type={self.action_type} active={self.is_active}>"

    def serialize(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "game_session_id": self.game_session_id,
            "action_type": self.action_type,
            "actor_user_id": self.actor_user_id,
            "actor_username": self.actor.username if self.actor else None,
            "subject_user_id": self.subject_user_id,
            "subject_username": self.subject_user.username if self.subject_user else None,
            "subject_message_id": self.subject_message_id,
            "source_report_id": self.source_report_id,
            "reason": self.reason,
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "is_active": self.is_active,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoked_by_user_id": self.revoked_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
