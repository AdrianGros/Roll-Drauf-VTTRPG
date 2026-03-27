"""Campaign map catalog model."""

from datetime import datetime

from vtt_app.extensions import db


class CampaignMap(db.Model):
    """Reusable map definition owned by a campaign."""

    __tablename__ = "campaign_maps"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)

    grid_type = db.Column(db.String(20), default="square", nullable=False)
    grid_size = db.Column(db.Integer, default=32, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)

    background_url = db.Column(db.Text)
    fog_enabled = db.Column(db.Boolean, default=False, nullable=False)
    light_rules = db.Column(db.JSON)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = db.Column(db.DateTime, index=True)

    campaign = db.relationship("Campaign", backref="maps")
    creator = db.relationship("User")

    def __repr__(self):
        return f"<CampaignMap {self.id} campaign={self.campaign_id}>"

    def is_archived(self) -> bool:
        return self.archived_at is not None

    def serialize(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "name": self.name,
            "description": self.description,
            "grid_type": self.grid_type,
            "grid_size": self.grid_size,
            "width": self.width,
            "height": self.height,
            "background_url": self.background_url,
            "fog_enabled": self.fog_enabled,
            "light_rules": self.light_rules or {},
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
        }
