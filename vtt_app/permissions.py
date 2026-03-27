"""
Central permission system for Roll-Drauf VTT.

All authorization logic in one place — no scattered guards.
This is the single source of truth for who can do what.
"""

from functools import wraps
from flask import abort, request, jsonify
from flask_jwt_extended import get_jwt_identity
from vtt_app.models import Campaign, User
from vtt_app.config import PLATFORM_ROLES, PROFILE_TIERS
from vtt_app.security import current_user


# ============= PLATFORM ROLE CHECKS =============

def has_platform_role(*required_roles):
    """
    Decorator: Check if user has one of the required platform roles.

    Usage:
        @has_platform_role('admin')
        @has_platform_role('moderator', 'admin')  # OR logic
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user or not current_user.is_authenticated:
                abort(401)

            if current_user.platform_role not in required_roles:
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def has_platform_role_level(min_level):
    """
    Decorator: Check platform role hierarchy level.

    Levels: owner=100, admin=80, moderator=60, supporter=40
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user or not current_user.is_authenticated:
                abort(401)

            current_level = PLATFORM_ROLES.get(current_user.platform_role, {}).get('level', 0)

            if current_level < min_level:
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============= CAMPAIGN-LEVEL PERMISSIONS =============

def can_view_campaign(user, campaign):
    """
    Check if user can view campaign (read-only).

    Rules:
    - Platform supporter+: All campaigns
    - DM/Headmaster: Own campaigns + joined campaigns
    - Player: Only joined campaigns
    """
    if not user:
        return False

    # Suspended users can't view anything
    if user.is_suspended:
        return False

    # Platform support+ can see all
    if user.platform_role in ['supporter', 'moderator', 'admin', 'owner']:
        return True

    # DM/Headmaster see own campaigns
    if campaign.dm_id == user.id:
        return True

    # Campaign members can see their campaign
    member = campaign.get_member(user.id) if hasattr(campaign, 'get_member') else None
    return member and member.is_active()


def can_edit_campaign(user, campaign):
    """
    Check if user can edit campaign (maps, details, settings).

    Rules:
    - Platform mods+: All campaigns
    - DM/Headmaster who owns it: Own campaign
    - CO_DM: Co-edit capability
    """
    if not user or user.is_suspended:
        return False

    # Platform staff edit all
    if user.platform_role in ['moderator', 'admin', 'owner']:
        return True

    # Only DM who created
    if campaign.dm_id == user.id:
        return True

    # CO_DM can edit
    member = campaign.get_member(user.id) if hasattr(campaign, 'get_member') else None
    return member and member.is_co_dm()


def can_delete_campaign(user, campaign):
    """
    Check if user can delete campaign.

    Rules:
    - Only DM who created it + mods/admins can delete
    """
    if not user or user.is_suspended:
        return False

    # Platform staff can delete any
    if user.platform_role in ['moderator', 'admin', 'owner']:
        return True

    # DM who created it can delete
    return campaign.dm_id == user.id


def can_create_campaign(user):
    """
    Check if user can create a campaign.

    Rules:
    - Only DM, Headmaster, and platform staff
    - Must have quota available
    """
    if not user or not user.is_authenticated or user.is_suspended:
        return False

    # Only content creators
    if user.profile_tier not in ['dm', 'headmaster']:
        if user.platform_role not in ['admin', 'owner']:
            return False

    # Check quota
    return user.can_create_campaign()


def can_view_all_campaigns(user):
    """Check if user can see all campaigns (team dashboard)."""
    if not user or not user.is_authenticated:
        return False

    return user.platform_role in ['supporter', 'moderator', 'admin', 'owner']


# ============= USER-LEVEL PERMISSIONS =============

def can_suspend_user(user, target_user):
    """
    Check if user can suspend another user.

    Rules:
    - Only mods+ can suspend
    - Can't suspend self
    - Can't suspend higher-level users
    """
    if not user or not user.is_authenticated:
        return False

    # Only mods+ can suspend
    if user.platform_role not in ['moderator', 'admin', 'owner']:
        return False

    # Can't suspend self
    if user.id == target_user.id:
        return False

    return True


def can_delete_user(user, target_user):
    """Check if user can delete/anonymize another user (admin+ only)."""
    if not user or not user.is_authenticated:
        return False

    if user.platform_role not in ['admin', 'owner']:
        return False

    if user.id == target_user.id:
        return False

    return True


# ============= QUOTA CHECKS =============

def can_upload_asset(user, size_mb):
    """
    Check if user can upload asset (storage quota check).

    Returns:
        (allowed: bool, message: str)
    """
    if not user:
        return False, "Not authenticated"

    if user.is_suspended:
        return False, "Account suspended"

    # Platform staff unlimited
    if user.platform_role in ['admin', 'owner']:
        return True, "Platform staff unlimited"

    # Check quota
    if not user.storage_quota_gb:
        return False, "No storage quota"

    available = user.storage_quota_gb - user.storage_used_gb
    required = size_mb / 1024  # Convert MB to GB

    if required > available:
        return False, f"Storage quota exceeded. Available: {available:.2f}GB, Required: {required:.2f}GB"

    return True, "OK"


# ============= DECORATORS FOR ROUTES =============

def require_campaign_access(permission_fn):
    """
    Decorator: Validate campaign access before executing route.

    Usage:
        @require_campaign_access(can_delete_campaign)
        def delete_campaign(campaign_id):
            campaign = Campaign.query.get(campaign_id)
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            campaign_id = kwargs.get('campaign_id') or request.view_args.get('campaign_id')
            campaign = Campaign.query.get(campaign_id) if campaign_id else None

            if not campaign:
                abort(404)

            if not permission_fn(current_user, campaign):
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_quota(resource_type='storage', size_param='size'):
    """
    Decorator: Check quota before operation.

    Usage:
        @require_quota('storage', size_param='file_size')
        def upload_asset():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            size_mb = request.args.get(size_param, 0, type=float)

            if resource_type == 'storage':
                allowed, msg = can_upload_asset(current_user, size_mb)
                if not allowed:
                    return jsonify({'error': msg}), 413  # Payload Too Large

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============= SUMMARY HELPERS =============

def get_user_permissions_summary(user):
    """Get a summary of what this user can do."""
    if not user:
        return {}

    return {
        'can_view_all_campaigns': can_view_all_campaigns(user),
        'can_create_campaign': can_create_campaign(user),
        'can_suspend_users': user.platform_role in ['moderator', 'admin', 'owner'],
        'can_delete_users': user.platform_role in ['admin', 'owner'],
        'storage_usage_percent': user.get_storage_usage_percent(),
        'active_campaigns_count': user.get_active_campaigns_count(),
        'can_create_more_campaigns': user.can_create_campaign(),
        'is_suspended': user.is_suspended,
        'platform_role': user.platform_role,
        'profile_tier': user.profile_tier,
    }
