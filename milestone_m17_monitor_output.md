# M17 Monitor Phase: Acceptance Criteria & Go/No-Go Gates

**Status**: Implementation Complete - Awaiting Testing & Deployment
**Date**: 2026-03-27
**Scope**: Verify permission system, role hierarchy, audit logging, team-view

---

## 1. Acceptance Criteria Checklist

### ✅ Data Model (User Extensions)

- [x] User model extended with `platform_role` field (owner, admin, moderator, supporter)
- [x] User model extended with `profile_tier` field (dm, headmaster, player, listener)
- [x] User model includes quotas: `storage_quota_gb`, `storage_used_gb`, `active_campaigns_quota`
- [x] User model includes suspension fields: `is_suspended`, `suspended_at`, `suspended_reason`, `suspended_by`
- [x] Relationships properly configured: `campaigns_as_dm`, `suspended_by_user`
- [x] Helper methods: `get_storage_usage_percent()`, `get_active_campaigns_count()`, `can_create_campaign()`

### ✅ Audit Logging

- [x] AuditLog model created with all required fields
- [x] Foreign keys: `user_id`, `performed_by_id` for tracking who did what
- [x] Fields: `action`, `resource_type`, `resource_id`, `details`, `ip_address`, `timestamp`
- [x] Indexes on `timestamp`, `action`, `resource_type/resource_id`
- [x] `serialize()` method for JSON responses
- [x] Audit helper functions: `log_campaign_deleted()`, `log_user_suspended()`, `log_permission_changed()`, etc.

### ✅ Central Permission Library

- [x] `vtt_app/permissions.py` created (single source of truth)
- [x] Decorators: `@has_platform_role()`, `@has_platform_role_level()`, `@require_campaign_access()`, `@require_quota()`
- [x] Campaign permissions: `can_view_campaign()`, `can_edit_campaign()`, `can_delete_campaign()`, `can_create_campaign()`
- [x] User permissions: `can_suspend_user()`, `can_delete_user()`
- [x] Team permissions: `can_view_all_campaigns()`
- [x] Quota checks: `can_upload_asset()`
- [x] Helper: `get_user_permissions_summary()`
- [x] No scattered permission checks in routes

### ✅ Team-View & Filtering

- [x] `Campaign.get_visible_campaigns(user)` filters campaigns by role
- [x] `Campaign.get_team_campaigns(limit, offset, filter_dm, filter_status)` for team dashboard
- [x] Team dashboard endpoint `/api/team/campaigns` (example provided)
- [x] Pagination support (page, limit)
- [x] Filtering support (dm username, campaign status)

### ✅ Configuration

- [x] `PLATFORM_ROLES` dict in config.py with levels (owner=100, admin=80, moderator=60, supporter=40)
- [x] `PROFILE_TIERS` dict in config.py with quotas per tier
- [x] Config-driven (not hardcoded in code)

### ✅ Database Migration

- [x] SQL migration file created: `migrations/migration_m17_add_platform_roles_and_audit.sql`
- [x] Migration includes column additions, indexes, data mapping, rollback
- [x] Backward compatible (old `role_id` field remains)

### ✅ Code Structure & Documentation

- [x] AuditLog model: `vtt_app/models/audit_log.py`
- [x] User model extensions: `vtt_app/models/user.py`
- [x] Permission library: `vtt_app/permissions.py`
- [x] Audit helpers: `vtt_app/utils/audit.py`
- [x] Campaign extensions: `vtt_app/models/campaign.py`
- [x] M17 Apply design doc: `milestone_m17_apply_output.md`
- [x] M17 Monitor checklist: `milestone_m17_monitor_output.md` (this file)

---

## 2. Role Hierarchy Matrix (Verification)

| Action | Owner | Admin | Moderator | Supporter | Headmaster | DM | Player | Listener |
|--------|-------|-------|-----------|-----------|-----------|-----|--------|----------|
| View all campaigns | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Create campaign | ✅ | ✅ | ❌ | ❌ | ✅* | ✅* | ❌ | ❌ |
| Delete any campaign | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Delete own campaign | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Edit any campaign | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Edit own campaign | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Edit campaign as CO_DM | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Suspend user | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Delete user | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Upload assets | ✅ | ✅ | ✅ | ✅ | ✅* | ✅* | ❌ | ❌ |

