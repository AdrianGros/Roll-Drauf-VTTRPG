# Milestones M19-M36: Complete Implementation Plan

**Status**: Design Complete, Ready for Phased Implementation
**Date**: 2026-03-27
**Scope**: Asset management through release certification (18 milestones)

---

## M19: Asset Domain Deep Discovery & Apply

### Discover
- CampaignMap (already exists) + TokenState (already exists)
- Need: Generic Asset model (maps, tokens, handouts, session files)
- Ownership: campaign_id, uploaded_by_user_id
- Metadata: checksum (MD5), size_bytes, mime_type, storage_key
- Versions: Keep history (v1, v2, v3 with rollback)
- References: Which sessions/maps use this asset
- Retention: Keep until campaign deleted

### Apply: Asset Model

```python
class Asset(db.Model):
    """Generic file asset (maps, tokens, handouts, images)."""
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # File metadata
    filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(50), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    checksum_md5 = db.Column(db.String(32), index=True)

    # Storage location
    storage_key = db.Column(db.String(255), unique=True)  # S3 key or local path
    storage_provider = db.Column(db.String(20), default='local')  # local, s3

    # Versioning
    asset_version = db.Column(db.Integer, default=1)
    parent_asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'))  # For versions

    # Scope
    asset_type = db.Column(db.String(50))  # 'map', 'token', 'handout', 'image'
    scope = db.Column(db.String(20), default='campaign')  # campaign, session
    is_public = db.Column(db.Boolean, default=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = db.Column(db.DateTime)  # Soft delete

    campaign = db.relationship('Campaign', backref='assets')
    uploader = db.relationship('User')
```

### Deploy
- Create `vtt_app/models/asset.py`
- Migration: `migration_m19_asset_model.sql`
- Export in models/__init__.py

---

## M20: Upload Security Pipeline

### Apply
```python
# vtt_app/upload_security.py
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/webp',
    'application/json',  # Token configs
}

MAX_FILE_SIZE_MB = 50
QUARANTINE_TIMEOUT = 3600  # 1 hour

def validate_upload(file, user):
    """Check MIME, size, filename safety."""
    if file.mimetype not in ALLOWED_MIME_TYPES:
        raise UploadError(f'Forbidden MIME type: {file.mimetype}')
    if len(file.stream.read()) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise UploadError(f'File too large')
    if not is_filename_safe(file.filename):
        raise UploadError(f'Invalid filename')

    # Check quota (uses M17 can_upload_asset)
    allowed, msg = can_upload_asset(user, len(file.stream.read()) / 1024 / 1024)
    if not allowed:
        raise QuotaError(msg)
```

### Deploy
- Create `vtt_app/upload_security.py`
- Create `POST /api/assets/upload` endpoint
- Add to `profile_m18.py` or new `assets.py`

---

## M21: Storage Abstraction (Local → S3)

### Apply
```python
# vtt_app/storage/base.py
class StorageAdapter(ABC):
    @abstractmethod
    def upload(self, file_key, file_content): pass
    @abstractmethod
    def download(self, file_key): pass
    @abstractmethod
    def delete(self, file_key): pass

# vtt_app/storage/local.py
class LocalStorageAdapter(StorageAdapter):
    def upload(self, file_key, content):
        path = f'{self.base_path}/{file_key}'
        with open(path, 'wb') as f:
            f.write(content)
        return {'path': path}

# vtt_app/storage/s3.py
class S3StorageAdapter(StorageAdapter):
    def upload(self, file_key, content):
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=file_key,
            Body=content
        )
        return {'s3_key': file_key}
```

### Deploy
- Create `vtt_app/storage/` package
- Create `vtt_app/storage/base.py`, `local.py`, `s3.py`
- Config in `config.py`: `STORAGE_PROVIDER = 'local'` or `'s3'`

---

## M22: Asset Serving & Access Control

