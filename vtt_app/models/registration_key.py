"""Registration key model for multi-tier account provisioning."""

from vtt_app.extensions import db
from vtt_app.utils.time import utcnow


class RegistrationKey(db.Model):
    """Registration key for bulk user provisioning and tier assignment."""

    __tablename__ = 'registration_keys'

    id = db.Column(db.Integer, primary_key=True)
    key_code = db.Column(db.String(23), unique=True, nullable=False, index=True)  # SPELL-XXXX-XXXX-XXXX
    key_name = db.Column(db.String(255), nullable=False)
    key_batch_id = db.Column(db.String(50), nullable=False, index=True)

    # Tier: free, player, dm, headmaster
    tier = db.Column(db.String(20), default='player', nullable=False, index=True)

    # Usage tracking
    max_uses = db.Column(db.Integer, default=1, nullable=False)
    uses_remaining = db.Column(db.Integer, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    used_at = db.Column(db.DateTime, index=True)  # When key was consumed
    expires_at = db.Column(db.DateTime, index=True)  # Optional expiration

    # User who consumed the key
    used_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)

    # Soft delete via revocation (never hard delete)
    is_revoked = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # Relationships
    used_by = db.relationship('User', backref='registration_keys_used', lazy=True, foreign_keys=[used_by_id])

    __table_args__ = (
        db.Index('idx_registration_keys_batch_id', 'key_batch_id'),
        db.Index('idx_registration_keys_tier', 'tier'),
        db.Index('idx_registration_keys_is_revoked', 'is_revoked'),
        db.Index('idx_registration_keys_used_at', 'used_at'),
    )

    def __repr__(self):
        return f'<RegistrationKey {self.key_code} tier={self.tier}>'

    def is_valid(self) -> bool:
        """
        Check if key is valid for registration.

        Returns:
            bool: True if key can be used, False otherwise.
        """
        # Must not be revoked
        if self.is_revoked:
            return False

        # Must have uses remaining
        if self.uses_remaining <= 0:
            return False

        # Must not be expired
        if self.expires_at and utcnow() > self.expires_at:
            return False

        return True

    def consume(self, user_id: int) -> bool:
        """
        Consume one use of the key (register a user with it).

        Args:
            user_id: ID of user consuming the key

        Returns:
            bool: True if consumption succeeded, False if key invalid
        """
        if not self.is_valid():
            return False

        self.uses_remaining -= 1
        self.used_at = utcnow()
        self.used_by_id = user_id

        db.session.commit()
        return True

    def revoke(self) -> None:
        """Revoke the key (soft delete via flag)."""
        self.is_revoked = True
        db.session.commit()

    def serialize(self) -> dict:
        """Return JSON-safe dictionary."""
        return {
            'id': self.id,
            'key_code': self.key_code,
            'key_name': self.key_name,
            'key_batch_id': self.key_batch_id,
            'tier': self.tier,
            'max_uses': self.max_uses,
            'uses_remaining': self.uses_remaining,
            'created_at': self.created_at.isoformat(),
            'used_at': self.used_at.isoformat() if self.used_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'used_by_id': self.used_by_id,
            'is_revoked': self.is_revoked,
        }
