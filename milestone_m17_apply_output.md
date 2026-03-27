# M17 Apply Phase: Tenant, Ownership, Permission Architecture

**Status**: Design-Ready for Implementation
**Date**: 2026-03-27
**Scope**: Central permission system, multi-tier platform roles, quota model, audit logging

---

## 1. Platform Role Hierarchy

```
Owner (1)
├─ Admin (n)
│  ├─ Moderator (n)
│  │  └─ Supporter (n)
│  │     └─ [Campaign Roles Below]
│  └─ [Campaign Roles Below]
│
└─ Headmaster (DM++) — profile_tier='headmaster'
   ├─ Quotas: 5 campaigns active, 5GB storage
   ├─ Permissions: Full DM ops + suspend users
   └─ [Campaign Roles Below]

└─ Dungeonmaster (DM) — profile_tier='dm'
   ├─ Quotas: 3 campaigns active, 1GB storage
   ├─ Permissions: Create/manage own campaigns
   └─ [Campaign Roles Below]

Player — profile_tier='player'
└─ Can join campaigns, read-only assets

Listener/Zuhörer — profile_tier='listener'
└─ Can observe live sessions only
```

### Role Attributes Table

| Role | Platform-Level | Can See All Campaigns | Can Create Campaign | Can Delete Any Campaign | Can Suspend User | Storage | Active Campaigns |
|------|---|---|---|---|---|---|---|
| Owner | Yes | Yes | Yes | Yes | Yes | Unlimited | Unlimited |
| Admin | Yes | Yes | Yes | Yes | Yes | Unlimited | Unlimited |
| Moderator | Yes | Yes | No | Yes (any) | Yes | Unlimited | Unlimited |
| Supporter | Yes | Yes | No | No | No | Unlimited | Unlimited |
| Headmaster | No | No | Yes | Own + Mod | No | 5GB | 5 |
| Dungeonmaster | No | No | Yes | Own + Mod | No | 1GB | 3 |
| Player | No | No | No | No | No | — | — |
| Listener | No | No | No | No | No | — | — |

---

## 2. Data Model Extensions

### 2.1 User Model (Extended)

```python
class User(db.Model):
    # Existing fields
    id, username, email, password_hash, role_id
    is_active, email_verified, mfa_enabled, mfa_secret
    created_at, updated_at

    # NEW: Platform tier
    platform_role = db.Column(db.String(20), default='supporter')
    # owner, admin, moderator, supporter (null for DM/Player)

    # NEW: Profile tier (content creator level)
    profile_tier = db.Column(db.String(20), default='player')
    # dm, headmaster, player, listener

    # NEW: Quotas
    storage_quota_gb = db.Column(db.Integer)  # 1, 5, or unlimited
    storage_used_gb = db.Column(db.Float, default=0.0)
    active_campaigns_quota = db.Column(db.Integer)  # 3, 5, or unlimited

    # NEW: Account status
    is_suspended = db.Column(db.Boolean, default=False)
    suspended_at = db.Column(db.DateTime)
    suspended_reason = db.Column(db.Text)
    suspended_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    campaigns_as_dm = db.relationship('Campaign', backref='dm', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)
```

### 2.2 New: AuditLog Model

```python
class AuditLog(db.Model):
    """Platform audit trail for permission/ownership changes."""

    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # 'campaign_delete', 'user_suspend', etc.
    resource_type = db.Column(db.String(50))  # 'campaign', 'user', 'session'
    resource_id = db.Column(db.Integer)  # campaign_id, user_id, etc.
    details = db.Column(db.JSON)  # Extra context (reason, old_values, etc.)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=utcnow, index=True)

    # Who performed the action (admin/mod who suspended/deleted)
    performed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    performed_by = db.relationship('User', foreign_keys=[performed_by_id])

    def serialize(self):
        return {
            'id': self.id,
            'action': self.action,
            'resource': f"{self.resource_type}#{self.resource_id}",
            'timestamp': self.timestamp.isoformat(),
            'performed_by': self.performed_by.username if self.performed_by else 'system',
            'details': self.details
        }
```

### 2.3 Quota/Profile Mapping (Config-Driven)