### Apply
```python
def can_download_asset(user, asset):
    """Permission check for asset download."""
    # Public assets anyone can download
    if asset.is_public:
        return True

    # Campaign members can download
    campaign_member = asset.campaign.get_member(user.id)
    if campaign_member and campaign_member.is_active():
        return True

    # DM/Admins can download anything
    if user.platform_role in ['admin', 'moderator']:
        return True

    return False

@app.route('/api/assets/<int:asset_id>/download')
@jwt_required()
def download_asset(asset_id):
    asset = Asset.query.get(asset_id)
    if not asset or not can_download_asset(current_user, asset):
        abort(403)

    content = storage_adapter.download(asset.storage_key)
    return send_file(
        io.BytesIO(content),
        mimetype=asset.mime_type,
        as_attachment=True,
        download_name=asset.filename
    )
```

### Deploy
- Add `can_download_asset()` to `vtt_app/permissions.py`
- Create `GET /api/assets/<id>/download` endpoint
- Add caching headers (ETag, Cache-Control)

---

## M23: Campaign Workspace UX (Maps/Tokens/Handouts)

### Apply
```python
# endpoints/campaign_assets.py
@app.route('/api/campaigns/<int:campaign_id>/assets', methods=['GET'])
@require_campaign_access(can_view_campaign)
def list_campaign_assets(campaign_id):
    """List all assets in campaign (grouped by type)."""
    campaign = Campaign.query.get(campaign_id)
    assets = Asset.query.filter_by(campaign_id=campaign_id).all()

    grouped = {
        'maps': [a.serialize() for a in assets if a.asset_type == 'map'],
        'tokens': [a.serialize() for a in assets if a.asset_type == 'token'],
        'handouts': [a.serialize() for a in assets if a.asset_type == 'handout'],
        'images': [a.serialize() for a in assets if a.asset_type == 'image'],
    }
    return jsonify(grouped)

@app.route('/api/campaigns/<int:campaign_id>/assets/<int:asset_id>/versions', methods=['GET'])
def get_asset_versions(campaign_id, asset_id):
    """Get version history with rollback support."""
    asset = Asset.query.get(asset_id)
    versions = Asset.query.filter_by(parent_asset_id=asset_id).all()
    return jsonify({'versions': [v.serialize() for v in versions]})
```

### Deploy
- Create `vtt_app/endpoints/campaign_assets.py`
- Endpoints: list, upload, delete, get_versions
- No UI (just API - UI in M23 frontend)

---

## M24: Session Workspace UX (Live Runtime)

### Apply
```python
# For live sessions, need quick asset swap
@app.route('/api/sessions/<int:session_id>/active-layer', methods=['GET', 'POST'])
@jwt_required()
def get_set_active_layer(session_id):
    """Get/set currently displayed map layer in session."""
    session = GameSession.query.get(session_id)

    if request.method == 'POST':
        data = request.get_json()
        session_state.active_asset_id = data['asset_id']
        db.session.commit()
        # Broadcast via WebSocket (M25)

    return jsonify({'active_asset_id': session_state.active_asset_id})
```

### Deploy
- Add session state tracking for active assets
- WebSocket broadcast handler (detailed in M25)

---

## M25: Realtime Asset Sync Contracts

### Apply
```python
# Socket events for asset changes
SOCKET_EVENTS = {
    'asset_uploaded': {'campaign_id', 'asset_id', 'filename'},
    'asset_deleted': {'campaign_id', 'asset_id'},
    'asset_updated': {'campaign_id', 'asset_id', 'version'},
    'session_active_layer_changed': {'session_id', 'asset_id'},
    'token_moved': {'session_id', 'token_id', 'x', 'y'},
}

# When asset changes:
# 1. Save to DB
# 2. Emit socket event to campaign room
# 3. Include version/checksum for conflict detection
# 4. On rejoin: send snapshot of all assets
```

### Deploy
- Add socket handlers in `vtt_app/play/sockets.py`
- Emit on: asset_uploaded, asset_deleted, active_layer_changed
- Snapshot on rejoin: `/api/sessions/<id>/snapshot`

---

## M26: Quotas, Billing Signals, Fair Use

### Apply
```python
# Already implemented in M17, just extend to assets
# DM: 1GB → 1000MB assets per campaign
# HM: 5GB → 5000MB per campaign

# Add warning thresholds:
def check_storage_warning(user):
    """Alert user if approaching quota."""
    percent = user.get_storage_usage_percent()
    if percent > 80:
        return {'warning': 'storage_near_limit', 'percent': percent}
    if percent > 95:
        return {'alert': 'storage_critical', 'percent': percent}
```

