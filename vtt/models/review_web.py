"""Account-bound requests to our print UI; never proof of physical printing."""

from vtt.extensions import db
from vtt.utils.time import utcnow


class ReviewPrintRequest(db.Model):
    __tablename__ = 'review_print_requests'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'request_id', name='uq_review_print_request'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    request_id = db.Column(db.String(36), nullable=False)
    ruleset = db.Column(db.String(160), nullable=False)
    document_id = db.Column(db.String(160), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
