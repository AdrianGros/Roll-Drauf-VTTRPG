"""M18: User profile endpoints (deletion, deactivation, restoration)."""

from flask import Blueprint, request, jsonify
from vtt_app.security import current_user
from flask_jwt_extended import jwt_required
from vtt_app.extensions import db
from vtt_app.models import User
from vtt_app.permissions import has_platform_role
from vtt_app.utils.user_deletion import (
    request_user_deletion, cancel_user_deletion, transfer_user_campaigns_to_admin
)
from vtt_app.utils.audit import log_audit

profile_m18_bp = Blueprint('profile_m18', __name__, url_prefix='/api/profile')


@profile_m18_bp.route('/request-deletion', methods=['POST'])
@jwt_required()
def request_deletion():
    """
    Request account deletion (30-day grace period).

    Body:
    {
      "reason": "string (optional)",
      "password": "string (required for verification)"
    }
    """
    data = request.get_json()

    # Require password confirmation
    password = data.get('password')
    if not password or not current_user.check_password(password):
        return jsonify({'error': 'Invalid password'}), 401

    # Check if already deleted or suspended
    if current_user.account_state in ['marked_for_deletion', 'permanently_deleted']:
        return jsonify({'error': 'Account already marked for deletion'}), 400

    if current_user.is_suspended:
        return jsonify({'error': 'Account is suspended'}), 400

    # Request deletion
    reason = data.get('reason', 'User requested deletion')
    request_user_deletion(current_user, reason=reason, requested_by=None)

    return jsonify({
        'status': 'deletion_requested',
        'message': 'Your account will be permanently deleted in 30 days.',
        'grace_period_end': current_user.get_grace_period_end().isoformat(),
        'can_cancel_until': current_user.get_grace_period_end().isoformat()
    }), 200


@profile_m18_bp.route('/cancel-deletion', methods=['POST'])
@jwt_required()
def cancel_deletion():
    """Cancel account deletion request and restore account."""
    if current_user.account_state != 'marked_for_deletion':
        return jsonify({'error': 'Account not marked for deletion'}), 400

    if not current_user.is_in_grace_period():
        return jsonify({
            'error': 'Grace period expired. Account cannot be restored.'
        }), 400

    # Cancel deletion
    cancel_user_deletion(current_user)

    return jsonify({
        'status': 'deletion_cancelled',
        'account_state': current_user.account_state,
        'message': 'Your account has been restored.'
    }), 200


@profile_m18_bp.route('/deactivate', methods=['POST'])
@jwt_required()
def deactivate_account():
    """
    Deactivate account (user can reactivate anytime).

    Body:
    {
      "reason": "string (optional)"
    }
    """
    data = request.get_json() or {}

    if current_user.account_state == 'deactivated':
        return jsonify({'error': 'Account already deactivated'}), 400

    reason = data.get('reason')
    current_user.deactivate(reason=reason)

    log_audit(
        action='account_deactivated',
        resource_type='user',
        resource_id=current_user.id,
        details={'reason': reason},
        performed_by=current_user
    )

    return jsonify({
        'status': 'deactivated',
        'message': 'Your account has been paused. You can reactivate anytime.',
        'account_state': current_user.account_state
    }), 200


@profile_m18_bp.route('/reactivate', methods=['POST'])
@jwt_required()
def reactivate_account():
    """Reactivate a deactivated account."""
    if current_user.account_state != 'deactivated':
        return jsonify({'error': 'Account is not deactivated'}), 400

    current_user.reactivate()

    log_audit(
        action='account_reactivated',
        resource_type='user',
        resource_id=current_user.id,
        performed_by=current_user
    )

    return jsonify({
        'status': 'active',
        'message': 'Welcome back! Your account is active again.',
        'account_state': current_user.account_state
    }), 200


