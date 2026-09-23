"""Invite token model for campaign invitations."""

from datetime import timedelta
import secrets
from vtt.extensions import db
from vtt.utils.time import utcnow


class InviteToken(db.Model):
    """Campaign invitation token (shareable link)."""

    __tablename__ = 'invite_tokens'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    
    # invited_user_email set = legacy per-user link (pre-2026-09-22):
    # exactly one accept, tied to that email. NULL = the current generic
    # campaign link: shareable as-is, good for max_uses redemptions, each
    # one filing a "pending" join request rather than granting membership
    # outright (naming a player up front for every single invite was the
    # actual friction - Adrian, 2026-09-22).
    invited_user_email = db.Column(db.String(120))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: utcnow() + timedelta(days=7))
    used_at = db.Column(db.DateTime)
    max_uses = db.Column(db.Integer, nullable=False, default=5)
    use_count = db.Column(db.Integer, nullable=False, default=0)

    campaign = db.relationship('Campaign')
    creator = db.relationship('User')

    def __repr__(self):
        return f'<InviteToken campaign={self.campaign_id}>'

    @staticmethod
    def generate_token():
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)

    def is_valid(self):
        """Check if token is still valid (not used up, not expired)."""
        if self.used_at:
            return False
        if self.expires_at and self.expires_at < utcnow():
            return False
        if self.use_count >= self.max_uses:
            return False
        return True

    def use(self):
        """Mark a legacy single-use (per-user) token as used."""
        self.used_at = utcnow()
        db.session.commit()

    def record_use(self):
        """Consume one redemption of a generic multi-use link. Does not
        commit - caller saves it together with whatever else the
        redemption changed (e.g. the new CampaignMember row)."""
        self.use_count = (self.use_count or 0) + 1
        if self.use_count >= self.max_uses:
            self.used_at = utcnow()

    def serialize(self):
        return {
            'token': self.token,
            'campaign_id': self.campaign_id,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'use_count': self.use_count,
            'max_uses': self.max_uses,
            'is_valid': self.is_valid()
        }
