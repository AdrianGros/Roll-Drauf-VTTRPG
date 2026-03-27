"""M30: Admin console endpoints (read-only metrics + user management)."""

from flask import Blueprint, request, jsonify
from vtt_app.security import current_user
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from vtt_app.extensions import db
from vtt_app.models import User, Campaign, Asset, GameSession, AuditLog
from vtt_app.permissions import has_platform_role

admin_dashboard_bp = Blueprint('admin_dashboard', __name__, url_prefix='/api/admin')


@admin_dashboard_bp.route('/dashboard/metrics', methods=['GET'])
@has_platform_role('admin', 'moderator')
def get_dashboard_metrics():
    """Get platform overview metrics."""
    total_storage = db.session.query(func.sum(Asset.size_bytes)).scalar() or 0

    return jsonify({
        'metrics': {
            'total_users': User.query.count(),
            'active_users': User.query.filter_by(account_state='active').count(),
            'suspended_users': User.query.filter_by(is_suspended=True).count(),
            'deleted_users': User.query.filter_by(account_state='marked_for_deletion').count(),
            'total_campaigns': Campaign.query.count(),
            'active_campaigns': Campaign.query.filter_by(status='active').count(),
            'total_assets': Asset.query.count(),
            'total_storage_gb': total_storage / 1024 / 1024 / 1024,
            'active_sessions': GameSession.query.filter_by(status='active').count(),
            'audit_logs': AuditLog.query.count(),
        }
    }), 200


@admin_dashboard_bp.route('/users/search', methods=['GET'])
@has_platform_role('admin', 'moderator')
def search_users():
    """Search users by username or email."""
    q = request.args.get('q', '')
    limit = request.args.get('limit', 20, type=int)

    users = User.query.filter(
        (User.username.ilike(f'%{q}%')) |
        (User.email.ilike(f'%{q}%'))
    ).limit(limit).all()

    return jsonify({
        'users': [u.serialize(include_email=True) for u in users],
        'count': len(users)
    }), 200


@admin_dashboard_bp.route('/campaigns/search', methods=['GET'])
@has_platform_role('admin', 'moderator')
def search_campaigns():
    """Search campaigns by name or owner."""
    q = request.args.get('q', '')
    limit = request.args.get('limit', 20, type=int)

    campaigns = Campaign.query.filter(
        Campaign.name.ilike(f'%{q}%')
    ).limit(limit).all()

    return jsonify({
        'campaigns': [c.serialize() for c in campaigns],
        'count': len(campaigns)
    }), 200


@admin_dashboard_bp.route('/audit-logs', methods=['GET'])
@has_platform_role('admin', 'moderator')
def get_audit_logs():
    """Get recent audit logs."""
    limit = request.args.get('limit', 100, type=int)
    action_filter = request.args.get('action')

    query = AuditLog.query.order_by(AuditLog.timestamp.desc())

    if action_filter:
        query = query.filter_by(action=action_filter)

    logs = query.limit(limit).all()

    return jsonify({
        'logs': [log.serialize() for log in logs],
        'count': len(logs)
    }), 200


@admin_dashboard_bp.route('/storage/top-users', methods=['GET'])
@has_platform_role('admin', 'moderator')
def get_top_storage_users():
    """Get users with highest storage usage."""
    limit = request.args.get('limit', 10, type=int)

    users = User.query.order_by(User.storage_used_gb.desc()).limit(limit).all()

    return jsonify({
        'users': [
            {
                'user_id': u.id,
                'username': u.username,
                'storage_gb': u.storage_used_gb,
                'quota_gb': u.storage_quota_gb,
                'usage_percent': u.get_storage_usage_percent(),
            }
            for u in users
        ]
    }), 200
