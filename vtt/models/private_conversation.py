"""Private fixed pairs. No campaign role or table room grants access to these rows."""
from vtt.extensions import db
from vtt.utils.time import utcnow


class PrivateConversation(db.Model):
    __tablename__ = 'private_conversations'
    __table_args__ = (
        db.UniqueConstraint('campaign_id', 'participant_low_id', 'participant_high_id', name='uq_private_pair'),
        db.CheckConstraint('participant_low_id < participant_high_id', name='ck_private_pair_order'),
    )
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    participant_low_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    participant_high_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)


class PrivateMessage(db.Model):
    __tablename__ = 'private_messages'
    __table_args__ = (
        db.UniqueConstraint('conversation_id', 'author_user_id', 'client_event_id', name='uq_private_message_event'),
        db.CheckConstraint('length(content) BETWEEN 1 AND 2000', name='ck_private_message_length'),
    )
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('private_conversations.id'), nullable=False, index=True)
    author_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    client_event_id = db.Column(db.String(36), nullable=False)
    content = db.Column(db.String(2000), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
