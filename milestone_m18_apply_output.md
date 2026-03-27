# M18 Apply Phase: Account Lifecycle & Profile Governance

**Status**: Architecture & Design Complete
**Date**: 2026-03-27
**Scope**: User deletion state machine, ownership transfer, anonymization, scheduled cleanup

---

## Design Decisions

### 1. Deletion Strategy: Hybrid (Soft → Hard)

```
┌──────────────────────────────────────────────┐
│  User initiates deletion request             │
│  account_state = 'marked_for_deletion'       │
│  deleted_at = NOW                            │
└──────────────────────────────────────────────┘
                       ↓ (30 days)
┌──────────────────────────────────────────────┐
│  Admin/User can restore within 30d           │
│  POST /api/profile/restore-account           │
│  account_state → 'active'                    │
│  deleted_at = NULL                           │
└──────────────────────────────────────────────┘
        OR (after 30d, automatic)
                       ↓
┌──────────────────────────────────────────────┐
│  Hard delete executed (scheduled job)        │
│  - User row soft-deleted from auth           │
│  - PII anonymized (username, email, etc)     │
│  - Password/MFA scrubbed                     │
│  - Account unrecoverable                     │
└──────────────────────────────────────────────┘
```

**Retention Timeline**:
- Day 0-30: Soft-deleted, can restore
- Day 30+: Hard-delete job runs daily
- Day 31+: User permanently gone

---

### 2. Account State Machine

```python
ACCOUNT_STATE = {
    'active': 'Normal active user',
    'deactivated': 'User manually paused account (can reactivate)',
    'marked_for_deletion': 'Deletion requested, 30d grace period',
    'permanently_deleted': 'Hard-deleted, unrecoverable',
    'suspended': 'Moderation ban (separate from deletion)'
}
```

**State Transitions**:
```
active ←→ deactivated
  ↓
marked_for_deletion ←→ [restore possible within 30d]
  ↓
permanently_deleted [final]

suspended [orthogonal - can be applied to any state]
```

---

### 3. Ownership Transfer: Cascade to Admin

**When user is deleted**:
- All campaigns owned by deleted user → assigned to `admin_user_id`
- Admin receives notification of transferred campaigns
- Campaign membership records remain (for history)
- Active sessions archived (read-only)

**Why**: Preserves player continuity, admin can manage orphaned campaigns later

**SQL**:
```sql
UPDATE campaigns
SET owner_id = :admin_user_id
WHERE owner_id = :deleted_user_id
```

---

### 4. Anonymization Strategy

**Immediate (on request)**:
- ❌ Delete password_hash
- ❌ Delete mfa_secret
- ❌ Delete email (set to NULL)
- ✓ Scrub username → "deleted_user_<id>"

**On Hard-Delete (after 30d)**:
- ✓ Full anonymization of audit logs (IP → NULL)
- ✓ Chat messages anonymized ("deleted user" sender)
- ✓ Campaign membership scrubbed

**Preserve (never delete)**:
- ✓ Audit logs (legal requirement)
- ✓ Campaign ownership history
- ✓ Session transcripts (game history)

---

### 5. Database Schema Changes

```python
# User model additions
class User(db.Model):
    # Lifecycle
    account_state = db.Column(
        db.String(20),
        default='active',
        index=True
    )
    # active, deactivated, marked_for_deletion, permanently_deleted, suspended

    deleted_at = db.Column(db.DateTime)  # When deletion was requested
    deletion_reason = db.Column(db.Text)
    deletion_requested_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Last action (to show in recovery email)
    last_active_at = db.Column(db.DateTime)

    # For hard-delete tracking
    hard_deleted_at = db.Column(db.DateTime)  # When actually hard-deleted
```

---

### 6. API Endpoints (M18 Deploy)

#### User-Initiated (Self-Service)