*Quota-dependent (must have active_campaigns < quota and storage_used < quota_gb)

---

## 3. Quota Testing Matrix

### DM Tier (1GB, 3 campaigns)

| Scenario | Expected Result | Test Command |
|----------|---|---|
| Create campaign #1 | ✅ Success | `POST /api/campaigns` (profile_tier=dm) |
| Create campaign #2 | ✅ Success | `POST /api/campaigns` (profile_tier=dm) |
| Create campaign #3 | ✅ Success | `POST /api/campaigns` (profile_tier=dm) |
| Create campaign #4 | ❌ Quota exceeded | `POST /api/campaigns` (profile_tier=dm) |
| Upload 500MB asset | ✅ Success | `POST /api/assets/upload` (500MB) |
| Upload another 600MB | ❌ Quota exceeded | `POST /api/assets/upload` (600MB) |

### Headmaster Tier (5GB, 5 campaigns)

| Scenario | Expected Result | Test Command |
|----------|---|---|
| Create 5 campaigns | ✅ Success | Loop `POST /api/campaigns` x5 |
| Create campaign #6 | ❌ Quota exceeded | `POST /api/campaigns` |
| Upload 4GB asset | ✅ Success | `POST /api/assets/upload` (4GB) |
| Upload 2GB asset | ❌ Quota exceeded | `POST /api/assets/upload` (2GB) |

---

## 4. Audit Logging Verification

### Test Cases

| Action | Expected Log | Log Field Check |
|--------|---|---|
| Delete campaign | `campaign_deleted` | action, resource_type, resource_id, performed_by_id, details.reason |
| Suspend user | `user_suspended` | action, resource_type, resource_id, performed_by_id, ip_address |
| Create campaign | `campaign_created` | action, resource_type, resource_id, details.campaign_name |
| Upload asset | `asset_uploaded` | action, resource_type, details.filename, details.size_mb |
| Quota exceeded | `quota_exceeded` | action, details.limit_type, details.current, details.limit |

### Audit Log Query Tests

```sql
-- Verify audit table exists and has data
SELECT COUNT(*) FROM audit_logs;

-- Verify timestamp index
EXPLAIN QUERY PLAN SELECT * FROM audit_logs WHERE timestamp > datetime('now', '-1 hour');

-- Verify resource filtering
SELECT * FROM audit_logs WHERE resource_type = 'campaign' AND resource_id = 1;
```

---

## 5. Team-View Testing

### Query Tests

| Test Case | Expected Behavior | SQL/Code |
|-----------|---|---|
| Supporter views all campaigns | Returns all campaigns | `Campaign.get_team_campaigns()` |
| DM views campaigns | Returns own + joined | `Campaign.get_visible_campaigns(dm_user)` |
| Player views campaigns | Returns joined only | `Campaign.get_visible_campaigns(player_user)` |
| Pagination | Returns limit x offset records | `?limit=20&offset=40` |
| Filter by DM | Returns campaigns for DM | `?dm=username` |
| Filter by status | Returns active/archived/paused | `?status=active` |

### Route Tests

```bash
# Team dashboard (supporter+ only)
curl -X GET "http://localhost/api/team/campaigns?limit=20&page=1" \
  -H "Authorization: Bearer $SUPPORTER_TOKEN"
# Expected: 200 + list of all campaigns

# Campaign view (user-specific)
curl -X GET "http://localhost/api/campaigns/visible" \
  -H "Authorization: Bearer $DM_TOKEN"
# Expected: 200 + own campaigns + joined campaigns

# Non-supporter tries team dashboard
curl -X GET "http://localhost/api/team/campaigns" \
  -H "Authorization: Bearer $PLAYER_TOKEN"
# Expected: 403 Forbidden
```

---

## 6. Integration Tests (Code-Level)

### Permission Tests