### Deploy
- Add to `GET /api/profile/status` (M18) a `storage_warning` field
- Dashboard shows usage bar with warning color at 80%, red at 95%

---

## M27: Background Jobs & Async Processing

### Apply
```python
# jobs/asset_cleanup_job.py
def cleanup_soft_deleted_assets():
    """Delete soft-deleted assets after 7 days."""
    cutoff = utcnow() - timedelta(days=7)
    assets = Asset.query.filter(
        Asset.deleted_at < cutoff
    ).all()

    for asset in assets:
        storage_adapter.delete(asset.storage_key)
        db.session.delete(asset)
    db.session.commit()

# jobs/thumbnail_job.py
def generate_asset_thumbnails():
    """Generate thumbnails for maps/images."""
    assets_without_thumbnails = Asset.query.filter(
        Asset.asset_type.in_(['map', 'image']),
        Asset.thumbnail_key == None
    ).limit(50).all()

    for asset in assets_without_thumbnails:
        content = storage_adapter.download(asset.storage_key)
        thumb = generate_thumbnail(content, size=(200, 200))
        asset.thumbnail_key = storage_adapter.upload(f'thumbs/{asset.id}', thumb)
    db.session.commit()
```

### Deploy
- Create `jobs/asset_cleanup_job.py`, `thumbnail_job.py`
- Schedule: cleanup daily, thumbnails on upload

---

## M28: Data Retention & Legal Boundaries

### Apply
```python
# config.py
RETENTION_POLICIES = {
    'asset': {
        'active': None,  # Keep forever
        'soft_deleted': 7,  # 7 days then hard-delete
        'campaign_deleted': 30,  # 30 days after campaign delete
    },
    'chat_message': {
        'active': None,
        'campaign_deleted': 90,  # 90 days GDPR right-to-be-forgotten
    },
}

# Retention audit
class RetentionLog(db.Model):
    action = db.Column(db.String(50))  # asset_deleted, campaign_hard_deleted
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    retention_days = db.Column(db.Integer)
    deleted_at = db.Column(db.DateTime)
```

### Deploy
- Create `vtt_app/models/retention_log.py`
- Schedule job: `jobs/retention_policy_job.py` (daily)

---

## M29: Backup, Restore, Tenant-Selective Recovery

### Apply
```python
# Backup strategy: Daily snapshots of DB + asset inventory
# Restore: Admin can restore single campaign or user assets

@app.route('/api/admin/backup/create', methods=['POST'])
@has_platform_role('admin')
def create_backup():
    """Trigger on-demand backup."""
    backup_id = uuid4()
    # 1. Dump DB
    # 2. Create asset manifest (list all assets with checksums)
    # 3. Store in backup bucket
    return {'backup_id': backup_id, 'status': 'running'}

@app.route('/api/admin/restore/campaign/<int:campaign_id>', methods=['POST'])
@has_platform_role('admin')
def restore_campaign(campaign_id):
    """Restore campaign from backup."""
    data = request.get_json()
    backup_id = data['backup_id']
    # Restore campaign + its assets from backup
    return {'status': 'restoring'}
```

### Deploy
- Create `vtt_app/backup/` package with backup/restore logic
- Endpoints: `/api/admin/backup/create`, `/restore/campaign/:id`

---

## M30: Admin Console v1

### Apply
```python
# Admin dashboard endpoints (read-only for now)
@app.route('/api/admin/dashboard/metrics', methods=['GET'])
@has_platform_role('admin')
def get_dashboard_metrics():
    """Overview metrics for admin."""
    return {
        'total_users': User.query.count(),
        'total_campaigns': Campaign.query.count(),
        'total_storage_gb': sum(u.storage_used_gb for u in User.query.all()),
        'active_sessions': GameSession.query.filter_by(status='active').count(),
        'users_marked_deletion': User.query.filter_by(account_state='marked_for_deletion').count(),
    }

@app.route('/api/admin/search/users', methods=['GET'])
@has_platform_role('admin')
def search_users():
    """Search users by username, email, role."""
    q = request.args.get('q')
    users = User.query.filter(
        (User.username.ilike(f'%{q}%')) |
        (User.email.ilike(f'%{q}%'))
    ).limit(20).all()
    return jsonify([u.serialize() for u in users])
```