```
POST /api/profile/request-deletion
{
  "reason": "Leaving the platform",
  "password": "confirm_password"  # Security: require password
}
Response:
{
  "status": "deletion_requested",
  "grace_period_ends": "2026-04-27T00:00:00Z",
  "can_cancel_until": "2026-04-27T00:00:00Z",
  "message": "Your account will be permanently deleted in 30 days. You can cancel this request anytime."
}

POST /api/profile/cancel-deletion
{
  "reason": "Changed my mind"
}
Response:
{
  "status": "deletion_cancelled",
  "account_state": "active",
  "message": "Your account has been restored."
}

POST /api/profile/deactivate
{
  "reason": "Taking a break"
}
Response:
{
  "status": "deactivated",
  "message": "Your account has been paused. You can reactivate anytime."
}

POST /api/profile/reactivate
Response:
{
  "status": "active",
  "message": "Welcome back!"
}
```

#### Admin-Only

```
GET /api/admin/users?state=marked_for_deletion
Response:
{
  "users": [
    {
      "id": 123,
      "username": "deleted_user_123",  # Already anonymized
      "deleted_at": "2026-03-27T10:00:00Z",
      "grace_period_ends": "2026-04-27T10:00:00Z",
      "deletion_reason": "Leaving the platform",
      "can_restore": true
    }
  ]
}

POST /api/admin/users/:user_id/restore
{
  "reason": "Admin restore"
}
Response:
{
  "status": "active",
  "message": "User restored."
}

POST /api/admin/users/:user_id/force-delete
{
  "reason": "Cleanup",
  "anonymize": true
}
Response:
{
  "status": "permanently_deleted",
  "message": "User hard-deleted."
}

POST /api/admin/campaigns/:campaign_id/reassign-owner
{
  "new_owner_id": :admin_user_id,
  "reason": "Original DM deleted"
}
Response:
{
  "campaign_id": 456,
  "new_owner_id": 789,
  "message": "Campaign reassigned."
}
```

---

### 7. Scheduled Job: Hard-Delete Job

**Job Name**: `delete_old_marked_users_job.py`

**Schedule**: Daily at 2am (off-peak)

**Logic**:
```python
def delete_marked_users_after_grace_period():
    """
    Hard-delete users marked for deletion > 30 days ago.
    """
    cutoff = datetime.utcnow() - timedelta(days=30)

    # Find all users to delete
    users_to_delete = User.query.filter(
        User.account_state == 'marked_for_deletion',
        User.deleted_at < cutoff
    ).all()

    for user in users_to_delete:
        try:
            # Anonymize
            user.username = f'deleted_user_{user.id}'
            user.email = None
            user.password_hash = None
            user.mfa_secret = None

            # Update state
            user.account_state = 'permanently_deleted'
            user.hard_deleted_at = utcnow()

            # Log event
            log_audit(
                action='user_permanently_deleted',
                resource_type='user',
                resource_id=user.id,
                details={
                    'reason': 'grace_period_expired',
                    'grace_period_days': 30,
                    'anonymized': True
                }
            )

            db.session.commit()
        except Exception as e:
            logger.error(f'Error hard-deleting user {user.id}: {e}')
            db.session.rollback()
```

**Monitoring**:
- Track: # users deleted, failures, total time
- Alert if: > 100 users deleted in one run, failures > 5%

---

### 8. Cascading Data Rules

| Entity | Deletion Rule | Rationale |
|--------|---|---|
| **Campaigns** | Transfer to admin | Preserve player continuity |
| **CampaignMember** | Keep record (anonymize username ref) | Preserve game history |
| **GameSession** | Archive (status='archived') | Read-only game records |
| **Assets** (M19) | Transfer to admin | Preserve maps/tokens |
| **ChatMessage** | Anonymize sender to "deleted user" | Preserve conversation history |
| **AuditLog** | Keep row, scrub IP | Legal compliance |
| **ModerationReport** | Keep record | For dispute resolution |

---

### 9. Recovery Endpoint Details

**Scenario: Admin wants to restore user**

```python
@app.route('/api/admin/users/<int:user_id>/restore', methods=['POST'])
@has_platform_role('admin', 'moderator')
def restore_user(user_id):
    """Restore a user marked for deletion."""
    user = User.query.get(user_id)

    if not user or user.account_state != 'marked_for_deletion':
        abort(404)

    # Check if still within grace period
    grace_period_end = user.deleted_at + timedelta(days=30)
    if datetime.utcnow() > grace_period_end:
        abort(400, "Grace period expired. User cannot be restored.")

    # Restore
    user.account_state = 'active'
    user.deleted_at = None
    user.deletion_reason = None
    db.session.commit()

    # Log
    log_audit(
        action='user_restored',
        resource_type='user',
        resource_id=user_id,
        details={'restored_by': current_user.id},
        performed_by=current_user
    )

    return jsonify({'status': 'restored'}), 200
```

