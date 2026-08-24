"""Single-use password recovery tokens."""

from vtt.extensions import db
from vtt.utils.time import utcnow


class PasswordResetToken(db.Model):
    """Hashed, expiring password-reset verifier bound to one account."""

    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used_at = db.Column(db.DateTime, index=True)
    requested_ip = db.Column(db.String(45))
    consumed_ip = db.Column(db.String(45))

    user = db.relationship("User", backref=db.backref(
        "password_reset_tokens", lazy=True, cascade="all, delete-orphan"
    ))

    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > utcnow()
