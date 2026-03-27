"""Moderation report model."""

from datetime import datetime

from vtt_app.extensions import db


class ModerationReport(db.Model):
    """User-submitted report with moderation triage state."""

    __tablename__ = "moderation_reports"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), index=True)
    reporter_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    target_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    target_message_id = db.Column(db.Integer, db.ForeignKey("chat_messages.id"), index=True)

    reason_code = db.Column(db.String(30), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="open", nullable=False)
    priority = db.Column(db.String(20), default="medium", nullable=False)

    assigned_to_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    resolution_note = db.Column(db.Text)
    resolved_action_id = db.Column(db.Integer, db.ForeignKey("moderation_actions.id"), index=True)
    resolved_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    campaign = db.relationship("Campaign")
    game_session = db.relationship("GameSession")
    reporter = db.relationship("User", foreign_keys=[reporter_user_id])
    target_user = db.relationship("User", foreign_keys=[target_user_id])
    target_message = db.relationship("ChatMessage", foreign_keys=[target_message_id])
    assignee = db.relationship("User", foreign_keys=[assigned_to_user_id])

    def __repr__(self):
        return f"<ModerationReport {self.id} campaign={self.campaign_id} status={self.status}>"

    def serialize(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "game_session_id": self.game_session_id,
            "reporter_user_id": self.reporter_user_id,
            "reporter_username": self.reporter.username if self.reporter else None,
            "target_user_id": self.target_user_id,
            "target_username": self.target_user.username if self.target_user else None,
            "target_message_id": self.target_message_id,
            "reason_code": self.reason_code,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "assigned_to_user_id": self.assigned_to_user_id,
            "assigned_to_username": self.assignee.username if self.assignee else None,
            "resolution_note": self.resolution_note,
            "resolved_action_id": self.resolved_action_id,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
