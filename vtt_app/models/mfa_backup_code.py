"""
MFA Backup Code model for account recovery.
"""

from flask_bcrypt import generate_password_hash, check_password_hash
from vtt_app.extensions import db
from vtt_app.utils.time import utcnow


class MFABackupCode(db.Model):
    """Single-use backup codes for MFA recovery."""

    __tablename__ = 'mfa_backup_codes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)
    
    used_at = db.Column(db.DateTime)  # NULL = unused
    created_at = db.Column(db.DateTime, default=utcnow)

    def __repr__(self):
        return f'<MFABackupCode user_id={self.user_id}>'

    @staticmethod
    def hash_code(code: str) -> str:
        """Hash a backup code for storage."""
        return generate_password_hash(code).decode('utf-8')

    def verify_code(self, code: str) -> bool:
        """Verify code against hash."""
        return check_password_hash(self.code_hash.encode('utf-8'), code)

    def is_unused(self) -> bool:
        """Check if code has not been used."""
        return self.used_at is None

    def use_code(self):
        """Mark code as used."""
        self.used_at = utcnow()
        db.session.commit()
