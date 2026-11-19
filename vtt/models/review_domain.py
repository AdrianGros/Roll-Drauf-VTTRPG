"""Additive scoped threads and explicit Atlas/campaign associations."""
from vtt.extensions import db
from vtt.utils.time import utcnow


class ReviewThread(db.Model):
    __tablename__ = 'review_threads'
    __table_args__ = (
        db.CheckConstraint('(private_conversation_id IS NULL) <> (campaign_id IS NULL)', name='ck_review_thread_parent'),
        db.UniqueConstraint('created_by', 'request_id', name='uq_review_thread_request'),
    )
    id = db.Column(db.Integer, primary_key=True)
    private_conversation_id = db.Column(db.Integer, db.ForeignKey('private_conversations.id'), index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_id = db.Column(db.String(36), nullable=False)
    request_title = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    revision = db.Column(db.Integer, nullable=False, default=1)
    closed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class ReviewThreadMessage(db.Model):
    __tablename__ = 'review_thread_messages'
    __table_args__ = (db.UniqueConstraint('thread_id', 'author_id', 'request_id', name='uq_review_thread_message'),)
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('review_threads.id', ondelete='CASCADE'), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_id = db.Column(db.String(36), nullable=False)
    content = db.Column(db.String(2000), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class AtlasCampaignLink(db.Model):
    __tablename__ = 'atlas_campaign_links'
    __table_args__ = (db.UniqueConstraint('created_by', 'request_id', name='uq_atlas_campaign_link_request'),)
    world_id = db.Column(db.String(36), db.ForeignKey('atlas_worlds.id', ondelete='CASCADE'), primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), primary_key=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_id = db.Column(db.String(36), nullable=False)
    revision = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