```python
# In config.py or constants.py

PROFILE_TIERS = {
    'listener': {
        'storage_quota_gb': 0,
        'active_campaigns': 0,
        'description': 'Observer only'
    },
    'player': {
        'storage_quota_gb': 0,
        'active_campaigns': 0,
        'description': 'Can join campaigns'
    },
    'dm': {
        'storage_quota_gb': 1,
        'active_campaigns': 3,
        'description': 'Content creator (Dungeonmaster)'
    },
    'headmaster': {
        'storage_quota_gb': 5,
        'active_campaigns': 5,
        'description': 'Senior content creator'
    }
}

PLATFORM_ROLES = {
    'owner': {'level': 100, 'description': 'Platform owner'},
    'admin': {'level': 80, 'description': 'Full admin access'},
    'moderator': {'level': 60, 'description': 'Content & user moderation'},
    'supporter': {'level': 40, 'description': 'Support team access'}
}
```

---

## 3. Central Permission Library

### 3.1 Structure: `vtt_app/permissions.py`

```python
"""
Central permission system.
All authorization logic in one place — no scattered guards.
"""

from functools import wraps
from flask import abort, current_user, request
from vtt_app.models import Campaign, AuditLog, User

# ============= PLATFORM ROLE CHECKS =============

def has_platform_role(required_level_or_roles):
    """
    Decorator: Check platform_role level.

    Usage:
        @has_platform_role('admin')
        @has_platform_role(['moderator', 'admin'])
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user or not current_user.is_authenticated:
                abort(401)

            if isinstance(required_level_or_roles, str):
                roles = [required_level_or_roles]
            else:
                roles = required_level_or_roles

            if current_user.platform_role not in roles:
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def has_platform_role_level(min_level):
    """Check role hierarchy level (owner=100, admin=80, mod=60, supporter=40)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user or not current_user.is_authenticated:
                abort(401)

            from vtt_app.config import PLATFORM_ROLES
            current_level = PLATFORM_ROLES.get(current_user.platform_role, {}).get('level', 0)

            if current_level < min_level:
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============= CAMPAIGN-LEVEL PERMISSIONS =============

def can_view_campaign(user, campaign):
    """Check if user can view campaign (read-only)."""
    if not user:
        return False

    # Platform support+ can see all
    if user.platform_role in ['supporter', 'moderator', 'admin', 'owner']:
        return True

    # DM/Headmaster see own campaigns
    if campaign.dm_id == user.id:
        return True

    # Campaign members can see their campaign
    member = campaign.get_member(user.id)
    return member and member.is_active()

def can_edit_campaign(user, campaign):
    """Check if user can edit campaign (maps, details, etc.)."""
    if not user:
        return False

    # Only DM + mods
    if user.platform_role in ['moderator', 'admin', 'owner']:
        return True

    if campaign.dm_id == user.id:
        return True

    # CO_DM can edit
    member = campaign.get_member(user.id)
    return member and member.is_co_dm()

def can_delete_campaign(user, campaign):
    """Check if user can delete campaign."""
    if not user:
        return False

    # Only DM who created + mods/admins
    if user.platform_role in ['moderator', 'admin', 'owner']:
        return True

    return campaign.dm_id == user.id

def can_create_campaign(user):
    """Check if user can create a campaign."""
    if not user or not user.is_authenticated:
        return False

    # Only DM, Headmaster, and platform staff
    if user.profile_tier not in ['dm', 'headmaster']:
        if user.platform_role not in ['admin', 'owner']:
            return False

    # Check active campaign quota
    active_count = Campaign.query.filter_by(dm_id=user.id, status='active').count()
    quota = user.active_campaigns_quota or 0

    return active_count < quota

def can_view_team_campaigns(user):
    """Check if user can see all campaigns (team dashboard)."""
    if not user or not user.is_authenticated:
        return False

    return user.platform_role in ['supporter', 'moderator', 'admin', 'owner']

# ============= USER-LEVEL PERMISSIONS =============

def can_suspend_user(user, target_user):
    """Check if user can suspend another user."""
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
    """Check if user can delete/anonymize another user."""
    # Only owner/admin
    return user and user.platform_role in ['admin', 'owner'] and user.id != target_user.id

# ============= QUOTA CHECKS =============

def can_upload_asset(user, size_mb):
    """Check storage quota before upload."""
    if not user:
        return False, "Not authenticated"

    if user.platform_role in ['admin', 'owner']:
        return True, "Platform staff unlimited"

    available = user.storage_quota_gb - user.storage_used_gb
    if (size_mb / 1024) > available:
        return False, f"Quota exceeded. Available: {available}GB, Requested: {size_mb/1024:.2f}GB"

    return True, "OK"

# ============= DECORATORS FOR ROUTES =============

def require_campaign_access(permission_fn):
    """
    Decorator: Validate campaign access before route.

    Usage:
        @require_campaign_access(can_delete_campaign)
        def delete_campaign(campaign_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            campaign_id = kwargs.get('campaign_id') or request.view_args.get('campaign_id')
            campaign = Campaign.query.get(campaign_id)

            if not campaign:
                abort(404)

            if not permission_fn(current_user, campaign):
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

---

## 4. Audit Logging Middleware

### 4.1 Logger Helper: `vtt_app/utils/audit.py`

```python
"""Audit logging helpers."""

