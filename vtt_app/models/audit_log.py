"""Audit logging model for permission/ownership tracking."""

from vtt_app.extensions import db
from vtt_app.utils.time import utcnow


class AuditLog(db.Model):
    """Platform audit trail for permission/ownership changes."""

    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    # campaign_delete, user_suspend, asset_upload, quota_exceeded, etc.

    resource_type = db.Column(db.String(50), index=True)  # campaign, user, session, asset
    resource_id = db.Column(db.Integer, index=True)

    details = db.Column(db.JSON)  # {reason, old_values, context}
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    # Who performed the action (if different from user_id)
    performed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='audit_logs_as_subject')
    performed_by = db.relationship('User', foreign_keys=[performed_by_id], backref='audit_logs_performed')

    __table_args__ = (
        db.Index('idx_audit_resource', 'resource_type', 'resource_id'),
        db.Index('idx_audit_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f'<AuditLog action={self.action} resource={self.resource_type}#{self.resource_id}>'

    def serialize(self):
        """Return JSON-safe dict."""
        return {
            'id': self.id,
            'action': self.action,
            'resource': f"{self.resource_type}#{self.resource_id}" if self.resource_type else None,
            'timestamp': self.timestamp.isoformat(),
            'performed_by': self.performed_by.username if self.performed_by else self.user.username,
            'details': self.details
        }