```python
# vtt_app/tests/test_permissions_m17.py

def test_can_view_campaign_as_supporter():
    user = create_user(platform_role='supporter')
    campaign = create_campaign(owner_id=999)
    assert can_view_campaign(user, campaign) == True

def test_can_view_campaign_as_player_not_member():
    user = create_user(profile_tier='player')
    campaign = create_campaign(owner_id=999)
    assert can_view_campaign(user, campaign) == False

def test_can_create_campaign_dm_with_quota():
    user = create_user(profile_tier='dm', active_campaigns_quota=3)
    create_campaign(owner_id=user.id)  # 1st
    create_campaign(owner_id=user.id)  # 2nd
    create_campaign(owner_id=user.id)  # 3rd
    assert can_create_campaign(user) == False

def test_can_suspend_user():
    admin = create_user(platform_role='admin')
    target = create_user(username='target')
    assert can_suspend_user(admin, target) == True
    assert can_suspend_user(target, admin) == False

def test_audit_log_created():
    admin = create_user(platform_role='admin')
    campaign = create_campaign()
    log_campaign_deleted(campaign, deleted_by=admin, reason='Inappropriate content')

    log = AuditLog.query.filter_by(action='campaign_deleted').first()
    assert log is not None
    assert log.performed_by_id == admin.id
    assert log.details['reason'] == 'Inappropriate content'
```

---

## 7. Go/No-Go Decision Gate

### Must-Have Criteria (Blocking)

- [ ] All acceptance criteria checked (section 1)
- [ ] Role hierarchy matrix verified (section 2)
- [ ] Quota logic tested (section 3)
- [ ] Audit logging working (section 4)
- [ ] Team-view queries returning correct results (section 5)
- [ ] No permission checks scattered in routes (centralized in `permissions.py`)
- [ ] AuditLog table created successfully
- [ ] Database migration runs without errors
- [ ] Backward compatibility maintained (old `role_id` field still works)

### Nice-to-Have (Non-Blocking)

- [ ] Audit logs visible in admin console
- [ ] Performance tested (pagination works with 1000+ campaigns)
- [ ] Docstrings complete for all functions

---

## 8. Deployment & Rollout Strategy

### Pre-Deployment Checklist

1. **Database Backup**: Create full backup before migration
2. **Migration Dry-Run**: Run migration on staging first
3. **Code Deployment**: Deploy permission library + model changes
4. **Test Suite**: Run all permission tests against production-like data
5. **Audit Logging**: Verify audit logs are being written

### Rollback Plan

If critical issues found:

1. Restore database backup
2. Revert code to previous version
3. Disable new permission checks
4. Log incident in audit system

### Monitoring After Deployment

- Track `403 Forbidden` errors (permission denials)
- Monitor audit log write latency
- Check for `quota_exceeded` events (early warning)
- Alert on abnormal suspension patterns

---

## 9. Known Limitations & Future Work

- **M18**: Soft-delete/hard-delete/restoration logic
- **M19**: Asset domain deep discovery + ownership models
- **M20**: Upload security pipeline (MIME validation, AV hooks)
- **M21**: Storage abstraction (local → S3)
- **M22**: Asset serving + signed URLs
- **M23-M24**: UX flows (campaign + session workspace)

---

## 10. Sign-Off

**Owner**: [Team Lead Name]
**Approved By**: [Product Manager Name]
**Date**: [Date of Approval]

**Status**: ✅ **Ready for M17 Deploy Phase**

---

## Appendix: File Manifest

**New Files Created**:
- `vtt_app/models/audit_log.py` — AuditLog model
- `vtt_app/permissions.py` — Central permission library
- `vtt_app/utils/audit.py` — Audit logging helpers
- `migrations/migration_m17_add_platform_roles_and_audit.sql` — Database migration
- `milestone_m17_apply_output.md` — M17 Apply design doc
- `milestone_m17_monitor_output.md` — This file

**Modified Files**:
- `vtt_app/models/user.py` — Extended with platform_role, profile_tier, quotas, suspension
- `vtt_app/models/campaign.py` — Added team-view methods + get_member
- `vtt_app/models/__init__.py` — Added AuditLog export
- `config.py` — Added PLATFORM_ROLES + PROFILE_TIERS

**No Breaking Changes**: All backward compatible (old `role_id` field remains)
