"""M19: Generic file asset model (maps, tokens, handouts, images)."""

from vtt_app.extensions import db
from vtt_app.utils.time import utcnow


class Asset(db.Model):
    """Generic file asset owned by a campaign."""

    __tablename__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # File metadata
    filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(50), nullable=False, index=True)
    size_bytes = db.Column(db.Integer, nullable=False)
    checksum_md5 = db.Column(db.String(32), index=True)  # For integrity checks

    # Storage location
    storage_key = db.Column(db.String(255), unique=True)  # S3 key or local path
    storage_provider = db.Column(db.String(20), default='local')  # local, s3

    # Versioning
    asset_version = db.Column(db.Integer, default=1)
    parent_asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'))  # For versions

    # Asset classification
    asset_type = db.Column(db.String(50), nullable=False, index=True)  # map, token, handout, image
    scope = db.Column(db.String(20), default='campaign', index=True)  # campaign, session
    is_public = db.Column(db.Boolean, default=False)

    # Optional thumbnail
    thumbnail_key = db.Column(db.String(255))  # For M27 (generated later)

    # Timestamps
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = db.Column(db.DateTime, index=True)  # Soft delete for M28

    # Relationships
    campaign = db.relationship('Campaign', backref='assets', lazy=True)
    uploader = db.relationship('User', backref='uploaded_assets', lazy=True)
    versions = db.relationship('Asset', remote_side=[id], backref=db.backref('version_history', remote_side=[parent_asset_id]), lazy=True)

    def __repr__(self):
        return f'<Asset {self.id} {self.filename} type={self.asset_type}>'

    def serialize(self):
        """Return JSON-safe dict."""
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'filename': self.filename,
            'mime_type': self.mime_type,
            'size_bytes': self.size_bytes,
            'asset_type': self.asset_type,
            'asset_version': self.asset_version,
            'scope': self.scope,
            'is_public': self.is_public,
            'uploaded_by': self.uploader.username if self.uploader else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.deleted_at is not None,
        }

    def is_soft_deleted(self):
        """Check if asset is soft-deleted."""
        return self.deleted_at is not None

    def get_size_mb(self):
        """Get size in MB."""
        return self.size_bytes / 1024 / 1024

    @staticmethod
    def get_campaign_assets(campaign_id, asset_type=None, include_deleted=False):
        """Get all assets in campaign (optionally filtered by type)."""
        query = Asset.query.filter_by(campaign_id=campaign_id)

        if not include_deleted:
            query = query.filter_by(deleted_at=None)

        if asset_type:
            query = query.filter_by(asset_type=asset_type)

        return query.all()

    @staticmethod
    def get_campaign_assets_by_type(campaign_id, include_deleted=False):
        """Get assets grouped by type."""
        assets = Asset.get_campaign_assets(campaign_id, include_deleted=include_deleted)

        grouped = {
            'maps': [a for a in assets if a.asset_type == 'map'],
            'tokens': [a for a in assets if a.asset_type == 'token'],
            'handouts': [a for a in assets if a.asset_type == 'handout'],
            'images': [a for a in assets if a.asset_type == 'image'],
            'other': [a for a in assets if a.asset_type not in ['map', 'token', 'handout', 'image']],
        }
        return grouped

    def get_version_history(self):
        """Get all versions of this asset (including current)."""
        if self.parent_asset_id:
            # This is a version, get parent
            parent = Asset.query.get(self.parent_asset_id)
            if parent:
                return [parent] + parent.versions
        else:
            # This is the parent
            return [self] + self.versions
