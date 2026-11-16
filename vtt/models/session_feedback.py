"""Personal reusable tokens and campaign text rooms; additive storage only."""
from vtt.extensions import db
from vtt.utils.time import utcnow


class TokenTemplate(db.Model):
    __tablename__ = "token_templates"
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    mode = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    values = db.Column(db.JSON, nullable=False)
    revision = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def serialize(self):
        return dict(id=self.id, name=self.name, values=self.values, revision=self.revision)


class CampaignChatMessage(db.Model):
    __tablename__ = "campaign_chat_messages"
    __table_args__ = (db.UniqueConstraint("campaign_id", "author_user_id", "client_event_id",
                                         name="uq_campaign_chat_event"),)
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True)
    author_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    client_event_id = db.Column(db.String(36), nullable=False)
    content = db.Column(db.String(2000), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    author = db.relationship("User")

    def serialize(self):
        return dict(id=self.id, author_user_id=self.author_user_id,
                    author_name=self.author.username if self.author else "?",
                    client_event_id=self.client_event_id, content=self.content,
                    created_at=self.created_at.isoformat() + "Z")