### Deploy
- Create `vtt_app/endpoints/admin_dashboard.py`
- Endpoints: metrics, search users, search campaigns, user actions

---

## M31: Observability for Multi-Tenant Operations

### Apply
```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

asset_uploads_counter = Counter('asset_uploads_total', 'Total uploads', ['mime_type'])
asset_size_histogram = Histogram('asset_size_bytes', 'Asset size distribution')
storage_usage_gauge = Gauge('user_storage_used_gb', 'Storage per user', ['user_id'])

# SLOs:
# - 99% of uploads complete < 5s
# - 99.9% of asset downloads < 2s
# - 99.5% of permissions checks < 100ms

# Logging: Structured logs with tenant_id, user_id, action
logger.info('asset_uploaded', extra={
    'tenant_id': campaign.owner_id,
    'user_id': current_user.id,
    'asset_id': asset.id,
    'size_mb': asset.size_bytes / 1024 / 1024,
})
```

### Deploy
- Add Prometheus instrumentation to key operations
- Create `vtt_app/metrics.py` with SLO definitions
- Dashboard: Grafana or simple `/metrics` endpoint

---

## M32: Performance & Cost Optimization

### Apply
```python
# Hot paths:
# 1. Asset download (add CDN/caching)
# 2. Campaign list (add pagination, filtering indices)
# 3. Permission checks (cache in request context)

# Optimizations:
# - Add HTTP caching headers (ETag, Cache-Control: max-age=86400)
# - Compress responses (gzip)
# - Index: campaigns(owner_id), assets(campaign_id), users(platform_role)
# - Asset CDN: Serve via CloudFront/Bunny (M33+)
# - Connection pooling for DB

# SQL indices added:
# CREATE INDEX idx_assets_campaign ON assets(campaign_id);
# CREATE INDEX idx_assets_created ON assets(created_at);
# CREATE INDEX idx_campaigns_owner ON campaigns(owner_id);
```

### Deploy
- Add DB indices via migration
- Add response caching decorators
- Compress uploads with gzip

---

## M33: Multi-Region Readiness (Optional)

### Apply
```python
# Region tagging for future deployment
# No code changes, just preparation:

# Assets: Add region_primary field (for future geo-distribution)
# Sessions: Stateless (ready for load balancing)
# DB: Connection pooling ready for read replicas

# If implemented:
# - S3: Use region-specific buckets
# - Sessions: Store in Redis (ready for horizontal scaling)
# - Users: Add geo_preference field (which region to serve from)
```

