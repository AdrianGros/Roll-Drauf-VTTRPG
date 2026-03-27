# Operating Playbook v2 (M36)

**Status**: Go-Live Ready
**Version**: 2.0
**Date**: 2026-03-27

---

## Part 1: Incident Response

### If Platform is Down (500+ Users Affected)
1. **Immediately** (within 5 min):
   - Check status: `curl https://api.rolldrauf.de/health`
   - Check logs: `tail -f logs/app.log`
   - Check DB connection: `psql rolldrauf_prod -c "SELECT 1"`
   - Declare incident in Slack #ops-incidents

2. **Triage** (5-15 min):
   - Database down? → Failover to replica
   - App crashed? → Restart services
   - Out of memory? → Scale up server

3. **Communication** (15 min):
   - Post to status page
   - Email affected users if > 15 min downtime

4. **Root Cause** (1-2 hours):
   - Find error in logs
   - Review recent deployments
   - Check metrics (CPU, memory, DB connections)

### If Users Can't Login
1. Check JWT secret not rotated without restart
2. Check DB connection pool not exhausted
3. Check MFA not broken (test with test account)
4. Check auth endpoints responding: `curl https://api.rolldrauf.de/api/auth/status`

### If Users Complain About Storage Quota
1. Check user's storage_used_gb vs. quota_gb
2. Run `SELECT SUM(size_bytes) FROM assets WHERE campaign_id = ?`
3. Check for orphaned assets (campaigns deleted but assets remain)
4. Clean up with: `python jobs/asset_cleanup_job.py`

### If Asset Won't Download
1. Check asset exists: `SELECT * FROM assets WHERE id = ?`
2. Check file in storage: `test -f /tmp/vtt-assets/{key}`
3. Check permissions: `can_download_asset(user, asset)`
4. Check storage adapter working: `python -c "from vtt_app.storage import get_storage_adapter; get_storage_adapter().exists(key)"`

---

## Part 2: Scaling Procedures

### When CPU > 80%
- Check: `top` or AWS CloudWatch
- Solution: Add 1 more app server (horizontal scale)
- Load balancer config: Add to Nginx upstream

### When DB CPU > 70%
- Check slow queries: `EXPLAIN ANALYZE SELECT ...`
- Solution: Add indices (see `migrations/*.sql`)
- Or: Upgrade DB instance size (vertical scale)

### When Storage > 80% of Disk
- Check: `du -sh /tmp/vtt-assets`
- Solution 1: Run cleanup job: `python jobs/asset_cleanup_job.py`
- Solution 2: Add new EBS volume or upgrade storage
- Solution 3: Migrate to S3 (if using local storage)

### When Audit Log Table > 1GB
- Partition table by month: `ALTER TABLE audit_logs PARTITION BY RANGE (YEAR(timestamp))`
- Archive old logs to S3

---

## Part 3: Backup & Recovery

### Daily Backup Procedure
```bash
# Automated every night at 2am
python jobs/backup_job.py

# Creates:
# - DB dump: backup/db-{date}.sql.gz
# - Asset manifest: backup/assets-{date}.json
```

### Test Backup Every Week
```bash
# Restore to staging DB
gunzip < backup/db-{date}.sql.gz | psql rolldrauf_staging

# Verify data
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM campaigns;
```

### Recover Single Campaign
```bash
# 1. Find backup with campaign
grep "campaign_id=123" backup/assets-{date}.json

# 2. Restore campaign + assets from S3 bucket
python jobs/restore_campaign.py --campaign-id 123 --backup-date 2026-03-20
```

### Recover Deleted User
```bash
# If within 30-day grace period
POST /api/admin/users/{user_id}/restore

# If after grace period (hard-deleted), must restore from DB backup
```

---

## Part 4: User Support Workflows

### User Requests Account Deletion
1. User requests: `POST /api/profile/request-deletion`
2. Check: `SELECT account_state, deleted_at FROM users WHERE id = ?`
3. Status: Should show `marked_for_deletion` + 30-day countdown
4. If user changes mind: `POST /api/profile/cancel-deletion`
5. If 30 days passed: Hard-delete runs automatically at 2am

### User Claims Quota Exceeded Unfairly
1. Check their storage: `SELECT storage_used_gb, storage_quota_gb FROM users WHERE id = ?`
2. Count assets: `SELECT SUM(size_bytes) FROM assets WHERE campaign_id IN (SELECT id FROM campaigns WHERE owner_id = ?)`
3. Check for duplicate assets: `SELECT checksum_md5, COUNT(*) FROM assets GROUP BY checksum_md5 HAVING COUNT(*) > 1`
4. If legitimate, increase quota: `UPDATE users SET storage_quota_gb = 2 WHERE id = ?`
5. Log in audit: `POST /api/admin/users/{id}/quota-increase`

