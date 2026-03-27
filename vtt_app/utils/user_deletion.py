"""M18: User deletion and lifecycle management utilities."""

from datetime import datetime, timedelta
from vtt_app.extensions import db
from vtt_app.models import User, Campaign
from vtt_app.utils.time import utcnow
from vtt_app.utils.audit import log_audit


def request_user_deletion(user, reason=None, requested_by=None):
    """
    Request user account deletion (30-day grace period).

    Args:
        user: User object to delete
        reason: Deletion reason (optional)
        requested_by: Admin user requesting deletion (optional)

    Returns:
        User object with account_state = 'marked_for_deletion'
    """
    user.request_deletion(reason=reason, requested_by=requested_by)

    # Log
    log_audit(
        action='user_deletion_requested',
        resource_type='user',
        resource_id=user.id,
        details={
            'reason': reason,
            'grace_period_end': user.get_grace_period_end().isoformat() if user.get_grace_period_end() else None
        },
        performed_by=requested_by
    )

    return user


def cancel_user_deletion(user, admin=None):
    """
    Cancel user deletion request and restore account.

    Args:
        user: User to restore
        admin: Admin who cancelled deletion (optional)

    Returns:
        Restored User object
    """
    user.cancel_deletion()

    log_audit(
        action='user_deletion_cancelled',
        resource_type='user',
        resource_id=user.id,
        details={'restored_by': admin.username if admin else 'system'},
        performed_by=admin
    )

    return user


def transfer_user_campaigns_to_admin(user, admin_user):
    """
    Transfer all campaigns owned by deleted user to admin.

    Args:
        user: Deleted user
        admin_user: Admin to receive campaigns

    Returns:
        List of transferred campaign IDs
    """
    campaigns = Campaign.query.filter_by(owner_id=user.id).all()
    transferred_ids = []

    for campaign in campaigns:
        old_owner = campaign.owner_id
        campaign.owner_id = admin_user.id
        campaign.status = 'archived' if campaign.status == 'active' else campaign.status
        db.session.add(campaign)
        transferred_ids.append(campaign.id)

        # Log transfer
        log_audit(
            action='campaign_ownership_transferred',
            resource_type='campaign',
            resource_id=campaign.id,
            details={
                'from_user_id': old_owner,
                'to_user_id': admin_user.id,
                'reason': 'user_deletion'
            },
            performed_by=admin_user
        )

    db.session.commit()
    return transferred_ids


def hard_delete_user(user, admin=None):
    """
    Perform hard-delete on user: anonymize and mark as permanently deleted.

    Args:
        user: User to hard-delete
        admin: Admin performing deletion (optional)

    Returns:
        Deleted User object
    """
    # Anonymize
    user.anonymize()

    # Mark as permanently deleted
    user.account_state = 'permanently_deleted'
    user.hard_deleted_at = utcnow()
    db.session.commit()

    # Log
    log_audit(
        action='user_permanently_deleted',
        resource_type='user',
        resource_id=user.id,
        details={
            'reason': 'grace_period_expired',
            'anonymized': True,
            'hard_deleted_at': user.hard_deleted_at.isoformat()
        },
        performed_by=admin
    )

    return user


def delete_marked_users_after_grace_period(admin_user=None):
    """
    Hard-delete all users marked for deletion > 30 days ago.

    Scheduled job (runs daily at 2am).

    Args:
        admin_user: System admin for logging (optional)

    Returns:
        dict with deleted_count, errors
    """
    cutoff = utcnow() - timedelta(days=30)

    # Find all users to hard-delete
    users_to_delete = User.query.filter(
        User.account_state == 'marked_for_deletion',
        User.deleted_at < cutoff
    ).all()

    deleted_count = 0
    errors = []

    for user in users_to_delete:
        try:
            hard_delete_user(user, admin=admin_user)
            deleted_count += 1
        except Exception as e:
            errors.append({
                'user_id': user.id,
                'error': str(e)
            })

    return {
        'deleted_count': deleted_count,
        'errors': errors,
        'timestamp': utcnow().isoformat()
    }


def get_users_in_grace_period():
    """
    Get all users currently in deletion grace period (marked for deletion, within 30d).

    Returns:
        List of User objects
    """
    cutoff = utcnow() - timedelta(days=30)

    return User.query.filter(
        User.account_state == 'marked_for_deletion',
        User.deleted_at >= cutoff
    ).all()


def get_users_past_grace_period():
    """
    Get all users past grace period (should be hard-deleted soon).

    Returns:
        List of User objects
    """
    cutoff = utcnow() - timedelta(days=30)

    return User.query.filter(
        User.account_state == 'marked_for_deletion',
        User.deleted_at < cutoff
    ).all()
