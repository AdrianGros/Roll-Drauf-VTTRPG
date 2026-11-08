"""One voluntary research survey response per VTT account."""

from vtt.extensions import db
from vtt.utils.time import utcnow


class ResearchSurveyResponse(db.Model):
    __tablename__ = "research_survey_responses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    topic = db.Column(db.String(32), nullable=False)
    usefulness = db.Column(db.String(32), nullable=False)
    concern = db.Column(db.String(32), nullable=False)
    vtt_priority = db.Column(db.String(32), nullable=False)
    comment = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def serialize_own(self):
        return {
            "topic": self.topic,
            "usefulness": self.usefulness,
            "concern": self.concern,
            "vtt_priority": self.vtt_priority,
            "comment": self.comment,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