### User Suspended By Moderator
1. Check reason: `SELECT suspended_reason FROM users WHERE id = ?`
2. Review audit logs: `GET /api/admin/audit-logs?action=user_suspended&resource_id={id}`
3. Contact moderator for appeal process
4. If appeal approved: `POST /api/admin/users/{id}/unsuspend`

### Player Can't Join Campaign
1. Check campaign status: `SELECT status FROM campaigns WHERE id = ?`
2. Check campaign membership: `SELECT * FROM campaign_members WHERE campaign_id = ? AND user_id = ?`
3. If not member, check invite: `SELECT * FROM invite_tokens WHERE campaign_id = ? AND email = ?`
4. If no invite, DM can send: `POST /api/campaigns/{id}/invite` (share link)

---

## Part 5: Admin Console Quick Start

### Login
```
1. Go to https://rolldrauf.de/admin
2. Login with admin account
3. Two-factor auth via authenticator app
```

### View Dashboard
- Total users, campaigns, storage, active sessions
- See users marked for deletion (coming in 30 days)
- See suspended users

### Search for User
- Click "Users" → Search by username or email
- View: role, profile tier, storage usage, account state

### Search for Campaign
- Click "Campaigns" → Search by name or owner
- View: status, members, asset count, storage used

### View Audit Logs
- Click "Audit" → See recent actions
- Filter by action (user_suspension, campaign_deleted, asset_uploaded)
- Export for compliance

### Restore User (if deleted accidentally)
- Click "Users" → Filter by `account_state: marked_for_deletion`
- Click user → "Restore Account"
- User can login again immediately

---

## Part 6: Monitoring & Alerting Setup

### Key Metrics to Monitor
- API response time (p95, p99)
- Error rate (4xx, 5xx)
- DB connection pool usage
- Storage usage (% of quota)
- Queue lag (for background jobs)

### Alert Thresholds
- Response time p95 > 2s: Warning
- Error rate > 1%: Critical
- DB connections > 80%: Warning
- Storage > 90% of disk: Critical
- 3+ upload failures in 1 minute: Warning

### Dashboard
- Grafana @ https://grafana.rolldrauf.de
- Prometheus @ https://prometheus.rolldrauf.de/metrics

---

## Part 7: On-Call Runbook

### Monday-Friday Weekday Hours (9-17)
- On-call: Senior Backend Engineer
- SLA: Response < 15 min

### After Hours & Weekends
- On-call: On-call rotation (4-person team)
- SLA: Response < 30 min for critical issues

### Escalation
1. **P1 (Down)**: Page on-call immediately
2. **P2 (Degraded)**: Notify within 1 hour
3. **P3 (Bug)**: File ticket, respond next business day

### Handoff
- At shift change, read #ops-incidents for open issues
- Check dashboard for any alerts
- Review error logs from previous shift

---

## Appendix: Key File Locations

```
/home/admin/projects/roll-drauf-vtt/
├── app.py                 # Main app
├── config.py              # Config
├── requirements.txt       # Dependencies
├── logs/                  # Application logs
│   ├── app.log
│   ├── user_deletion_job.log
│   └── asset_cleanup_job.log
├── backups/               # Daily backups
│   ├── db-2026-03-27.sql.gz
│   └── assets-2026-03-27.json
├── vtt_app/
│   ├── models/            # All database models
│   ├── endpoints/         # All API endpoints
│   ├── permissions.py     # Permission checks
│   ├── upload_security.py # File validation
│   └── storage/           # Local/S3 storage
├── jobs/                  # Background jobs
│   ├── delete_marked_users_job.py
│   ├── asset_cleanup_job.py
│   └── backup_job.py
├── migrations/            # Database migrations
├── tests/                 # Unit & integration tests
└── docs/                  # Documentation
    ├── OPERATING_PLAYBOOK_v2.md (this file)
    ├── SECURITY_COMPLIANCE_M34.md
    ├── INCIDENT_RESPONSE.md (TODO)
    └── RUNBOOKS/          # Specific runbooks
        ├── database_failover.md (TODO)
        ├── scale_vertically.md (TODO)
        └── user_data_recovery.md (TODO)
```

---

## Last Updated
- **Date**: 2026-03-27
- **By**: Claude (Haiku 4.5)
- **Next Review**: 2026-04-27 (monthly)
