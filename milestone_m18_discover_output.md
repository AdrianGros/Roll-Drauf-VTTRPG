# M18 Discover Phase: Account Lifecycle & Profile Governance

**Status**: Discovery in Progress
**Date**: 2026-03-27
**Scope**: User deletion, ownership transfer, account state machine, recovery

---

## Current State Analysis

### User Model Status
- ✅ `is_active` field exists (but unused in deletion logic)
- ✅ `is_suspended` + `suspended_at` + `suspended_reason` (M17)
- ❌ No `deleted_at` field
- ❌ No deletion request tracking
- ❌ No state machine for lifecycle
- ❌ No ownership transfer mechanism

### Related Models
- **Campaign**: `owner_id` → campaign ownership tied to user
- **CampaignMember**: Records of user membership in campaigns
- **GameSession**: Sessions tied to campaigns
- **Asset** (M19+): Files tied to campaigns/sessions

### Cascading Dependencies
If user is deleted, what happens to:
1. **Owned Campaigns** — orphaned? transferred? deleted?
2. **Campaign Memberships** — removed? anonymized?
3. **Game Sessions** — archived? deleted?
4. **Assets** (maps, tokens) — deleted? transferred?
5. **Chat Messages** — deleted? anonymized to "deleted user"?
6. **Audit Logs** — kept for compliance? anonymized?

---

## M18 Discovery Questions

### 1. Deletion Strategy: Soft vs. Hard vs. Hybrid?

**Option A: Soft-Delete Only** (Preserve history, compliance)
```
User marked as deleted, but row remains.
- Pro: Full audit trail, can restore anytime
- Con: Dead rows accumulate, privacy concerns
```

**Option B: Hard-Delete Only** (GDPR right-to-be-forgotten)
```
User data wiped immediately.
- Pro: Clean, privacy-first
- Con: Irreversible, audit trail lost
```

**Option C: Hybrid (Soft → Hard after retention period)**
```
Day 0-30: Soft delete (grace period, can restore)
Day 30+: Hard delete (GDPR compliance)
- Pro: Both audit trail + privacy
- Con: Complex, needs scheduled jobs
```

**Q: Which strategy for Roll-Drauf?**

---

### 2. Ownership Transfer: What happens to DM's campaigns?

**Option A: Campaigns deleted with user**
```
DELETE FROM campaigns WHERE owner_id = deleted_user_id
- Pro: Clean slate
- Con: Lose campaign history, active sessions orphaned
```

**Option B: Campaigns transferred to Admin/Support**
```
UPDATE campaigns SET owner_id = support_admin_id WHERE owner_id = deleted_user_id
- Pro: Preserve campaigns for players
- Con: Admin burden, "ghost campaigns"
```

**Option C: Campaigns transferred to co-DM (if exists)**
```
IF campaign has co_dm → promote to DM
ELSE → transfer to admin
- Pro: Natural succession
- Con: Complex logic
```

**Option D: Campaigns archived (read-only)**
```
UPDATE campaigns SET status = 'archived' WHERE owner_id = deleted_user_id
- Pro: Preserve history, no new sessions
- Con: Players can't continue
```

**Q: Which approach for Roll-Drauf?**

---

### 3. Anonymization: What data to anonymize vs. delete?

**Anonymizable Data** (keep for compliance, scrub personally identifiable):
- Username → "deleted_user_12345"
- Email → null
- Password hash → null
- MFA secret → null
- IP addresses in audit logs → null

**Delete Immediately**:
- Password hash
- MFA secret
- Email address
- Auth tokens

**Keep (cannot delete)**:
- Audit logs (legal requirement)
- Campaign ownership history (for dispute resolution)
- Transaction/billing records (tax law)

**Q: What's the compliance requirement for Roll-Drauf? (GDPR? National? Internal?)**

---

### 4. Deletion Request Flow: Immediate vs. Grace Period?

**Option A: Immediate Deletion**
```
User clicks "Delete Account" → Account gone now
- Pro: Fast, clean
- Con: No undo, accidental deletions
```

**Option B: Deletion Request + Grace Period**
```
Day 0: User requests deletion
Day 0-30: Account marked for deletion, user can cancel
Day 30: Automatic hard-delete executed
- Pro: Safety net for accidents
- Con: More complex, longer UX
```

**Option C: Admin-only Deletion**
```
Only admins/mods can delete user accounts.
Users can only deactivate.
- Pro: Prevents accidents, audit trail
- Con: Less user control
```

**Q: What UX flow for Roll-Drauf players?**

---

### 5. Recovery & Restoration: How long can we restore?

**Option A: No restoration (deleted = gone)**
```
Instant permanent deletion.
- Pro: Simple, clear policy
- Con: No safety net
```

**Option B: Restorable for X days**
```
Soft-deleted for 30 days, then permanent delete.
Can restore within window.
- Pro: Grace period, audit trail
- Con: Need to track "restore" events
```