from flask import request, current_user
from vtt_app.models import AuditLog
from vtt_app.extensions import db
from vtt_app.utils.time import utcnow

def log_audit(action, resource_type, resource_id, details=None, performed_by=None):
    """
    Log an audit event.

    Args:
        action: e.g., 'campaign_delete', 'user_suspend', 'asset_upload'
        resource_type: 'campaign', 'user', 'session', etc.
        resource_id: ID of affected resource
        details: Dict with extra context {'reason': '...', 'old_values': {...}}
        performed_by: User who performed action (default: current_user)
    """
    performer = performed_by or current_user

    log = AuditLog(
        user_id=performer.id if performer else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=request.remote_addr if request else None,
        timestamp=utcnow()
    )

    db.session.add(log)
    db.session.commit()

    return log

def log_campaign_deletion(user, campaign_id, reason=None):
    """Log campaign deletion."""
    return log_audit(
        action='campaign_deleted',
        resource_type='campaign',
        resource_id=campaign_id,
        details={'reason': reason},
        performed_by=user
    )

def log_user_suspension(admin_user, target_user, reason=None):
    """Log user suspension."""
    return log_audit(
        action='user_suspended',
        resource_type='user',
        resource_id=target_user.id,
        details={'reason': reason},
        performed_by=admin_user
    )

def log_quota_exceeded(user, resource_type, limit_type, current, limit):
    """Log quota violation attempt."""
    return log_audit(
        action='quota_exceeded',
        resource_type=resource_type,
        resource_id=user.id,
        details={
            'limit_type': limit_type,  # 'storage', 'campaigns'
            'current': current,
            'limit': limit
        },
        performed_by=user
    )
```

---

## 5. Team-View & Filtering

### 5.1 Campaign Query Helper: `vtt_app/models/campaign.py`

```python
@staticmethod
def get_visible_campaigns(user):
    """
    Get campaigns visible to user.

    Logic:
    - Supporter+: All campaigns
    - DM/Headmaster: Own campaigns + joined campaigns
    - Player: Only joined campaigns
    """
    if not user:
        return Campaign.query.filter(False)  # Empty result

    # Platform staff see all
    if user.platform_role in ['supporter', 'moderator', 'admin', 'owner']:
        return Campaign.query.all()

    # DM/Headmaster see own campaigns
    own_campaigns = Campaign.query.filter_by(dm_id=user.id).all()

    # Plus campaigns they're members of
    member_campaigns = db.session.query(Campaign).join(
        CampaignMember,
        Campaign.id == CampaignMember.campaign_id
    ).filter(
        CampaignMember.user_id == user.id,
        CampaignMember.status == 'active'
    ).all()

    # Union (avoid duplicates)
    campaign_ids = set(c.id for c in own_campaigns + member_campaigns)
    return Campaign.query.filter(Campaign.id.in_(campaign_ids)).all()

@staticmethod
def get_team_campaigns(limit=100, offset=0, filter_dm=None, filter_status=None):
    """
    Get all campaigns for team dashboard (supporter+ only).

    Args:
        limit: Pagination limit
        offset: Pagination offset
        filter_dm: Filter by DM username
        filter_status: Filter by campaign status ('active', 'archived')
    """
    query = Campaign.query

    if filter_dm:
        query = query.join(User).filter(User.username.ilike(f"%{filter_dm}%"))

    if filter_status:
        query = query.filter_by(status=filter_status)

    return query.order_by(Campaign.updated_at.desc()).limit(limit).offset(offset).all()
```

---

## 6. Route Implementation Example

### 6.1 Campaign Delete Route

```python
@app.route('/api/campaigns/<int:campaign_id>', methods=['DELETE'])
@require_campaign_access(can_delete_campaign)
def delete_campaign(campaign_id):
    """Delete campaign — requires DM or Moderator+."""
    campaign = Campaign.query.get(campaign_id)

    # Log the deletion
    log_audit(
        action='campaign_deleted',
        resource_type='campaign',
        resource_id=campaign_id,
        details={
            'campaign_name': campaign.name,
            'deleted_by': current_user.username
        },
        performed_by=current_user
    )

    # Soft delete or hard delete
    campaign.status = 'archived'  # or db.session.delete(campaign)
    db.session.commit()

    return jsonify({'message': 'Campaign deleted'}), 200