### Deploy
- Add `region_primary` field to Asset model
- Make all services stateless (no local session files)
- Document multi-region architecture (but don't implement yet)

---

## M34: Compliance, Security Hardening, Audit Readiness

### Apply
```python
# Security hardening:
# - CORS: Only allow same-origin
# - CSP: Restrict script sources
# - Rate limiting: 100 req/min per user (already in Flask-Limiter)
# - SQL injection: All queries use ORM (SQLAlchemy)
# - XSS: All responses JSON (not HTML injection risk)
# - CSRF: JWT tokens (not vulnerable to CSRF)

# Encryption at rest:
# - Passwords: bcrypt (already done)
# - MFA secrets: AES encryption
# - Sensitive fields: database-level encryption (optional)

# Audit completeness:
# - All permission changes logged (M17 ✅)
# - All deletions logged (M18 ✅)
# - All asset ops logged (M19-M25)
# - All admin actions logged (M30)

# Compliance checklist:
# ✅ GDPR: Right to delete (M18), data export (M29)
# ✅ Data minimization: Only store needed fields
# ✅ Privacy: Suspension + anonymization (M18)
# ✅ Audit: Full audit trail (M17-M31)
```

### Deploy
- Add CORS headers in app.py
- Add CSP headers
- Review and test rate limiting
- Document security architecture

---

## M35: Migration & Backward-Compatibility Closure

### Apply
```python
# Identify legacy fields to remove:
# - Campaign.background_url (use Asset instead)
# - Campaign.token_url (use Asset instead)
# - User.role_id (use platform_role + profile_tier)

# Migration strategy:
# Phase 1: Dual-read (old + new both work)
# Phase 2: Single-write (write to new only)
# Phase 3: Sunset (remove old field reads)

# Example migration:
# 1. Keep background_url for reads (backward compat)
# 2. New uploads → Asset model
# 3. After 90 days: Remove background_url field
# 4. Test all existing campaigns still work

DEPRECATED_FIELDS = {
    'campaign.background_url': 'Use Asset model instead (M19)',
    'campaign.token_url': 'Use Asset model instead (M19)',
    'user.role_id': 'Use platform_role + profile_tier instead (M17)',
}
```

### Deploy
- Create migration: `migration_m35_deprecations.sql`
- Document sunset timeline
- Add deprecation warnings to logs

---

## M36: Release Certification & Operating Playbook v2

### Apply
```python
# Final go/no-go gates:
# ✅ All 35 milestones implemented
# ✅ 100+ unit tests passing
# ✅ Integration tests passed
# ✅ Load test: 100 concurrent users, <2s response
# ✅ Security scan: 0 critical vulnerabilities
# ✅ Backup/restore tested
# ✅ Admin console tested
# ✅ Observability: Dashboards working
# ✅ Audit logs: 100% coverage of critical actions

# Operating playbook v2 sections:
# 1. Incident response (down? quota exceeded? data corruption?)
# 2. Scaling procedures (add DB replica? increase asset storage?)
# 3. Backup/recovery SOP
# 4. User support workflows (delete request? restore? suspension?)
# 5. Admin console walkthrough
# 6. Monitoring & alerting setup
# 7. On-call runbook

# Go-live readiness:
# - Staging environment mirrors prod
# - Canary deployment: 10% traffic → 100%
# - Rollback plan documented
# - Support team trained
```

### Deploy
- Create `docs/OPERATING_PLAYBOOK_v2.md`
- Create `docs/INCIDENT_RESPONSE.md`
- Create `docs/RUNBOOKS/`
- Final integration test suite
- Load test results

---

## Summary: M19-M36 Deliverables

| Milestone | Deliverable | Status |
|-----------|---|---|
| M19 | Asset model, migration | Ready |
| M20 | Upload security, validation | Ready |
| M21 | Storage abstraction (local/S3) | Ready |
| M22 | Asset download + permissions | Ready |
| M23 | Campaign asset management API | Ready |
| M24 | Session live asset swap | Ready |
| M25 | Realtime asset sync + WebSocket | Ready |
| M26 | Storage quota enforcement | Ready (extends M17) |
| M27 | Background jobs (cleanup, thumbnails) | Ready |
| M28 | Retention policies + enforcement | Ready |
| M29 | Backup/restore architecture | Ready |
| M30 | Admin console (read-only metrics) | Ready |
| M31 | Observability + SLOs | Ready |
| M32 | Performance optimization (indices, caching) | Ready |
| M33 | Multi-region readiness (prep only) | Ready |
| M34 | Security hardening + compliance | Ready |
| M35 | Legacy field sunset + migration | Ready |
| M36 | Certification checklist + playbooks | Ready |

**Total New Files**: ~35 (models, endpoints, jobs, docs)
**Total Modified Files**: ~10 (config, migrations, app.py)
**Total Lines of Code**: ~3000-4000
**Total Documentation**: ~5000 lines

---

## Implementation Order (Phased)

**Phase 1 (M19-M22)**: Asset core infrastructure
**Phase 2 (M23-M25)**: UX/realtime
**Phase 3 (M26-M29)**: Quotas, jobs, retention
**Phase 4 (M30-M32)**: Admin + observability + optimization
**Phase 5 (M33-M36)**: Multi-region prep + hardening + release

Each phase: 1-2 weeks of development + testing.

---

## Critical Path Dependencies

```
M17 (Permissions) ← needed by M18 (Lifecycle)
                 ← needed by M22 (Asset Access)
                 ← needed by M30 (Admin)

M18 (Lifecycle) ← needed by M35 (Legacy sunset)

M19 (Asset Model) ← needed by M20-M32 (all asset ops)

M27 (Jobs) ← needed by M28 (Retention)
           ← needed by M32 (Optimization)

M34 (Security) must complete before M36 (Release)
```

All dependencies satisfied by ordering above.

