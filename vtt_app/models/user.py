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

    # M17: Platform Role (owner, admin, moderator, supporter)
    platform_role = db.Column(db.String(20), default='supporter', index=True)

    # M17: Profile Tier (dm, headmaster, player, listener)
    profile_tier = db.Column(db.String(20), default='player', index=True)

    # M17: Storage & Campaign Quotas
    storage_quota_gb = db.Column(db.Integer)  # 1, 5, or unlimited
    storage_used_gb = db.Column(db.Float, default=0.0)
    active_campaigns_quota = db.Column(db.Integer)  # 3, 5, or unlimited

    # M17: Account Suspension (moderation)
    is_suspended = db.Column(db.Boolean, default=False)
    suspended_at = db.Column(db.DateTime)
    suspended_reason = db.Column(db.Text)
    suspended_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # M18: Account Lifecycle (active, deactivated, marked_for_deletion, permanently_deleted, suspended)
    account_state = db.Column(db.String(20), default='active', index=True)
    deleted_at = db.Column(db.DateTime)  # When deletion was requested
    deletion_reason = db.Column(db.Text)
    deletion_requested_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    last_active_at = db.Column(db.DateTime)  # For recovery email context
    hard_deleted_at = db.Column(db.DateTime)  # When hard-deleted executed

    # Timestamps
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    sessions = db.relationship('Session', backref='user', lazy=True, cascade='all, delete-orphan')
    mfa_backup_codes = db.relationship('MFABackupCode', backref='user', lazy=True, cascade='all, delete-orphan')

    # M17: Campaign ownership (dm = owner)
    campaigns_as_dm = db.relationship('Campaign', backref='dm', lazy=True, foreign_keys='Campaign.owner_id')
    suspended_by_user = db.relationship('User', foreign_keys=[suspended_by], backref='suspended_users', remote_side=[id])

    # M18: Deletion tracking
    deletion_requested_by_user = db.relationship('User', foreign_keys=[deletion_requested_by], backref='deletions_requested', remote_side=[id])

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
            'platform_role': self.platform_role,
            'profile_tier': self.profile_tier,
            'mfa_enabled': self.mfa_enabled,
            'is_active': self.is_active,
            'is_suspended': self.is_suspended,
            'email_verified': self.email_verified,
            'storage_quota_gb': self.storage_quota_gb,
            'storage_used_gb': self.storage_used_gb,
            'active_campaigns_quota': self.active_campaigns_quota,
            'created_at': self.created_at.isoformat()
        }

    def get_storage_usage_percent(self):
        """Return storage usage as percentage (0-100)."""
        if not self.storage_quota_gb or self.storage_quota_gb == 0:
            return 0
        return min(100, (self.storage_used_gb / self.storage_quota_gb) * 100)

    def get_active_campaigns_count(self):
        """Get count of active campaigns where user is DM (owner)."""
        from vtt_app.models import Campaign
        return Campaign.query.filter_by(owner_id=self.id, status='active').count()

    def can_create_campaign(self):
        """Check if user has quota for new campaign."""
        if not self.active_campaigns_quota:
            return False
        return self.get_active_campaigns_count() < self.active_campaigns_quota

    def update_last_login(self):
        """Update last_login timestamp."""
        self.last_login = utcnow()
        db.session.commit()

    # ===== M18: Account Lifecycle Methods =====

    def is_accessible(self):
        """Check if user account is accessible (not deleted or suspended)."""
        if self.is_suspended:
            return False
        if self.account_state in ['marked_for_deletion', 'permanently_deleted']:
            return False
        return True

    def is_active_account(self):
        """Check if user has active account (not deactivated, deleted, or suspended)."""
        return self.account_state == 'active'

    def request_deletion(self, reason=None, requested_by=None):
        """Mark user account for deletion (30-day grace period)."""
        self.account_state = 'marked_for_deletion'
        self.deleted_at = utcnow()
        self.deletion_reason = reason
        self.deletion_requested_by = requested_by.id if requested_by else None
        db.session.commit()

    def cancel_deletion(self):
        """Cancel deletion request and restore account."""
        if self.account_state != 'marked_for_deletion':
            raise ValueError('Account is not marked for deletion')
        self.account_state = 'active'
        self.deleted_at = None
        self.deletion_reason = None
        self.deletion_requested_by = None
        db.session.commit()

    def deactivate(self, reason=None):
        """Deactivate account (user can reactivate)."""
        self.account_state = 'deactivated'
        db.session.commit()

    def reactivate(self):
        """Reactivate deactivated account."""
        if self.account_state != 'deactivated':
            raise ValueError('Account is not deactivated')
        self.account_state = 'active'
        db.session.commit()

    def anonymize(self):
        """Anonymize user data for hard-delete."""
        self.username = f'deleted_user_{self.id}'
        self.email = None
        self.password_hash = None
        self.mfa_secret = None
        self.mfa_enabled = False
        db.session.commit()

    def get_grace_period_end(self):
        """Get when hard-delete will be executed (30 days from deletion request)."""
        if not self.deleted_at:
            return None
        from datetime import timedelta
        return self.deleted_at + timedelta(days=30)

    def is_in_grace_period(self):
        """Check if user is still within 30-day restoration grace period."""
        if self.account_state != 'marked_for_deletion':
            return False
        from datetime import timedelta
        grace_period_end = self.deleted_at + timedelta(days=30)
        return utcnow() <= grace_period_end