**Option C: Admin can restore indefinitely**
```
Admins can restore any deleted user (even after 30d).
- Pro: Ultimate safety net
- Con: Privacy concerns, storage growth
```

**Q: What's the retention window for Roll-Drauf?**

---

### 6. User Lifecycle State Machine: What states?

**Current**:
- `is_active = true` (normal)
- `is_active = false` (deactivated?)
- `is_suspended = true` (moderation ban)
- ???

**Proposed State Machine**:
```
                    ┌─ ACTIVE ─┐
                    │           │
                    │           ↓
                ┌───┴─ DEACTIVATED (user can reactivate)
                │           │
                │           ↓
            ┌───┴─ DELETION_REQUESTED (30d grace period)
            │           │
            │           ↓
        ┌───┴─ PERMANENTLY_DELETED (hard delete executed)
        │
        └──────── SUSPENDED (moderation, not deletion)
```

**Q: Which state machine for Roll-Drauf?**

---

## Dependencies to Map

### Users → Campaigns (1:many)
- **current**: Campaign.owner_id FK to User.id
- **question**: On user delete, what happens to campaigns?

### Users → CampaignMember (1:many)
- **current**: CampaignMember.user_id FK to User.id
- **question**: On user delete, cascade delete membership?

### Users → GameSession (1:many via Campaign)
- **current**: No direct FK, via Campaign
- **question**: On user delete, what happens to active sessions?

### Users → Assets (1:many via Campaign)
- **current**: No direct FK, via Campaign
- **question**: On user delete, who owns the assets?

### Users → AuditLog (1:many)
- **current**: AuditLog.user_id FK to User.id (M17)
- **question**: Do we anonymize audit logs on delete?

### Users → ChatMessage (1:many)
- **current**: No direct FK visible
- **question**: On user delete, anonymize or delete messages?

---

## Acceptance Criteria (Draft)

### Data Model (M18 Apply)
- [ ] User state added: `deleted_at`, `deletion_requested_at`, `deletion_reason`
- [ ] Optional: State machine enum `account_state` (active, deactivating, deleted, suspended)
- [ ] Ownership transfer logic: Campaign reassignment rules
- [ ] Anonymization rules: Which fields to scrub on deletion

### API Endpoints (M18 Deploy)
- [ ] `POST /api/profile/request-deletion` — Request account deletion
- [ ] `POST /api/profile/cancel-deletion` — Cancel deletion request (grace period)
- [ ] `DELETE /api/admin/users/<user_id>` — Force delete (admin only)
- [ ] `POST /api/admin/users/<user_id>/restore` — Restore deleted user (admin only)
- [ ] `POST /api/admin/users/<user_id>/transfer-ownership` — Transfer campaigns

### Cascading Rules (M18 Apply)
- [ ] Campaign ownership reassignment on user delete
- [ ] Campaign membership anonymization
- [ ] Session archival/deletion rules
- [ ] Asset ownership transfer
- [ ] Chat message anonymization

### Audit Logging (M18 Deploy)
- [ ] Log deletion requests
- [ ] Log actual deletions (hard delete)
- [ ] Log ownership transfers
- [ ] Log restorations

---

## Risk Assessment

| Scenario | Risk | Mitigation |
|----------|------|-----------|
| User deletes account, campaigns orphaned | High | Clarify ownership transfer rule |
| Active session when user deleted | High | Define session archival behavior |
| Admin deletes user by mistake | High | Implement grace period + restore |
| Compliance audit finds deleted user data | Critical | Define retention policy + anonymization |
| Storage bloat from soft-deleted users | Medium | Implement cleanup job after retention |
| User data leaks during deletion | Critical | Ensure password/MFA scrubbed immediately |

---

## Next Steps

**For M18 Apply Phase, we need answers to:**

1. **Deletion Strategy**: Soft → Hard (hybrid) or just one?
2. **Ownership Model**: Delete campaigns, transfer, or archive?
3. **Compliance**: GDPR? Right-to-be-forgotten timeline?
4. **Grace Period**: How long before hard delete? (30d default?)
5. **State Machine**: Simple flags or enum state?
6. **Recovery**: Can admins restore deleted users indefinitely?

**Once decided**, we'll design:
- State machine diagram
- Database schema changes
- API endpoints
- Migration job (soft → hard delete scheduler)

---

## Files to Create (M18 Apply)

1. `vtt_app/models/user_lifecycle.py` — State machine + rules
2. `vtt_app/utils/deletion.py` — Deletion helpers
3. `vtt_app/endpoints/profile.py` — Deletion request endpoints
4. `vtt_app/endpoints/admin_users.py` — Admin deletion endpoints
5. `migrations/migration_m18_user_lifecycle.sql` — Add deletion fields
6. `jobs/delete_old_users_job.py` — Scheduled hard-delete job

---

## Key Question for Roll-Drauf Team

> **Should deleted users be recoverable indefinitely by admins, or should they be permanently gone after 30 days (GDPR compliance)?**

This one decision drives the entire architecture.
