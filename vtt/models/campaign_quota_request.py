"""FV15: an account's request for a higher active-campaign quota.

A request is never an entitlement. Submitting, cancelling and rejecting leave
User.active_campaigns_quota unchanged; only an explicit owner/admin approval
writes a manually chosen total. ``pending_key`` equals the requester ID while
pending and is NULL once terminal, so the unique column allows one pending
request per account on SQLite and PostgreSQL while keeping terminal history.

Self-contained on purpose (only db/utcnow imports): the additive schema
helper executes this file against the previously running image.
"""

from vtt.extensions import db
from vtt.utils.time import utcnow


class CampaignQuotaRequest(db.Model):
    __tablename__ = 'campaign_quota_requests'
    STATUSES = ('pending', 'approved', 'rejected', 'cancelled')
    TEXT_MAX = 500
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')",
            name='ck_campaign_quota_request_status'),
        db.CheckConstraint(
            "(status = 'pending' AND pending_key IS NOT NULL AND pending_key = requester_id)"
            " OR (status <> 'pending' AND pending_key IS NULL)",
            name='ck_campaign_quota_request_pending_key'),
        db.CheckConstraint(
            'current_quota > 0 AND desired_total > current_quota',
            name='ck_campaign_quota_request_totals'),
        db.CheckConstraint(
            "approved_total IS NULL OR status = 'approved'",
            name='ck_campaign_quota_request_approved_total'),
        db.Index('ix_campaign_quota_requests_requester_created', 'requester_id', 'created_at'),
        db.Index('ix_campaign_quota_requests_status_created', 'status', 'created_at'),
    )

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Finite live quota at submission time; the live value stays on User.
    current_quota = db.Column(db.Integer, nullable=False)
    desired_total = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    pending_key = db.Column(db.Integer, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer_note = db.Column(db.String(500))
    decided_at = db.Column(db.DateTime)
    approved_total = db.Column(db.Integer)

    def __repr__(self):
        return f'<CampaignQuotaRequest {self.id} {self.status}>'
