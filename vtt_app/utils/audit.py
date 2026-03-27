"""Audit logging helpers."""

from flask import request
from vtt_app.extensions import db
from vtt_app.utils.time import utcnow
from vtt_app.security import current_user


def log_audit(action, resource_type=None, resource_id=None, details=None, performed_by=None):
    """
    Log an audit event.

    Args:
        action: Event type (e.g., 'campaign_deleted', 'user_suspended', 'asset_uploaded')
        resource_type: Type of resource affected ('campaign', 'user', 'session', 'asset', etc.)
        resource_id: ID of affected resource
        details: Dict with extra context {'reason': '...', 'old_values': {...}}
        performed_by: User who performed action (default: current_user)

    Returns:
        AuditLog instance
    """
    from vtt_app.models import AuditLog

    performer = performed_by or current_user

    log = AuditLog(
        user_id=performer.id if performer and performer.is_authenticated else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=request.remote_addr if request else None,
        timestamp=utcnow(),
        performed_by_id=performer.id if (performed_by and performed_by != current_user) else None
    )

    db.session.add(log)
    db.session.commit()

    return log


def log_campaign_deleted(campaign, deleted_by=None, reason=None):
    """Log campaign deletion."""
    return log_audit(
        action='campaign_deleted',
        resource_type='campaign',
        resource_id=campaign.id,
        details={
            'campaign_name': campaign.name,
            'reason': reason
        },
        performed_by=deleted_by
    )


def log_campaign_created(campaign, created_by=None):
    """Log campaign creation."""
    return log_audit(
        action='campaign_created',
        resource_type='campaign',
        resource_id=campaign.id,
        details={'campaign_name': campaign.name},
        performed_by=created_by
    )


def log_user_suspended(target_user, suspended_by=None, reason=None):
    """Log user suspension."""
    return log_audit(
        action='user_suspended',
        resource_type='user',
        resource_id=target_user.id,
        details={
            'username': target_user.username,
            'reason': reason
        },
        performed_by=suspended_by
    )


def log_user_unsuspended(target_user, unsuspended_by=None):
    """Log user un-suspension."""
    return log_audit(
        action='user_unsuspended',
        resource_type='user',
        resource_id=target_user.id,
        details={'username': target_user.username},
        performed_by=unsuspended_by
    )


def log_asset_uploaded(asset_id, user, file_name, size_mb):
    """Log asset upload."""
    return log_audit(
        action='asset_uploaded',
        resource_type='asset',
        resource_id=asset_id,
        details={
            'filename': file_name,
            'size_mb': size_mb
        },
        performed_by=user
    )


def log_quota_exceeded(user, resource_type, limit_type, current, limit):
    """Log quota violation attempt."""
    return log_audit(
        action='quota_exceeded',
        resource_type=resource_type,
        resource_id=user.id,
        details={
            'limit_type': limit_type,  # 'storage_gb', 'active_campaigns'
            'current': current,
            'limit': limit
        },
        performed_by=user
    )


def log_permission_changed(user, old_role, new_role, changed_by=None):
    """Log permission/role change."""
    return log_audit(
        action='permission_changed',
        resource_type='user',
        resource_id=user.id,
        details={
            'username': user.username,
            'old_role': old_role,
            'new_role': new_role
        },
        performed_by=changed_by
    )


def get_audit_logs(resource_type=None, resource_id=None, action=None, limit=100):
    """Query audit logs with optional filters."""
    from vtt_app.models import AuditLog

    query = AuditLog.query

    if resource_type:
        query = query.filter_by(resource_type=resource_type)

    if resource_id:
        query = query.filter_by(resource_id=resource_id)

    if action:
        query = query.filter_by(action=action)

    return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