@profile_m18_bp.route('/status', methods=['GET'])
@jwt_required()
def get_account_status():
    """Get current account status and lifecycle info."""
    return jsonify({
        'user_id': current_user.id,
        'username': current_user.username,
        'account_state': current_user.account_state,
        'is_accessible': current_user.is_accessible(),
        'is_active': current_user.is_active_account(),
        'is_suspended': current_user.is_suspended,
        'suspended_reason': current_user.suspended_reason,
        'deletion_info': {
            'deleted_at': current_user.deleted_at.isoformat() if current_user.deleted_at else None,
            'deletion_reason': current_user.deletion_reason,
            'grace_period_end': current_user.get_grace_period_end().isoformat() if current_user.get_grace_period_end() else None,
            'in_grace_period': current_user.is_in_grace_period(),
            'can_restore': current_user.is_in_grace_period()
        }
    }), 200


# ===== ADMIN ENDPOINTS =====

admin_m18_bp = Blueprint('admin_m18', __name__, url_prefix='/api/admin')


@admin_m18_bp.route('/users', methods=['GET'])
@has_platform_role('admin', 'moderator')
def list_users():
    """
    List users with optional filtering.

    Query params:
      state: active, deactivated, marked_for_deletion, permanently_deleted, suspended
      page: int (default 1)
      limit: int (default 20)
    """
    state = request.args.get('state')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)

    query = User.query

    if state:
        query = query.filter_by(account_state=state)

    total = query.count()
    users = query.offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        'users': [u.serialize(include_email=True) for u in users],
        'page': page,
        'limit': limit,
        'total': total
    }), 200


@admin_m18_bp.route('/users/<int:user_id>/restore', methods=['POST'])
@has_platform_role('admin', 'moderator')
def restore_user(user_id):
    """Restore a user marked for deletion."""
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.account_state != 'marked_for_deletion':
        return jsonify({'error': 'User is not marked for deletion'}), 400

    if not user.is_in_grace_period():
        return jsonify({'error': 'Grace period expired. User cannot be restored.'}), 400

    # Restore
    cancel_user_deletion(user, admin=current_user)

    return jsonify({
        'status': 'restored',
        'user_id': user.id,
        'account_state': user.account_state
    }), 200


@admin_m18_bp.route('/users/<int:user_id>/force-delete', methods=['POST'])
@has_platform_role('admin')
def force_delete_user(user_id):
    """Force hard-delete a user (admin only, final action)."""
    data = request.get_json() or {}

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.account_state == 'permanently_deleted':
        return jsonify({'error': 'User already permanently deleted'}), 400

    # Get admin user for campaigns transfer
    admin_user = User.query.filter_by(platform_role='admin').first()

    try:
        # Transfer campaigns to admin
        transferred = transfer_user_campaigns_to_admin(user, admin_user)

        # Hard-delete user
        from vtt_app.utils.user_deletion import hard_delete_user
        hard_delete_user(user, admin=current_user)

        return jsonify({
            'status': 'permanently_deleted',
            'user_id': user.id,
            'campaigns_transferred': len(transferred),
            'message': 'User has been permanently deleted.'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_m18_bp.route('/campaigns/<int:campaign_id>/reassign-owner', methods=['POST'])
@has_platform_role('admin', 'moderator')
def reassign_campaign_owner(campaign_id):
    """Reassign campaign ownership (when original owner deleted)."""
    from vtt_app.models import Campaign

    data = request.get_json()
    new_owner_id = data.get('new_owner_id')

    if not new_owner_id:
        return jsonify({'error': 'new_owner_id required'}), 400

    campaign = Campaign.query.get(campaign_id)
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), 404

    new_owner = User.query.get(new_owner_id)
    if not new_owner:
        return jsonify({'error': 'New owner not found'}), 404

    old_owner_id = campaign.owner_id
    campaign.owner_id = new_owner_id
    db.session.commit()

    # Log
    log_audit(
        action='campaign_ownership_reassigned',
        resource_type='campaign',
        resource_id=campaign.id,
        details={
            'from_user_id': old_owner_id,
            'to_user_id': new_owner_id,
            'reason': data.get('reason', 'Admin reassignment')
        },
        performed_by=current_user
    )

    return jsonify({
        'campaign_id': campaign.id,
        'new_owner_id': new_owner_id,
        'message': 'Campaign ownership reassigned.'
    }), 200