```

### 6.2 Team Dashboard Route

```python
@app.route('/api/team/campaigns', methods=['GET'])
@has_platform_role_level(40)  # Supporter+
def get_team_campaigns():
    """Get all campaigns for team dashboard."""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    filter_dm = request.args.get('dm')
    filter_status = request.args.get('status')

    offset = (page - 1) * limit

    campaigns = Campaign.get_team_campaigns(
        limit=limit,
        offset=offset,
        filter_dm=filter_dm,
        filter_status=filter_status
    )

    return jsonify({
        'campaigns': [c.serialize() for c in campaigns],
        'page': page,
        'limit': limit
    }), 200
```

---

## 7. Migration Strategy

### 7.1 Data Migration (for existing users)

```sql
-- Add new columns to users table
ALTER TABLE users ADD COLUMN platform_role VARCHAR(20) DEFAULT 'supporter';
ALTER TABLE users ADD COLUMN profile_tier VARCHAR(20) DEFAULT 'player';
ALTER TABLE users ADD COLUMN storage_quota_gb INTEGER;
ALTER TABLE users ADD COLUMN storage_used_gb FLOAT DEFAULT 0.0;
ALTER TABLE users ADD COLUMN active_campaigns_quota INTEGER;
ALTER TABLE users ADD COLUMN is_suspended BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN suspended_at DATETIME;
ALTER TABLE users ADD COLUMN suspended_reason TEXT;
ALTER TABLE users ADD COLUMN suspended_by INTEGER;

-- Map existing role_id to platform_role
UPDATE users SET platform_role = 'admin' WHERE role_id = (SELECT id FROM roles WHERE name = 'Admin');
UPDATE users SET platform_role = NULL WHERE role_id = (SELECT id FROM roles WHERE name = 'DM');
UPDATE users SET profile_tier = 'dm' WHERE role_id = (SELECT id FROM roles WHERE name = 'DM');
UPDATE users SET profile_tier = 'player' WHERE role_id = (SELECT id FROM roles WHERE name = 'Player');

-- Set quotas based on profile_tier
UPDATE users SET storage_quota_gb = 1, active_campaigns_quota = 3 WHERE profile_tier = 'dm';
UPDATE users SET storage_quota_gb = 5, active_campaigns_quota = 5 WHERE profile_tier = 'headmaster';

-- Create AuditLog table
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSON,
    ip_address VARCHAR(45),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    performed_by_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (performed_by_id) REFERENCES users(id)
);

CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
```

---

## 8. Acceptance Criteria (M17 Apply)

✅ **Data Model**
- [ ] User model extended with platform_role, profile_tier, quotas, suspension fields
- [ ] AuditLog model created with timestamp/ip/performer tracking
- [ ] Migration creates new columns + backfills existing data

✅ **Permission Library**
- [ ] Central `vtt_app/permissions.py` with all authorization functions
- [ ] Decorators: `@has_platform_role`, `@require_campaign_access`
- [ ] No scattered permission checks in routes

✅ **Audit Logging**
- [ ] `vtt_app/utils/audit.py` with helper functions
- [ ] Logs: campaign_deleted, user_suspended, quota_exceeded
- [ ] Timestamp + IP + performer tracked

✅ **Team-View**
- [ ] `Campaign.get_visible_campaigns(user)` filters by role
- [ ] `Campaign.get_team_campaigns()` supports pagination + filtering
- [ ] Route `/api/team/campaigns` returns all campaigns for supporter+

✅ **Documentation**
- [ ] Role hierarchy diagram
- [ ] Permission matrix (who can do what)
- [ ] API examples for team dashboard

---

## 9. Next Steps (M18+)

- **M18**: Implement soft-delete/hard-delete/restoration logic
- **M19**: Asset domain + quota enforcement on uploads
- **M20**: Upload security pipeline with MIME validation
- **M21**: Storage abstraction (local → S3)

---

## Notes

- **Backward Compatibility**: Old `role_id` field remains but deprecated. Platform-level logic uses `platform_role` + `profile_tier`.
- **Extensibility**: New roles can be added to `PLATFORM_ROLES` config without code changes.
- **Performance**: Audit logging is async-ready (queue large logs for batch writes later).
- **Security**: All permission checks centralized → easier to audit + maintain.
