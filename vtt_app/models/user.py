"""
User model with authentication and MFA support.
"""

import pyotp
from flask_bcrypt import generate_password_hash, check_password_hash
from vtt_app.extensions import db
from vtt_app.utils.time import utcnow


class User(db.Model):
    """User entity with password hashing, MFA, and session tracking."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), default=1, nullable=False)
    
    # MFA fields
    mfa_secret = db.Column(db.String(32))
    mfa_enabled = db.Column(db.Boolean, default=False)

    # Account status
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    email_verified_at = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    sessions = db.relationship('Session', backref='user', lazy=True, cascade='all, delete-orphan')
    mfa_backup_codes = db.relationship('MFABackupCode', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password: str) -> None:
        """Hash and store password using bcrypt."""
        self.password_hash = generate_password_hash(password, rounds=12).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """Verify password against hash."""
        return check_password_hash(self.password_hash.encode('utf-8'), password)

    def get_mfa_totp(self):
        """Return TOTP object for MFA verification."""
        if self.mfa_secret:
            return pyotp.TOTP(self.mfa_secret)
        return None

    def generate_mfa_secret(self) -> str:
        """Generate new TOTP secret (base32)."""
        self.mfa_secret = pyotp.random_base32()
        return self.mfa_secret

    def get_provisioning_uri(self) -> str:
        """Get provisioning URI for QR code (Google Authenticator, Authy, etc)."""
        if not self.mfa_secret:
            self.generate_mfa_secret()
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.provisioning_uri(
            name=self.email,
            issuer_name='roll drauf vtt'
        )

    def verify_mfa_code(self, otp: str) -> bool:
        """Verify TOTP code against current time window."""
        if not self.mfa_secret:
            return False
        totp = self.get_mfa_totp()
        return totp.verify(otp, valid_window=1)  # Allow 30s window

    def serialize(self, include_email=False):
        """Return JSON-safe dictionary for API responses."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email if include_email else None,
            'role': self.role.name,
            'mfa_enabled': self.mfa_enabled,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat()
        }

    def update_last_login(self):
        """Update last_login timestamp."""
        self.last_login = utcnow()
        db.session.commit()