---

### 10. Email Notifications

**On Deletion Request**:
```
Subject: Your Roll-Drauf account will be deleted

Hi {username},

You requested to delete your account. Your account will be permanently
deleted in 30 days ({grace_period_end_date}).

If you change your mind, you can restore it anytime before the deletion:
[Restore Account Button]

Reason given: {reason}

Your campaigns have been transferred to our support team to preserve
your players' progress. We'll manage them on your behalf.

Questions? Contact: support@rolldrauf.de
```

**On Restoration**:
```
Subject: Your account has been restored

Hi {username},

Your account is active again. Your campaigns are back in your control.

Welcome back!
```

**On Hard-Delete (Admin Notification)**:
```
Subject: User permanently deleted: {old_username}

User ID: {user_id}
Deleted: {hard_deleted_at}
Campaigns transferred: {campaign_count}

No further action needed.
```

---

### 11. Acceptance Criteria (M18 Apply)

✅ **Data Model**
- [ ] User model extended with `account_state` enum
- [ ] `deleted_at`, `deletion_reason`, `deletion_requested_by` fields added
- [ ] `last_active_at` field added (for recovery email context)
- [ ] `hard_deleted_at` field added (for cleanup tracking)
- [ ] Indexes on `account_state` and `deleted_at`

✅ **State Machine Logic**
- [ ] `can_request_deletion()` — checks state transitions
- [ ] `can_restore()` — checks grace period
- [ ] `is_accessible()` — checks if user can be used (not deleted/suspended)
- [ ] State transition validation (no invalid transitions)

✅ **Ownership Transfer**
- [ ] Campaign.owner_id updated to admin on user soft-delete
- [ ] Active sessions archived when campaign owner deleted
- [ ] Transfer logged in audit trail

✅ **Anonymization**
- [ ] Username scrubbed immediately on request
- [ ] Email set to NULL immediately
- [ ] Password/MFA scrubbed on hard-delete
- [ ] Audit log IPs anonymized on hard-delete

✅ **Scheduled Job**
- [ ] Hard-delete job created (`jobs/delete_old_marked_users_job.py`)
- [ ] Scheduled daily (off-peak)
- [ ] Error handling + logging
- [ ] Monitoring metrics

✅ **API Endpoints**
- [ ] `POST /api/profile/request-deletion`
- [ ] `POST /api/profile/cancel-deletion`
- [ ] `POST /api/profile/deactivate`
- [ ] `POST /api/profile/reactivate`
- [ ] `POST /api/admin/users/:id/restore`
- [ ] `POST /api/admin/users/:id/force-delete`
- [ ] `GET /api/admin/users?state=marked_for_deletion`

✅ **Notifications**
- [ ] Deletion request email
- [ ] Restoration email
- [ ] Admin log email (for hard-delete)
- [ ] Campaign transfer notification (to admin)

✅ **Migration**
- [ ] `migration_m18_user_lifecycle.sql` with rollback

---

## Next Steps (M18 Deploy)

1. ✅ Design complete (this doc)
2. ⏳ Code implementation (User model, endpoints, job)
3. ⏳ Database migration
4. ⏳ Email templates
5. ⏳ Tests (test_user_lifecycle.py)
6. ⏳ Integration with M17 permission system (deleted users = no access)

---

## Known Limitations & Future Work

- **M19**: Asset ownership transfer (maps, tokens)
- **M20**: Upload security for transferred assets
- **Future**: GDPR data export before deletion
- **Future**: Batch operations (admin delete multiple users)
- **Future**: Deletion reason analytics (why users leave?)

---

## Critical Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Deletion Strategy | Hybrid (soft 30d → hard) | GDPR + audit trail balance |
| Ownership | Campaigns → admin | Preserves player continuity |
| Anonymization | Immediate username, 30d full | Privacy + compliance |
| Grace Period | 30 days | Standard GDPR compliance |
| Hard-Delete Job | Daily at 2am | Off-peak, consistent |
| Recovery | Admin-restorable always | Safety net for accidents |

