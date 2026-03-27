"""
Session model for audit trail and JWT token revocation.
"""

from vtt_app.extensions import db
from vtt_app.utils.time import utcnow


class Session(db.Model):
    """Session tracking for audit trail and logout/revocation."""

    __tablename__ = 'sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    token_jti = db.Column(db.String(255), unique=True)  # JWT ID for revocation
    
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    revoked_at = db.Column(db.DateTime)  # NULL = active, set = revoked (logout)

    ip_address = db.Column(db.String(45))  # IPv6 support
    user_agent = db.Column(db.Text)

    def __repr__(self):
        return f'<Session user_id={self.user_id}>'

    def is_active(self) -> bool:
        """Check if session is still active (not revoked, not expired)."""
        return self.revoked_at is None and self.expires_at > utcnow()

    def revoke(self):
        """Revoke this session (logout)."""
        self.revoked_at = utcnow()
        db.session.commit()

    def serialize(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'ip_address': self.ip_address,
            'is_active': self.is_active()
        }
