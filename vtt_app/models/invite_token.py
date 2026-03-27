"""Invite token model for campaign invitations."""

from datetime import timedelta
import secrets
from vtt_app.extensions import db
from vtt_app.utils.time import utcnow


class InviteToken(db.Model):
    """Campaign invitation token (shareable link)."""

    __tablename__ = 'invite_tokens'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    
    invited_user_email = db.Column(db.String(120))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: utcnow() + timedelta(days=7))
    used_at = db.Column(db.DateTime)

    campaign = db.relationship('Campaign')
    creator = db.relationship('User')

    def __repr__(self):
        return f'<InviteToken campaign={self.campaign_id}>'

    @staticmethod
    def generate_token():
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)

    def is_valid(self):
        """Check if token is still valid (not used, not expired)."""
        if self.used_at:
            return False
        if self.expires_at and self.expires_at < utcnow():
            return False
        return True

    def use(self):
        """Mark token as used."""
        self.used_at = utcnow()
        db.session.commit()

    def serialize(self):
        return {
            'token': self.token,
            'campaign_id': self.campaign_id,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_valid': self.is_valid()
        }
